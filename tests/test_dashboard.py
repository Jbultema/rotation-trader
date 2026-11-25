import json
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest


def test_dashboard_executes_without_runtime_exceptions(
    tmp_path: Path,
    monkeypatch,
) -> None:
    summary = {
        "promotion_status": "research_candidate_not_promoted",
        "protocol_phase": "post_holdout_adversarial_wave_2",
        "selected_variant_id": "rotation-test",
        "variants_tested": 100,
        "latest_decision": {
            "as_of_close": "2026-11-23",
            "leadership_state": "transition",
            "breadth": 0.55,
            "cash_weight": 0.0,
            "target_weights": {"XLE": 0.5, "XLV": 0.5},
            "sector_ranks": {"XLE": 2.0, "XLV": 1.0, "XLP": 3.0},
        },
        "allocation_timing_challenger": {
            "family": "volatility_managed_rotation",
            "latest_decision": {
                "timing_stage": 1,
                "sleeve_exposure": 0.4,
                "target_holding_count": 3,
                "target_weights": {"XLE": 0.1, "XLP": 0.15, "XLV": 0.15},
            },
        },
        "behavioral_distinctness": {
            "return_correlation": 0.8,
            "mean_weight_overlap": 0.6,
            "different_weight_day_share": 0.8,
        },
        "promotion_gates": {"distinct": True, "multiple_testing": False},
    }
    (tmp_path / "research_summary.json").write_text(
        json.dumps(summary),
        encoding="utf-8",
    )
    dates = pd.bdate_range("2024-01-02", periods=20)
    comparison = pd.DataFrame(
        {
            "rotation_candidate": 0.001,
            "allocation_timing_challenger": 0.0009,
            "swing_sector_control": 0.0008,
            "spy_buy_hold": 0.0006,
            "equal_weight_sectors": 0.0007,
        },
        index=dates,
    )
    comparison.to_parquet(tmp_path / "comparison_returns.parquet")
    pd.DataFrame(
        {
            "regime": ["forward"] * 5,
            "strategy": comparison.columns,
            "cagr": [0.1, 0.095, 0.09, 0.08, 0.07],
        }
    ).to_csv(tmp_path / "regime_comparison.csv", index=False)
    pd.DataFrame(
        {
            "family": ["transition"],
            "research_wave": [1],
            "variants": [100],
            "preholdout_gate_pass_count": [1],
            "preholdout_gate_pass_rate": [0.01],
            "best_robust_score": [0.2],
            "median_robust_score": [0.1],
        }
    ).to_csv(tmp_path / "family_preholdout_evidence.csv", index=False)
    monkeypatch.setenv("ROTATION_TRADER_REPORT_DIR", str(tmp_path))
    dashboard = Path(__file__).parents[1] / "src/rotation_trader/dashboard.py"
    app = AppTest.from_file(dashboard, default_timeout=30)

    app.run()

    assert not app.exception
    assert [title.value for title in app.title] == ["Rotation Trader"]
    assert len(app.metric) == 12
    assert len(app.get("plotly_chart")) == 6
