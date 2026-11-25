import numpy as np
import pandas as pd

from rotation_trader.evidence import (
    annual_evidence,
    family_evidence,
    parameter_neighborhood,
    point_in_time_market_states,
    preholdout_pareto_frontier,
    regime_break_event_evidence,
    rolling_outperformance_evidence,
    state_conditioned_evidence,
)


def test_family_evidence_counts_passes() -> None:
    frame = pd.DataFrame(
        {
            "research_wave": [1, 1],
            "family": ["rotation", "rotation"],
            "pre_holdout_gate_passed": [True, False],
            "robust_score": [0.2, 0.1],
            "development_cagr": [0.1, 0.0],
            "validation_cagr": [0.1, 0.0],
            "validation_sharpe_zero_rf": [0.8, 0.1],
            "walk_forward_positive_share": [0.8, 0.2],
            "preholdout_return_correlation_to_swing": [0.8, 0.7],
        }
    )

    result = family_evidence(frame).iloc[0]

    assert result["preholdout_gate_pass_count"] == 1
    assert result["preholdout_gate_pass_rate"] == 0.5


def test_parameter_neighborhood_excludes_distant_variants() -> None:
    registry = pd.DataFrame(
        {
            "variant_id": ["selected", "near", "far"],
            "family": ["rotation"] * 3,
            "top_n": [2, 3, 4],
            "cadence": ["monthly", "monthly", "weekly"],
            "weighting": ["equal", "equal", "inverse_volatility"],
            "momentum_lookbacks": [(63, 126), (63, 126), (126, 252)],
        }
    )
    scores = pd.DataFrame(
        {
            "variant_id": registry["variant_id"],
            "development_cagr": 0.1,
            "validation_cagr": 0.1,
            "development_sharpe_zero_rf": 0.8,
            "validation_sharpe_zero_rf": 0.8,
            "development_max_drawdown": -0.2,
            "validation_max_drawdown": -0.2,
            "robust_score": [0.3, 0.2, 0.1],
            "pre_holdout_gate_passed": True,
        }
    )

    result = parameter_neighborhood("selected", registry, scores, maximum_distance=1)

    assert set(result["variant_id"]) == {"selected", "near"}


def test_annual_evidence_compounds_daily_returns() -> None:
    dates = pd.to_datetime(["2024-01-02", "2024-01-03"])
    result = annual_evidence({"candidate": pd.Series([0.1, -0.1], index=dates)})

    assert abs(result.iloc[0]["return"] + 0.01) < 1e-12


def test_pareto_frontier_excludes_strictly_dominated_variant() -> None:
    frame = pd.DataFrame(
        {
            "variant_id": ["strong", "weak"],
            "research_wave": [3, 3],
            "family": ["timing", "timing"],
            "development_cagr": [0.08, 0.06],
            "validation_cagr": [0.08, 0.06],
            "development_sharpe_zero_rf": [0.8, 0.6],
            "validation_sharpe_zero_rf": [0.8, 0.6],
            "development_max_drawdown": [-0.15, -0.20],
            "validation_max_drawdown": [-0.15, -0.20],
            "development_annualized_turnover": [5.0, 7.0],
            "validation_annualized_turnover": [5.0, 7.0],
            "pre_holdout_gate_passed": [True, False],
            "robust_score": [0.2, 0.1],
        }
    )

    result = preholdout_pareto_frontier(frame)

    assert result["variant_id"].tolist() == ["strong"]


def test_point_in_time_states_and_break_reports_separate_normal_from_stress() -> None:
    dates = pd.bdate_range("2018-01-02", periods=1_200)
    close = pd.Series(np.geomspace(100.0, 180.0, len(dates)), index=dates)
    close.iloc[-120:] = np.geomspace(close.iloc[-121], 100.0, 120)
    states = point_in_time_market_states(close)
    spy = close.pct_change(fill_method=None).fillna(0.0)
    protected = spy.where(~states["market_state"].eq("break"), 0.0)
    returns = {"candidate": protected, "spy_buy_hold": spy}

    conditioned = state_conditioned_evidence(
        returns,
        states,
        benchmark_name="spy_buy_hold",
    )
    events = regime_break_event_evidence(
        returns,
        states,
        benchmark_name="spy_buy_hold",
    )

    assert states.iloc[-1]["market_state"] == "break"
    assert set(conditioned["market_state"]) == {"normal", "transition", "break"}
    break_row = conditioned.loc[
        conditioned["market_state"].eq("break")
        & conditioned["strategy"].eq("candidate")
    ].iloc[0]
    assert break_row["annualized_excess_vs_spy"] > 0.0
    assert {"lead_in", "break"}.issubset(set(events["phase"]))


def test_rolling_outperformance_reports_multiple_buy_and_hold_benchmarks() -> None:
    dates = pd.bdate_range("2020-01-02", periods=800)
    returns = {
        "candidate": pd.Series(0.0005, index=dates),
        "spy_buy_hold": pd.Series(0.0003, index=dates),
        "qqq_buy_hold": pd.Series(0.0004, index=dates),
    }

    result = rolling_outperformance_evidence(
        returns,
        benchmark_names=("spy_buy_hold", "qqq_buy_hold"),
    )

    candidate = result.loc[result["strategy"].eq("candidate")]
    assert set(candidate["benchmark"]) == {"spy_buy_hold", "qqq_buy_hold"}
    assert candidate["beat_share"].eq(1.0).all()
