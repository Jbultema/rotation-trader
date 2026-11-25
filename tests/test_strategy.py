import numpy as np
import pandas as pd

from rotation_trader.strategy import FeatureCache, VariantSpec, build_strategy, rebalance_mask


def _prices() -> tuple[pd.DataFrame, pd.Series]:
    dates = pd.bdate_range("2020-01-02", periods=420)
    trend = np.linspace(100.0, 180.0, len(dates))
    close = pd.DataFrame(
        {
            "XLE": trend * (1.0 + np.r_[np.zeros(300), np.linspace(0.0, 0.5, 120)]),
            "XLV": trend * 1.05,
            "XLP": trend * 0.95,
        },
        index=dates,
    )
    benchmark = pd.Series(trend, index=dates, name="SPY")
    return close, benchmark


def test_monthly_rebalance_marks_only_last_session_of_each_month() -> None:
    dates = pd.bdate_range("2026-01-05", "2026-03-10")
    mask = rebalance_mask(dates, "monthly")

    selected = dates[mask]
    assert selected[0] == pd.Timestamp("2026-01-30")
    assert selected[1] == pd.Timestamp("2026-02-27")
    assert selected[2] == pd.Timestamp("2026-03-10")


def test_rotation_strategy_is_long_only_latched_and_bounded() -> None:
    close, benchmark = _prices()
    spec = VariantSpec(
        family="acceleration",
        momentum_lookbacks=(63, 126),
        momentum_weights=(0.5, 0.5),
        top_n=2,
        acceleration_weight=0.5,
    )

    result = build_strategy(FeatureCache(close, benchmark), spec)

    assert result.target_weights.min().min() >= 0.0
    assert result.target_weights.sum(axis=1).max() <= 1.0 + 1e-12
    changes = result.target_weights.diff().abs().sum(axis=1) > 1e-12
    assert not changes[~result.rebalance].any()


def test_rank_acceleration_changes_late_leadership_score() -> None:
    close, benchmark = _prices()
    close.loc[close.index[-63] :, "XLE"] *= np.geomspace(1.0, 3.0, 63)
    plain = VariantSpec(
        family="comparator",
        momentum_lookbacks=(126,),
        momentum_weights=(1.0,),
        top_n=1,
        absolute_gate=False,
    )
    accelerated = VariantSpec(
        family="acceleration",
        momentum_lookbacks=(126,),
        momentum_weights=(1.0,),
        top_n=1,
        absolute_gate=False,
        acceleration_weight=0.75,
    )
    cache = FeatureCache(close, benchmark)

    plain_run = build_strategy(cache, plain)
    accelerated_run = build_strategy(cache, accelerated)

    assert accelerated_run.score.iloc[-1]["XLE"] > plain_run.score.iloc[-1]["XLE"]


def test_context_echo_is_confirmation_only_and_changes_sector_scores() -> None:
    close, benchmark = _prices()
    context = pd.DataFrame(
        {
            "DBC": np.geomspace(100.0, 300.0, len(close)),
            "QQQ": np.geomspace(100.0, 105.0, len(close)),
            "SMH": np.geomspace(100.0, 102.0, len(close)),
            "IEF": np.geomspace(100.0, 90.0, len(close)),
        },
        index=close.index,
    )
    spec = VariantSpec(
        family="context_echo_confirmation",
        momentum_lookbacks=(126,),
        momentum_weights=(1.0,),
        top_n=1,
        absolute_gate=False,
        context_echo_weight=0.5,
    )

    without_context = build_strategy(FeatureCache(close, benchmark), spec)
    with_context = build_strategy(FeatureCache(close, benchmark, context), spec)

    assert not with_context.score.equals(without_context.score)
    assert set(with_context.target_weights.columns) == set(close.columns)
    assert with_context.target_weights.sum(axis=1).max() <= 1.0


def test_score_weighting_dynamic_holdings_and_caps_are_effective() -> None:
    close, benchmark = _prices()
    spec = VariantSpec(
        family="adaptive_allocation",
        momentum_lookbacks=(63, 126),
        momentum_weights=(0.4, 0.6),
        top_n=3,
        weighting="score_softmax",
        absolute_gate=False,
        dynamic_top_n=True,
        minimum_holdings=2,
        maximum_holdings=3,
        score_temperature=0.5,
        maximum_sector_weight=0.6,
        acceleration_weight=0.5,
    )

    result = build_strategy(FeatureCache(close, benchmark), spec)
    latest = result.target_weights.loc[result.target_weights.sum(axis=1).gt(0.0)].iloc[-1]

    assert latest.max() <= 0.6 + 1e-12
    assert latest[latest.gt(0.0)].nunique() > 1
    counts = result.diagnostics["target_holding_count"]
    assert counts[counts.gt(0)].between(2, 3).all()


def test_staged_timing_creates_partial_exposure_and_transition_rebalances() -> None:
    close, benchmark = _prices()
    benchmark.iloc[-140:] = np.geomspace(benchmark.iloc[-140], 70.0, 140)
    spec = VariantSpec(
        family="staged_timing",
        momentum_lookbacks=(63, 126),
        momentum_weights=(0.5, 0.5),
        top_n=2,
        weighting="score_inverse_volatility",
        absolute_gate=False,
        acceleration_weight=0.5,
        timing_mode="staged",
        timing_fast_days=42,
        timing_slow_days=100,
        timing_confirmation_days=3,
        watch_exposure=0.75,
        warning_exposure=0.5,
        defensive_exposure=0.2,
        rebalance_on_timing_transition=True,
    )

    result = build_strategy(FeatureCache(close, benchmark), spec)

    assert set(result.diagnostics["timing_stage"].unique()).issubset({0, 1, 2, 3})
    assert result.diagnostics["timing_exposure"].nunique() > 1
    assert result.target_weights.sum(axis=1).between(0.0, 1.0 + 1e-12).all()
    scheduled = rebalance_mask(close.index, spec.cadence)
    assert (result.rebalance & ~scheduled).any()
