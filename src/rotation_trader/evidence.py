from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from rotation_trader.metrics import performance_metrics

REGIME_WINDOWS = (
    ("dotcom_unwind", "2000-01-03", "2002-12-31"),
    ("credit_expansion", "2003-01-02", "2006-12-29"),
    ("global_financial_crisis", "2007-01-03", "2009-03-09"),
    ("post_crisis_recovery", "2009-03-10", "2012-12-31"),
    ("low_vol_expansion", "2013-01-02", "2019-12-31"),
    ("pandemic_shock_recovery", "2020-01-02", "2020-12-31"),
    ("inflation_rate_shock", "2021-01-04", "2023-12-29"),
    ("ai_concentration_forward", "2024-01-02", "2099-12-31"),
)

PARAMETER_COLUMNS = (
    "momentum_lookbacks",
    "momentum_weights",
    "top_n",
    "cadence",
    "weighting",
    "absolute_gate",
    "sector_trend_days",
    "benchmark_trend_days",
    "acceleration_days",
    "acceleration_weight",
    "rank_velocity_days",
    "rank_velocity_weight",
    "persistence_days",
    "persistence_weight",
    "reversal_days",
    "reversal_weight",
    "group_rotation_days",
    "group_rotation_weight",
    "breadth_trend_days",
    "breadth_threshold",
    "dispersion_days",
    "dispersion_penalty",
    "rank_buffer",
    "minimum_holding_rebalances",
    "rank_crossing_days",
    "rank_crossing_weight",
    "pair_transition_days",
    "pair_transition_weight",
    "confirmation_min_signals",
    "confirmation_weight",
    "leader_crowding_penalty",
    "correlation_days",
    "correlation_rotation_scale",
    "context_echo_days",
    "context_echo_weight",
)


def family_evidence(selection_scores: pd.DataFrame) -> pd.DataFrame:
    grouped = selection_scores.groupby(["research_wave", "family"], dropna=False)
    rows: list[dict[str, object]] = []
    for (wave, family), frame in grouped:
        rows.append(
            {
                "research_wave": int(wave),
                "family": str(family),
                "variants": int(len(frame)),
                "preholdout_gate_pass_count": int(frame["pre_holdout_gate_passed"].sum()),
                "preholdout_gate_pass_rate": float(
                    frame["pre_holdout_gate_passed"].mean()
                ),
                "median_robust_score": float(frame["robust_score"].median()),
                "best_robust_score": float(frame["robust_score"].max()),
                "median_development_cagr": float(frame["development_cagr"].median()),
                "median_validation_cagr": float(frame["validation_cagr"].median()),
                "median_validation_sharpe": float(
                    frame["validation_sharpe_zero_rf"].median()
                ),
                "median_walk_forward_positive_share": float(
                    frame["walk_forward_positive_share"].median()
                ),
                "median_swing_return_correlation": float(
                    frame["preholdout_return_correlation_to_swing"].median()
                ),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["preholdout_gate_pass_rate", "best_robust_score"],
        ascending=[False, False],
    )


def parameter_neighborhood(
    selected_variant_id: str,
    registry: pd.DataFrame,
    selection_scores: pd.DataFrame,
    *,
    maximum_distance: int = 2,
) -> pd.DataFrame:
    selected_rows = registry.loc[registry["variant_id"].eq(selected_variant_id)]
    if selected_rows.empty:
        return pd.DataFrame()
    selected = selected_rows.iloc[0]
    family = registry.loc[registry["family"].eq(selected["family"])].copy()
    columns = [column for column in PARAMETER_COLUMNS if column in family]
    distances = np.zeros(len(family), dtype=int)
    for column in columns:
        left = family[column]
        right = selected[column]
        equal = left.map(
            lambda value, selected_value=right: _same_parameter_value(
                value,
                selected_value,
            )
        )
        distances += (~equal).to_numpy(dtype=int)
    family["parameter_distance"] = distances
    nearby = family.loc[family["parameter_distance"] <= maximum_distance]
    score_columns = [
        "variant_id",
        "development_cagr",
        "validation_cagr",
        "development_sharpe_zero_rf",
        "validation_sharpe_zero_rf",
        "development_max_drawdown",
        "validation_max_drawdown",
        "robust_score",
        "pre_holdout_gate_passed",
    ]
    return (
        nearby[["variant_id", "parameter_distance"]]
        .merge(selection_scores[score_columns], on="variant_id", how="left")
        .sort_values(["parameter_distance", "robust_score"], ascending=[True, False])
    )


def regime_evidence(returns_by_name: Mapping[str, pd.Series]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for regime, start, end in REGIME_WINDOWS:
        for name, returns in returns_by_name.items():
            selected = returns.loc[start:end]
            if selected.empty:
                continue
            rows.append(
                {
                    "regime": regime,
                    "strategy": name,
                    **performance_metrics(selected),
                }
            )
    return pd.DataFrame(rows)


def _same_parameter_value(left: object, right: object) -> bool:
    if isinstance(left, (list, tuple, np.ndarray)) or isinstance(
        right, (list, tuple, np.ndarray)
    ):
        return tuple(np.asarray(left).tolist()) == tuple(np.asarray(right).tolist())
    if pd.isna(left) and pd.isna(right):
        return True
    return bool(left == right)


def annual_evidence(returns_by_name: Mapping[str, pd.Series]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for name, returns in returns_by_name.items():
        for year, values in returns.groupby(returns.index.year):
            rows.append(
                {
                    "year": int(year),
                    "strategy": name,
                    "return": float((1.0 + values.fillna(0.0)).prod() - 1.0),
                    "worst_day": float(values.min()),
                    "positive_day_rate": float((values > 0.0).mean()),
                }
            )
    return pd.DataFrame(rows)
