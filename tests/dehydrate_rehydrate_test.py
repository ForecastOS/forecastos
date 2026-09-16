"""Dehydrate/rehydrate round-trip for portfolio strategies.

Exercises the live-trading workflow the HydrateMixin enables: run a strategy for a
while, persist the BacktestController to disk mid-run, reload it, and keep generating
trades. The resumed run must produce the exact same trades, holdings, and (crucially)
tranche-unwind ledger as an uninterrupted run.

Uses small synthetic data so the test is fast and offline. The strategy under test is
SPOWeightsTranches, whose unwind logic depends on state split across the strategy
(`dollars_trades_unwind_pre`) and the results ledger (`dollars_trades`) — so a correct
round-trip proves both survive together.
"""

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from forecastos.portfolio import BacktestController
from forecastos.portfolio.strategy import SPOWeightsTranches

ASSETS = ["A", "B", "C", "D", "cash"]
N_PERIODS_HELD = 5
N_PERIODS = 20
SPLIT = 8  # dehydrate after this many periods (well past the first unwind)


def _build_controller():
    # ~monthly periods over multiple years, so annualized metrics (Sharpe, etc.) are
    # realistic. A short daily span would make annualization (raising returns to ~1/years)
    # blow the numbers up to absurd magnitudes.
    start = pd.Timestamp("2018-01-02")
    dates = pd.DatetimeIndex(
        [start + pd.Timedelta(days=30 * i) for i in range(N_PERIODS + 1)]
    )
    rng = np.random.default_rng(0)
    actual_returns = pd.DataFrame(
        rng.normal(0.004, 0.03, size=(len(dates), len(ASSETS))),  # ~monthly, equity-like
        index=dates,
        columns=ASSETS,
    )
    actual_returns["cash"] = 0.0016  # deterministic ~2%/yr over monthly periods

    # Per-tranche target trade weights: small long positions funded by cash. They sum to
    # zero so the optimizer can hit the target exactly (strictly better than not trading),
    # which makes the strategy actually take risk — uniform weights summing to 1 leave
    # "do nothing" tied with "trade", so the portfolio would never leave cash.
    target_weights = pd.DataFrame(
        [[0.03, 0.03, 0.03, 0.03, -0.12]] * len(dates), index=dates, columns=ASSETS
    )

    strategy = SPOWeightsTranches(
        actual_returns=actual_returns,
        target_weights=target_weights,
        n_periods_held=N_PERIODS_HELD,
        cash_column_name="cash",
    )
    return BacktestController(strategy=strategy)


def _init_positions(controller):
    """Replicates the t=0 setup in BacktestController.generate_positions()."""
    t0 = controller._get_initial_t()
    holdings = controller.initial_portfolio
    zero = pd.Series(index=holdings.index, data=0.0)
    controller.results.save_position(t0, zero, holdings)
    return holdings


def _step(controller, holdings, t):
    """One day of the live loop: generate trades, settle, record."""
    strat = controller.strategy
    trades = strat.generate_trade_list(holdings, t)
    holdings_next, trades = strat.get_actual_positions_for_t(holdings, trades, t)
    controller.results.save_position(t, trades, holdings_next)
    return holdings_next


def test_dehydrate_rehydrate_resumes_identically(tmp_path):
    # Reference: one uninterrupted run.
    ref = _build_controller()
    periods = list(ref.time_periods)
    h = _init_positions(ref)
    for t in periods:
        h = _step(ref, h, t)

    # Sanity: the synthetic data should yield realistic (finite, sensibly-scaled) metrics,
    # not the absurd values you get from annualizing too short a span.
    assert np.isfinite(ref.results.sharpe_ratio)
    assert abs(ref.results.sharpe_ratio) < 25

    # Split run: dehydrate mid-stream, rehydrate, then resume.
    ctl = _build_controller()
    assert list(ctl.time_periods) == periods
    h = _init_positions(ctl)
    for t in periods[:SPLIT]:
        h = _step(ctl, h, t)

    ctl.dehydrate_to_disk(str(tmp_path), "controller.pkl")
    resumed = BacktestController.rehydrate_from_disk(str(tmp_path), "controller.pkl")

    # Cross-references dropped to break the pickling cycle must be rebuilt on load.
    assert resumed.strategy.backtest_controller is resumed
    assert resumed.results.strategy is resumed.strategy
    # Non-pickleable runtime attrs are gone but the object stays usable.
    assert resumed.hooks == {}

    # Resume the daily loop via the controller's own method (data was persisted).
    resumed.resume(periods[SPLIT:])

    # The tranche-unwind ledger (strategy state) survived and is complete.
    assert resumed.strategy.dollars_trades_unwind_pre.shape[0] == len(periods)
    # ...and the unwind logic actually engaged (otherwise the test is vacuous).
    assert len(periods) > N_PERIODS_HELD

    # Resumed run matches the uninterrupted run, position-for-position.
    pdt.assert_frame_equal(
        resumed.results.dollars_trades,
        ref.results.dollars_trades,
        check_exact=False,
        rtol=1e-4,
        atol=1e-6,
    )
    pdt.assert_frame_equal(
        resumed.results.dollars_holdings_at_next_t,
        ref.results.dollars_holdings_at_next_t,
        check_exact=False,
        rtol=1e-4,
        atol=1e-6,
    )
    pdt.assert_frame_equal(
        resumed.strategy.dollars_trades_unwind_pre,
        ref.strategy.dollars_trades_unwind_pre,
        check_exact=False,
        rtol=1e-4,
        atol=1e-6,
    )


def test_pending_trade_survives_dehydrate_and_settles_identically(tmp_path):
    """Live/paper-trading flow: each day, generate trades for *today* (returns not yet
    known), persist to disk, reload, then settle once the day's returns are in. The result
    must match an uninterrupted backtest position-for-position."""
    # Reference: ordinary uninterrupted run (returns known throughout).
    ref = _build_controller()
    periods = list(ref.time_periods)
    h = _init_positions(ref)
    for t in periods:
        h = _step(ref, h, t)

    # Live run: settle the prior session's pending before each new day, persisting in the
    # gap between "trades decided" and "returns known".
    ctl = _build_controller()
    h = _init_positions(ctl)
    for t in periods[:SPLIT]:
        h = _step(ctl, h, t)

    for t in periods[SPLIT:]:
        pending_trades = ctl.generate_trades(t)
        assert ctl.pending is not None

        # Dehydrate in the gap: trades are decided but today's outcome is unknown.
        ctl.dehydrate_to_disk(str(tmp_path), "live.pkl")
        ctl = BacktestController.rehydrate_from_disk(str(tmp_path), "live.pkl")

        # The pending trade list survived the round trip intact.
        pdt.assert_series_equal(ctl.pending_trades, pending_trades)

        # Next day: the period's returns are now known, so settle.
        ctl.settle_pending()
        assert ctl.pending is None

    # The day-by-day live flow reproduced the uninterrupted run exactly.
    pdt.assert_frame_equal(
        ctl.results.dollars_trades, ref.results.dollars_trades,
        check_exact=False, rtol=1e-4, atol=1e-6,
    )
    pdt.assert_frame_equal(
        ctl.results.dollars_holdings_at_next_t, ref.results.dollars_holdings_at_next_t,
        check_exact=False, rtol=1e-4, atol=1e-6,
    )
    pdt.assert_frame_equal(
        ctl.strategy.dollars_trades_unwind_pre, ref.strategy.dollars_trades_unwind_pre,
        check_exact=False, rtol=1e-4, atol=1e-6,
    )


def test_generate_trades_blocks_double_pending():
    ctl = _build_controller()
    periods = list(ctl.time_periods)
    _init_positions(ctl)
    ctl.generate_trades(periods[0])
    with pytest.raises(ValueError, match="pending trade"):
        ctl.generate_trades(periods[1])


def test_resume_requires_excluded_data(tmp_path):
    ctl = _build_controller()
    periods = list(ctl.time_periods)
    h = _init_positions(ctl)
    for t in periods[:SPLIT]:
        h = _step(ctl, h, t)

    # Simulate dehydrating without the big data frames (excluded to keep files small /
    # to force fresh data each day). Instance-level _excluded_attrs shadows the class set.
    fresh_returns = ctl.strategy.actual_returns
    fresh_weights = ctl.strategy.target_weights
    ctl.strategy._excluded_attrs = set(ctl.strategy._excluded_attrs) | {
        "actual_returns",
        "target_weights",
    }

    ctl.dehydrate_to_disk(str(tmp_path), "c.pkl")
    resumed = BacktestController.rehydrate_from_disk(str(tmp_path), "c.pkl")

    # The excluded data did not survive.
    assert getattr(resumed.strategy, "actual_returns", None) is None
    assert getattr(resumed.strategy, "target_weights", None) is None

    # Resuming without the required data fails loudly...
    with pytest.raises(ValueError, match="missing required data"):
        resumed.resume(periods[SPLIT:])

    # ...and succeeds once it's supplied.
    resumed.resume(
        periods[SPLIT:],
        strategy_data={
            "actual_returns": fresh_returns,
            "target_weights": fresh_weights,
        },
    )
    # t=0 row + every period now recorded.
    assert resumed.results.dollars_trades.shape[0] == len(periods) + 1
    assert resumed.strategy.dollars_trades_unwind_pre.shape[0] == len(periods)
