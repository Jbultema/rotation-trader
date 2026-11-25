from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from statistics import NormalDist

import numpy as np
import pandas as pd

from rotation_trader.config import PromotionConfig, ResearchConfig
from rotation_trader.metrics import performance_metrics


@dataclass(frozen=True)
class SelectionResult:
    selected_variant_id: str | None
    eligible_variants: int
    family_winners: tuple[str, ...]
    reason: str


def period_masks(index: pd.DatetimeIndex, config: ResearchConfig) -> dict[str, pd.Series]:
    return {
        "development": pd.Series(index <= pd.Timestamp(config.development_end), index=index),
        "validation": pd.Series(
            (index >= pd.Timestamp(config.validation_start))
            & (index <= pd.Timestamp(config.validation_end)),
            index=index,
        ),
        "holdout": pd.Series(
            (index >= pd.Timestamp(config.holdout_start))
            & (index <= pd.Timestamp(config.holdout_end)),
            index=index,
        ),
        "forward_diagnostic": pd.Series(
            index >= pd.Timestamp(config.forward_diagnostic_start),
            index=index,
        ),
    }


def evaluate_periods(
    variant_id: str,
    returns: pd.Series,
    turnover: pd.Series,
    config: ResearchConfig,
    periods: tuple[str, ...] | None = None,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for period, mask in period_masks(returns.index, config).items():
        if periods is not None and period not in periods:
            continue
        selected = mask[mask].index
        if selected.empty:
            continue
        metrics = performance_metrics(
            returns.reindex(selected),
            turnover=turnover.reindex(selected),
        )
        rows.append({"variant_id": variant_id, "period": period, **metrics})
    return rows


def select_pre_holdout_candidate(
    metrics: pd.DataFrame,
    registry: pd.DataFrame,
    promotion: PromotionConfig,
) -> tuple[SelectionResult, pd.DataFrame]:
    allowed = metrics[metrics["period"].isin(["development", "validation"])].copy()
    pivot = allowed.pivot(index="variant_id", columns="period")
    summary = pd.DataFrame(index=pivot.index)
    for metric in ("cagr", "sharpe_zero_rf", "max_drawdown", "annualized_turnover"):
        for period in ("development", "validation"):
            summary[f"{period}_{metric}"] = pivot[(metric, period)]
    optional = [
        column
        for column in (
            "family",
            "research_wave",
            "preholdout_return_correlation_to_swing",
            "walk_forward_positive_share",
        )
        if column in registry
    ]
    summary = summary.join(registry.set_index("variant_id")[optional])
    summary["robust_score"] = (
        0.45 * summary[["development_sharpe_zero_rf", "validation_sharpe_zero_rf"]].min(axis=1)
        + 0.35 * summary[["development_cagr", "validation_cagr"]].min(axis=1)
        + 0.20 * summary[["development_max_drawdown", "validation_max_drawdown"]].min(axis=1)
        - 0.005 * summary["validation_annualized_turnover"].clip(lower=0.0)
    )
    summary["pre_holdout_gate_passed"] = (
        (summary["development_cagr"] >= promotion.minimum_development_cagr)
        & (summary["validation_cagr"] >= promotion.minimum_validation_cagr)
        & (summary["validation_sharpe_zero_rf"] >= promotion.minimum_validation_sharpe)
        & (summary["validation_max_drawdown"] >= promotion.maximum_validation_drawdown)
        & (summary["validation_annualized_turnover"] <= promotion.maximum_annual_turnover)
        & ~summary["family"].str.startswith("comparator_")
    )
    if "preholdout_return_correlation_to_swing" in summary:
        summary["pre_holdout_gate_passed"] &= (
            summary["preholdout_return_correlation_to_swing"].abs() < 0.97
        )
    if "walk_forward_positive_share" in summary:
        summary["pre_holdout_gate_passed"] &= (
            summary["walk_forward_positive_share"]
            >= promotion.minimum_positive_walk_forward_windows
        )
    ordered = summary.sort_values(
        ["pre_holdout_gate_passed", "robust_score"],
        ascending=[False, False],
    )
    family_winners = (
        ordered.sort_values("robust_score", ascending=False)
        .groupby("family", sort=False)
        .head(1)
        .index.tolist()
    )
    eligible = ordered[ordered["pre_holdout_gate_passed"]]
    selected = str(eligible.index[0]) if not eligible.empty else None
    reason = (
        "highest robust development-validation score among rotation-specific gated variants"
        if selected is not None
        else "no rotation-specific variant passed the frozen pre-holdout gate"
    )
    return (
        SelectionResult(selected, int(len(eligible)), tuple(family_winners), reason),
        ordered.reset_index(),
    )


def combinatorial_pbo(
    returns_by_variant: pd.DataFrame,
    *,
    partitions: int,
) -> dict[str, float | int]:
    clean = returns_by_variant.dropna(how="all").fillna(0.0)
    if partitions % 2 or partitions < 4:
        raise ValueError("PBO partitions must be an even integer of at least four.")
    blocks = [
        np.asarray(block, dtype=int) for block in np.array_split(np.arange(len(clean)), partitions)
    ]
    logits: list[float] = []
    half = partitions // 2
    combinations = list(itertools.combinations(range(partitions), half))
    for chosen in combinations[: len(combinations) // 2]:
        in_sample = np.concatenate([blocks[position] for position in chosen])
        out_positions = [position for position in range(partitions) if position not in chosen]
        out_sample = np.concatenate([blocks[position] for position in out_positions])
        in_score = _sharpe_vector(clean.iloc[in_sample])
        winner_position = int(np.nanargmax(in_score.to_numpy()))
        out_score = _sharpe_vector(clean.iloc[out_sample])
        winner_score = float(out_score.iloc[winner_position])
        rank = float((out_score < winner_score).sum() + 0.5 * (out_score == winner_score).sum())
        relative_rank = min(max(rank / len(out_score), 1e-9), 1.0 - 1e-9)
        logits.append(math.log(relative_rank / (1.0 - relative_rank)))
    values = np.asarray(logits)
    return {
        "partitions": partitions,
        "combinatorial_splits": int(len(values)),
        "probability_selected_below_oos_median": float((values <= 0.0).mean()),
        "median_oos_rank_logit": float(np.median(values)),
    }


def deflated_sharpe_diagnostic(
    selected_returns: pd.Series,
    all_returns: pd.DataFrame,
) -> dict[str, float | int]:
    clean = all_returns.fillna(0.0)
    trial_sharpes = _sharpe_vector(clean) / math.sqrt(252)
    trials = len(trial_sharpes)
    mean_trial = float(trial_sharpes.mean())
    std_trial = float(trial_sharpes.std(ddof=1))
    normal = NormalDist()
    euler_gamma = 0.5772156649015329
    if trials <= 1 or std_trial == 0.0:
        expected_max = mean_trial
    else:
        expected_standard_max = (1.0 - euler_gamma) * normal.inv_cdf(
            1.0 - 1.0 / trials
        ) + euler_gamma * normal.inv_cdf(1.0 - 1.0 / (trials * math.e))
        expected_max = mean_trial + std_trial * expected_standard_max
    values = selected_returns.fillna(0.0)
    selected_daily_sharpe = float(values.mean() / values.std(ddof=1))
    skew = float(values.skew())
    kurtosis = float(values.kurt() + 3.0)
    denominator = math.sqrt(
        max(
            1e-12,
            1.0
            - skew * selected_daily_sharpe
            + ((kurtosis - 1.0) / 4.0) * selected_daily_sharpe**2,
        )
    )
    z_score = (
        (selected_daily_sharpe - expected_max) * math.sqrt(max(len(values) - 1, 1)) / denominator
    )
    return {
        "trials": trials,
        "selected_annualized_sharpe": selected_daily_sharpe * math.sqrt(252),
        "expected_max_daily_sharpe_under_trials": expected_max,
        "deflated_sharpe_probability": float(normal.cdf(z_score)),
    }


def paired_block_bootstrap(
    candidate: pd.Series,
    benchmark: pd.Series,
    *,
    samples: int,
    block_sessions: int,
    seed: int,
) -> dict[str, float | int]:
    paired = pd.concat([candidate.rename("candidate"), benchmark.rename("benchmark")], axis=1)
    paired = paired.dropna()
    differences = paired["candidate"] - paired["benchmark"]
    rng = np.random.default_rng(seed)
    n = len(differences)
    estimates = np.empty(samples)
    for sample in range(samples):
        values: list[float] = []
        while len(values) < n:
            start = int(rng.integers(0, max(1, n - block_sessions + 1)))
            values.extend(differences.iloc[start : start + block_sessions].tolist())
        estimates[sample] = float(np.mean(values[:n]) * 252)
    return {
        "samples": samples,
        "block_sessions": block_sessions,
        "annualized_mean_excess_median": float(np.median(estimates)),
        "annualized_mean_excess_ci_2_5": float(np.quantile(estimates, 0.025)),
        "annualized_mean_excess_ci_97_5": float(np.quantile(estimates, 0.975)),
        "probability_positive_annualized_mean_excess": float((estimates > 0.0).mean()),
    }


def walk_forward_relative_stability(
    candidate: pd.Series,
    benchmark: pd.Series,
) -> dict[str, object]:
    windows = (
        ("2000-2004", "2000-01-01", "2004-12-31"),
        ("2005-2008", "2005-01-01", "2008-12-31"),
        ("2009-2011", "2009-01-01", "2011-12-31"),
        ("2012-2014", "2012-01-01", "2014-12-31"),
        ("2015-2018", "2015-01-01", "2018-12-31"),
    )
    rows: list[dict[str, object]] = []
    for name, start, end in windows:
        difference = candidate.loc[start:end].fillna(0.0) - benchmark.loc[start:end].fillna(0.0)
        rows.append(
            {
                "window": name,
                "sessions": int(len(difference)),
                "annualized_mean_excess": float(difference.mean() * 252),
                "positive": bool(difference.mean() > 0.0),
            }
        )
    return {
        "windows": rows,
        "positive_window_share": float(np.mean([row["positive"] for row in rows])),
    }


def behavioral_similarity(
    candidate_returns: pd.Series,
    comparator_returns: pd.Series,
    candidate_weights: pd.DataFrame,
    comparator_weights: pd.DataFrame,
) -> dict[str, float]:
    aligned_returns = pd.concat(
        [candidate_returns.rename("candidate"), comparator_returns.rename("comparator")],
        axis=1,
    ).dropna()
    candidate = candidate_weights.reindex_like(comparator_weights).fillna(0.0)
    comparator = comparator_weights.fillna(0.0)
    daily_distance = (candidate - comparator).abs().sum(axis=1).clip(upper=2.0) / 2.0
    return {
        "return_correlation": float(aligned_returns.corr().iloc[0, 1]),
        "mean_weight_overlap": float((1.0 - daily_distance).mean()),
        "different_weight_day_share": float((daily_distance > 0.05).mean()),
    }


def _sharpe_vector(frame: pd.DataFrame) -> pd.Series:
    mean = frame.mean(axis=0)
    std = frame.std(axis=0, ddof=1).replace(0.0, np.nan)
    return mean.div(std).fillna(-np.inf) * math.sqrt(252)
