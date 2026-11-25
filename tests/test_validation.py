import numpy as np
import pandas as pd

from rotation_trader.config import PromotionConfig
from rotation_trader.validation import (
    combinatorial_pbo,
    paired_block_bootstrap,
    select_pre_holdout_candidate,
)


def test_selector_uses_only_development_and_validation() -> None:
    rows = []
    for variant, development, validation, holdout in (
        ("stable", 0.10, 0.09, -0.50),
        ("holdout_star", 0.07, 0.07, 1.50),
    ):
        for period, cagr in (
            ("development", development),
            ("validation", validation),
            ("holdout", holdout),
        ):
            rows.append(
                {
                    "variant_id": variant,
                    "period": period,
                    "cagr": cagr,
                    "sharpe_zero_rf": cagr * 10,
                    "max_drawdown": -0.2,
                    "annualized_turnover": 2.0,
                }
            )
    metrics = pd.DataFrame(rows)
    registry = pd.DataFrame(
        {"variant_id": ["stable", "holdout_star"], "family": ["rotation", "rotation"]}
    )
    promotion = PromotionConfig(0.06, 0.06, 0.45, -0.35, 12.0, 0.6)

    selection, _ = select_pre_holdout_candidate(metrics, registry, promotion)

    assert selection.selected_variant_id == "stable"


def test_pbo_and_bootstrap_are_deterministic() -> None:
    rng = np.random.default_rng(7)
    dates = pd.bdate_range("2010-01-04", periods=504)
    returns = pd.DataFrame(
        rng.normal(0.0003, 0.01, size=(len(dates), 6)),
        index=dates,
        columns=[f"v{value}" for value in range(6)],
    )

    first = combinatorial_pbo(returns, partitions=4)
    second = combinatorial_pbo(returns, partitions=4)
    bootstrap = paired_block_bootstrap(
        returns["v0"],
        returns["v1"],
        samples=100,
        block_sessions=21,
        seed=42,
    )

    assert first == second
    assert 0.0 <= first["probability_selected_below_oos_median"] <= 1.0
    assert bootstrap["samples"] == 100
    assert 0.0 <= bootstrap["probability_positive_annualized_mean_excess"] <= 1.0
