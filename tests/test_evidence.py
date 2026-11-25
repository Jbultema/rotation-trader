import pandas as pd

from rotation_trader.evidence import (
    annual_evidence,
    family_evidence,
    parameter_neighborhood,
    preholdout_pareto_frontier,
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
