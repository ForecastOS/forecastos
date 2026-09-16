import statistics
import time
from datetime import datetime

import pandas as pd
from dask.distributed import Client
from dask_cloudprovider.aws import FargateCluster

from forecastos.portfolio.result import BaseResult
from forecastos.utils import HydrateMixin


class BacktestController(HydrateMixin):
    """Container class that runs backtests using passed-in portfolio engineering `strategy` (see :py:class:`~forecastos.portfolio.strategy.base_strategy.BaseStrategy`), then saves results into `result` (see :py:class:`~forecastos.backtest.result.Result`) class.

    Supports dehydrate/rehydrate (see :py:class:`~forecastos.utils.hydrate.HydrateMixin`).
    Dehydrating the controller persists the whole bundle — strategy config, any stateful
    optimization ledgers (e.g. tranche unwind state), and the full holdings/trade history
    in `results` — in a single file, so a strategy can be loaded each day to generate the
    next trade list. Runtime-only attributes that cannot (or should not) be pickled are
    excluded: the dask `client`/`dask_cluster` (recreate for distributed runs) and `hooks`
    (often lambdas, which do not pickle). The strategy<->controller<->results back-references
    are dropped to avoid a pickling cycle and rebuilt on rehydrate in :py:meth:`__setstate__`.

    For live/paper trading, trades for the current day must be generated before that day's
    returns exist, so the holdings outcome cannot yet be computed. :py:meth:`generate_trades`
    produces the executable trade list and holds it as a *pending* position (`self.pending`,
    which persists across dehydrate/rehydrate); :py:meth:`settle_pending` later applies the
    realized returns and records the completed position. The typical daily loop is: rehydrate
    -> settle yesterday's pending with today's now-known returns -> generate today's trades ->
    dehydrate. :py:meth:`resume` settles any pending trade before continuing.
    """

    _excluded_attrs = {"client", "dask_cluster", "hooks"}

    def __setstate__(self, state):
        super().__setstate__(state)

        # `hooks` (often lambdas) aren't persisted; restore an empty registry so the
        # rehydrated controller stays usable (e.g. generate_positions()).
        if "hooks" not in self.__dict__:
            self.hooks = {}

        # Backward-compat for pickles written before `pending` existed.
        if "pending" not in self.__dict__:
            self.pending = None

        # Re-establish the cross-references intentionally dropped to break the pickling
        # cycle (mirrors what __init__ wires up).
        strategy = getattr(self, "strategy", None)
        if strategy is not None:
            strategy.backtest_controller = self
            results = getattr(self, "results", None)
            if results is not None:
                results.strategy = strategy

    def __init__(self, strategy, **kwargs):
        self.strategy = strategy
        self.strategy.backtest_controller = self

        # Optional
        self._set_time_periods(**kwargs)

        self.hooks = kwargs.get("hooks", {})

        self.distributed = kwargs.get("distributed", False)
        self.dask_cluster = kwargs.get("dask_cluster", False)
        self.dask_cluster_config = {
            "n_workers": 50,
            "image": "daskdev/dask:latest",
            "region_name": "us-east-2",  # Change this to your preferred AWS region
            "worker_cpu": 1024 * 2,  # 2 vCPU
            "worker_mem": 1024 * 4,  # 4 GB memory
            "scheduler_cpu": 1024 * 16,
            "scheduler_mem": 1024 * 32,
            "scheduler_timeout": "3600s",
            "environment": {
                "EXTRA_PIP_PACKAGES": "forecastos scikit-learn",
            },
        }
        self.dask_cluster_config.update(kwargs.get("dask_cluster_config", {}))

        self.initial_portfolio = kwargs.get(
            "initial_portfolio",
            self._create_initial_portfolio_if_not_provided(**kwargs),
        )

        # Create results instance for saving performance
        self.results = kwargs.get("results_model", BaseResult)(
            start_date=self.start_date,
            end_date=self.end_date,
        )
        self.results.strategy = self.strategy

        # Holds a trade list generated for a period whose returns aren't yet known
        # (live/paper trading); settled by settle_pending() once they are. See class docstring.
        self.pending = None

    def generate_positions(self):
        print(
            f"Generating historical portfolio trades and positions at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}..."
        )
        # Create t == 0 position (no trades)
        t = self._get_initial_t()
        dollars_trades = pd.Series(index=self.initial_portfolio.index, data=0)
        dollars_holdings_at_next_t = self.initial_portfolio  # Includes cash
        self.results.save_position(t, dollars_trades, dollars_holdings_at_next_t)

        if self.distributed:
            self._dask_start_client_and_cluster()
            self.strategy.precompute_trades_distributed(
                dollars_holdings_at_next_t, self.time_periods
            )
            print("\nClosing dask cluster...")
            self.dask_cluster.close()
            print("\nDask cluster closed.\n")
            self.strategy.weights_trades_distr = (
                self.strategy.weights_trades_distr.fillna(0)
            )  # Fill NAs that occur due to no solution

        # Walk through time and calculate future trades, estimated and actual costs and returns, and resulting positions
        for t in self.time_periods:
            dollars_trades = self.strategy.generate_trade_list(
                dollars_holdings_at_next_t, t
            )
            dollars_holdings_at_next_t, dollars_trades = (
                self.strategy.get_actual_positions_for_t(
                    dollars_holdings_at_next_t, dollars_trades, t
                )
            )
            self.results.save_position(t, dollars_trades, dollars_holdings_at_next_t)

            for func in self.hooks.get("after_trades", []):
                func(self, t, dollars_trades, dollars_holdings_at_next_t)

        print(f"\n\nDone simulating at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.")
        return self.results

    @property
    def pending_trades(self):
        """The most recent trade list generated but not yet settled, or ``None``."""
        return None if self.pending is None else self.pending["dollars_trades"]

    def generate_trades(self, t, *, strategy_data=None, hooks=None):
        """Generate the executable trade list for period `t` **without** settling it into
        next-period holdings (which would require `t`'s realized returns — unavailable when
        trading for the current/future day).

        The cash-balanced trade list is returned and held as a *pending* position in
        `self.pending` (which survives dehydrate/rehydrate) until :py:meth:`settle_pending`
        is called once `t`'s returns are known. So the live loop is: generate today's
        trades, dehydrate, execute them, then reload tomorrow and settle.

        Raises ``ValueError`` if a pending trade already exists (settle it first) or if the
        strategy is missing required data (pass it via `strategy_data`).

        Parameters
        ----------
        t : datetime-like
            The period the trades are for (typically "today").
        strategy_data : dict, optional
            Fresh data to set on the strategy first, e.g. ``{"target_weights": df}``.
            Required for any of the strategy's ``_required_data`` that was excluded from
            dehydration.
        hooks : dict, optional
            `after_trades` hooks to (re)install (run at settlement, not here).

        Returns
        -------
        The pending `dollars_trades` (a pandas Series).
        """
        if self.pending is not None:
            raise ValueError(
                f"A pending trade for {self.pending['t']} is unsettled; call "
                f"settle_pending() (once its returns are known) before generating new trades."
            )

        strategy = self._prepare_strategy(strategy_data=strategy_data, hooks=hooks)
        self._require_data(getattr(strategy, "_required_data", ()))
        self._ensure_initial_position()

        dollars_holdings = self.results.dollars_holdings_at_next_t.iloc[-1]
        dollars_trades = strategy.generate_trade_list(dollars_holdings, t)
        dollars_holdings_after_trades, dollars_trades = strategy.settle_trades(
            dollars_holdings, dollars_trades, t
        )

        self.pending = {
            "t": t,
            "dollars_trades": dollars_trades,
            "dollars_holdings_after_trades": dollars_holdings_after_trades,
        }
        return dollars_trades

    def settle_pending(self, *, strategy_data=None):
        """Settle the pending trade created by :py:meth:`generate_trades`, now that period
        `t`'s realized returns are available: apply the returns to the post-trade holdings to
        get the next period's starting holdings, record the completed position in
        `self.results`, run `after_trades` hooks, and clear the pending state.

        Parameters
        ----------
        strategy_data : dict, optional
            Fresh data to set on the strategy first — in particular an updated
            `actual_returns` that now includes the realized row for the pending period.

        Returns
        -------
        The resulting `dollars_holdings_at_next_t` (a pandas Series).
        """
        if self.pending is None:
            raise ValueError("No pending trade to settle.")

        strategy = self._prepare_strategy(strategy_data=strategy_data, hooks=None)
        t = self.pending["t"]

        actual_returns = getattr(strategy, "actual_returns", None)
        if actual_returns is None:
            raise ValueError(
                "Strategy is missing `actual_returns`; pass it via "
                "settle_pending(strategy_data=...) so realized returns can be applied."
            )
        if t not in actual_returns.index:
            raise ValueError(
                f"actual_returns has no realized row for pending period {t}; supply updated "
                f"actual_returns (including {t}) via settle_pending(strategy_data=...)."
            )

        dollars_trades = self.pending["dollars_trades"]
        dollars_holdings_at_next_t = strategy.apply_returns(
            self.pending["dollars_holdings_after_trades"], t
        )
        self.results.save_position(t, dollars_trades, dollars_holdings_at_next_t)

        for func in self.hooks.get("after_trades", []):
            func(self, t, dollars_trades, dollars_holdings_at_next_t)

        self.pending = None
        return dollars_holdings_at_next_t

    def resume(self, time_periods=None, *, strategy_data=None, hooks=None):
        """Continue generating trades on a (typically rehydrated) controller.

        First settles any pending trade (e.g. one generated in a prior live session and
        dehydrated before its returns were known). Then, if `time_periods` is given, picks
        up from the most recent holdings in `self.results` and generates+settles trades for
        each period — the batch "load and generate the next trade list" loop. Stateful
        strategy ledgers (e.g. the tranche unwind schedule) carry forward, so unwinds
        continue correctly.

        For day-by-day live/paper trading where only the *previous* day's returns are known,
        use :py:meth:`settle_pending` + :py:meth:`generate_trades` instead.

        Parameters
        ----------
        time_periods : iterable of datetime-like, optional
            New periods to generate trades for, in order, all with known returns. Should
            come *after* the last period already recorded in `self.results`. If omitted,
            only a pending trade (if any) is settled.
        strategy_data : dict, optional
            Fresh data to set on the strategy before resuming, e.g.
            ``{"actual_returns": df, "target_weights": df}``. Each key is set on the
            strategy. **Required** for any of the strategy's ``_required_data`` that was
            excluded when the controller was dehydrated (raises ``ValueError`` otherwise,
            when `time_periods` is given). The supplied frames must cover both `time_periods`
            and far enough back to scale any still-open tranches being unwound.
        hooks : dict, optional
            `after_trades` hooks to (re)install. Hooks are not persisted across
            dehydration (lambdas don't pickle), so re-supply them here if needed.

        Returns
        -------
        The `self.results` object.
        """
        strategy = self._prepare_strategy(strategy_data=strategy_data, hooks=hooks)

        if self.pending is not None:
            self.settle_pending()

        if not time_periods:
            return self.results

        self._require_data(getattr(strategy, "_required_data", ()))
        if getattr(self.results, "dollars_holdings_at_next_t", None) is None:
            raise ValueError(
                "No prior positions to resume from. Run generate_positions() (or save an "
                "initial position) before calling resume()."
            )

        dollars_holdings_at_next_t = self.results.dollars_holdings_at_next_t.iloc[-1]

        for t in time_periods:
            dollars_trades = strategy.generate_trade_list(
                dollars_holdings_at_next_t, t
            )
            dollars_holdings_at_next_t, dollars_trades = (
                strategy.get_actual_positions_for_t(
                    dollars_holdings_at_next_t, dollars_trades, t
                )
            )
            self.results.save_position(t, dollars_trades, dollars_holdings_at_next_t)

            for func in self.hooks.get("after_trades", []):
                func(self, t, dollars_trades, dollars_holdings_at_next_t)

        return self.results

    def _prepare_strategy(self, *, strategy_data=None, hooks=None):
        """Inject fresh `strategy_data`, ensure the back-reference, optionally (re)install
        `hooks`, and return the strategy."""
        strategy = self.strategy
        strategy.backtest_controller = self  # defensive: ensure the back-reference holds

        for name, value in (strategy_data or {}).items():
            setattr(strategy, name, value)

        if hooks is not None:
            self.hooks = hooks

        return strategy

    def _require_data(self, names):
        missing = [
            name for name in names if getattr(self.strategy, name, None) is None
        ]
        if missing:
            raise ValueError(
                f"{type(self.strategy).__name__} is missing required data {missing}. "
                f"Pass it via strategy_data=...; this data must be re-supplied when it was "
                f"excluded from dehydration."
            )

    def _ensure_initial_position(self):
        """Save a t=0 position from `initial_portfolio` if `results` has none yet."""
        if getattr(self.results, "dollars_holdings_at_next_t", None) is not None:
            return
        t = self._get_initial_t()
        dollars_trades = pd.Series(index=self.initial_portfolio.index, data=0)
        self.results.save_position(t, dollars_trades, self.initial_portfolio)

    def _set_time_periods(self, **kwargs):
        time_periods = kwargs.get("time_periods", self.strategy.actual_returns.index)
        self.start_date = kwargs.get("start_date", time_periods[0])
        self.end_date = kwargs.get("end_date", time_periods[-1])

        self.time_periods = time_periods[
            (time_periods >= self.start_date) & (time_periods <= self.end_date)
        ]

    def _create_initial_portfolio_if_not_provided(self, **kwargs):
        aum = kwargs.get("aum", 100_000_000)
        initial_portfolio = pd.Series(
            index=self.strategy.actual_returns.columns, data=0
        )
        initial_portfolio[self.strategy.cash_column_name] = aum

        return initial_portfolio

    def _get_initial_t(self):
        try:
            median_time_delta = statistics.median(
                self.time_periods[1:5] - self.time_periods[0:4]
            )
        except ValueError:
            median_time_delta = self.time_periods[1] - self.time_periods[0]

        return pd.to_datetime(self.start_date) - median_time_delta

    def _dask_start_client_and_cluster(self, retries=5, delay=15):
        print(
            "\nDistributing trade generation with Dask client.\n\nTrade-specific costs, constraints, and risk-models will continue to work as expected."
        )
        if self.dask_cluster:
            self.client = Client(self.dask_cluster, timeout="3600s")
        else:
            for i in range(retries):
                try:
                    print(
                        f"\nCreating Dask cluster at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}..."
                    )
                    self.dask_cluster = FargateCluster(**self.dask_cluster_config)
                    self.client = Client(self.dask_cluster, timeout="600s")
                    print(
                        f"\nCluster created. Distributing tasks at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}."
                    )
                    return True
                except Exception as e:
                    print(
                        f"Connection attempt {i+1} failed: {e}. Will retry in {delay}s"
                    )
                    if i < retries - 1:
                        time.sleep(delay)
                    else:
                        raise
