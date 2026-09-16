import datetime as dt

import pandas as pd

from forecastos.portfolio.constraint_model import BaseConstraint
from forecastos.portfolio.cost_model import BaseCost
from forecastos.utils import HydrateMixin


class BaseStrategy(HydrateMixin):
    """Base class for an optimization strategy.

    Must implement :py:meth:`~forecastos.portfolio.strategy.base_strategy.BaseStrategy.generate_trade_list` as per below.

    Supports dehydrate/rehydrate (see :py:class:`~forecastos.utils.hydrate.HydrateMixin`)
    so strategies can be persisted between sessions (e.g. loaded daily to generate the
    next trade list). The `backtest_controller` back-reference is intentionally excluded
    to avoid a pickling cycle; it is re-established when the owning
    :py:class:`~forecastos.portfolio.backtest_controller.BacktestController` is rehydrated.
    Dehydrate the controller (not the strategy on its own) to keep the strategy state,
    holdings, and trade history in sync.

    Attributes
    ----------
    costs : list
        Cost models evaluated during optimization strategy. Defaults to empty list. See :py:class:`~forecastos.portfolio.cost_model.base_cost.BaseCost` for cost model base class.
    constraints : list
        Constraints applied for optimization strategy. Defaults to empty list. See :py:class:`~forecastos.portfolio.constraint_model.base_constraint.BaseConstraint for optimization model base class.
    """

    _excluded_attrs = {"backtest_controller"}

    # Data attributes the strategy needs to generate trades. Checked by
    # :py:meth:`~forecastos.portfolio.backtest_controller.BacktestController.resume` so
    # that, if any were excluded from dehydration, resuming fails loudly until they are
    # re-supplied via ``resume(strategy_data=...)``.
    _required_data = ("actual_returns",)

    def __init__(
        self,
        actual_returns: pd.DataFrame,
        costs: [BaseCost] = [],
        constraints: [BaseConstraint] = [],
        **kwargs,
    ):
        self.actual_returns = actual_returns
        self.costs = costs
        self.constraints = constraints

        self.cash_column_name = kwargs.get("cash_column_name", "cash")
        self.metadata_properties = ["cash_column_name"]

    def _zerotrade(self, holdings):
        return pd.Series(index=holdings.index, data=0.0)

    def generate_trade_list(self, holdings: pd.Series, t: dt.datetime) -> pd.Series:
        """Calculates and returns trade list (in units of currency passed in), given (added) optimization logic.

        Parameters
        ----------
        holdings : pandas.Series
            Holdings at beginning of period `t`.
        t : datetime.datetime
            The datetime for associated holdings `holdings`.
        """
        raise NotImplementedError

    def settle_trades(
        self, dollars_holdings: pd.Series, dollars_trades: pd.Series, t: dt.datetime
    ) -> pd.Series:
        """Applies trading/holding costs and the balancing cash entry to `dollars_trades`,
        returning ``(dollars_holdings_after_trades, dollars_trades)`` — the portfolio held
        immediately after executing the trades during period `t`.

        This step needs only data available at trade time (prices, volume, spreads); it
        does **not** apply period returns, so it is safe to call when generating trades for
        the current (not-yet-realized) period. Use :py:meth:`apply_returns` afterwards, once
        `t`'s returns are known, to roll forward to the next period's holdings.
        """
        dollars_holdings_plus_trades = dollars_holdings + dollars_trades

        costs = [
            cost.actual_cost(
                t,
                dollars_holdings_plus_trades=dollars_holdings_plus_trades,
                dollars_trades=dollars_trades,
            )
            for cost in self.costs
        ]

        cash_col = self.cash_column_name
        dollars_trades[cash_col] = -sum(
            dollars_trades[dollars_trades.index != cash_col]
        ) - sum(costs)
        dollars_holdings_plus_trades[cash_col] = (
            dollars_holdings[cash_col] + dollars_trades[cash_col]
        )

        return dollars_holdings_plus_trades, dollars_trades

    def apply_returns(
        self, dollars_holdings_after_trades: pd.Series, t: dt.datetime
    ) -> pd.Series:
        """Applies realized period-`t` returns to post-trade holdings, returning holdings at
        the start of the next period.

        Requires ``actual_returns.loc[t]`` (i.e. period `t` must have elapsed), so this is
        the step deferred when trading live for the current day.
        """
        return (
            self.actual_returns.loc[t] * dollars_holdings_after_trades
            + dollars_holdings_after_trades
        )

    def get_actual_positions_for_t(
        self, dollars_holdings: pd.Series, dollars_trades: pd.Series, t: dt.datetime
    ) -> pd.Series:
        """Calculates and returns actual positions, after accounting for trades and costs during period t.

        Equivalent to :py:meth:`settle_trades` followed by :py:meth:`apply_returns`; used by
        the backtest loop where period `t`'s returns are already known.
        """
        dollars_holdings_after_trades, dollars_trades = self.settle_trades(
            dollars_holdings, dollars_trades, t
        )
        dollars_holdings_at_next_t = self.apply_returns(
            dollars_holdings_after_trades, t
        )

        return dollars_holdings_at_next_t, dollars_trades

    def metadata_dict(self):
        meta_d = {
            "strategy": self.__class__.__name__,
        }

        if getattr(self, "risk_model", False):
            meta_d[self.risk_model.__class__.__name__] = self.risk_model.metadata_dict()

        if getattr(self, "constraints", False):
            meta_d["constraint_models"] = {
                el.__class__.__name__: el.metadata_dict() for el in self.constraints
            }

        if getattr(self, "costs", False):
            meta_d["cost_models"] = {
                el.__class__.__name__: el.metadata_dict()
                for el in self.costs
                if "Risk" not in el.__class__.__name__
            }

        return self._add_strategy_metadata_params(meta_d)

    def _add_strategy_metadata_params(self, meta_d):
        metadata_properties = getattr(self, "metadata_properties", [])
        if metadata_properties:
            meta_d["strategy_config"] = {}
            for p in metadata_properties:
                meta_d["strategy_config"][p] = getattr(self, p, "n.a.")

        return meta_d
