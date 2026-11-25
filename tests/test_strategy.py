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
