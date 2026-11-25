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

POINT_IN_TIME_STATES = ("normal", "transition", "break")

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
    "dynamic_top_n",
    "minimum_holdings",
    "maximum_holdings",
    "score_temperature",
    "maximum_sector_weight",
    "timing_mode",
    "timing_fast_days",
    "timing_slow_days",
    "timing_confirmation_days",
    "timing_reentry_days",
    "watch_exposure",
    "warning_exposure",
    "defensive_exposure",
    "market_drawdown_limit",
    "rebalance_on_timing_transition",
    "defensive_rotation_share",
    "defensive_holdings",
    "sector_core_weight",
    "sector_core_defensive_floor",
    "sector_core_weighting",
)


def family_evidence(selection_scores: pd.DataFrame) -> pd.DataFrame:
    grouped = selection_scores.groupby(["research_wave", "family"], dropna=False)
    rows: list[dict[str, object]] = []
    for (wave, family), frame in grouped:
        row: dict[str, object] = {
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
        if "regime_gate_passed" in frame:
            row.update(
                {
                    "regime_gate_pass_count": int(frame["regime_gate_passed"].sum()),
                    "regime_gate_pass_rate": float(frame["regime_gate_passed"].mean()),
                    "median_regime_robust_score": float(
                        frame["regime_robust_score"].median()
                    ),
                    "best_regime_robust_score": float(
                        frame["regime_robust_score"].max()
                    ),
                }
            )
        rows.append(row)
    return pd.DataFrame(rows).sort_values(
        ["preholdout_gate_pass_rate", "best_robust_score"],
        ascending=[False, False],
    )


def preholdout_pareto_frontier(selection_scores: pd.DataFrame) -> pd.DataFrame:
    candidates = selection_scores.loc[
        ~selection_scores["family"].str.startswith("comparator_")
    ].copy()
    candidates["cagr_floor"] = candidates[
        ["development_cagr", "validation_cagr"]
    ].min(axis=1)
    candidates["sharpe_floor"] = candidates[
        ["development_sharpe_zero_rf", "validation_sharpe_zero_rf"]
    ].min(axis=1)
    candidates["drawdown_floor"] = candidates[
        ["development_max_drawdown", "validation_max_drawdown"]
    ].min(axis=1)
    candidates["turnover_ceiling"] = candidates[
        ["development_annualized_turnover", "validation_annualized_turnover"]
    ].max(axis=1)
    objectives = candidates[
        ["cagr_floor", "sharpe_floor", "drawdown_floor", "turnover_ceiling"]
    ].to_numpy(dtype=float)
    objectives[:, 3] *= -1.0
    frontier = np.ones(len(candidates), dtype=bool)
    for position, row in enumerate(objectives):
        at_least_as_good = np.all(objectives >= row, axis=1)
        strictly_better = np.any(objectives > row, axis=1)
        frontier[position] = not bool(np.any(at_least_as_good & strictly_better))
    columns = [
        "variant_id",
        "research_wave",
        "family",
        "cagr_floor",
        "sharpe_floor",
        "drawdown_floor",
        "turnover_ceiling",
        "pre_holdout_gate_passed",
        "robust_score",
    ]
    return candidates.loc[frontier, columns].sort_values(
        ["cagr_floor", "sharpe_floor"],
        ascending=False,
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


def point_in_time_market_states(benchmark_close: pd.Series) -> pd.DataFrame:
    close = benchmark_close.astype(float).sort_index()
    returns = close.pct_change(fill_method=None)
    realized_volatility = returns.rolling(63, min_periods=42).std() * np.sqrt(252)
    trailing_threshold = (
        realized_volatility.shift(1)
        .rolling(756, min_periods=252)
        .quantile(0.75)
    )
    expanding_threshold = (
        realized_volatility.shift(1).expanding(min_periods=126).quantile(0.75)
    )
    volatility_threshold = trailing_threshold.fillna(expanding_threshold)
    drawdown = close.div(close.cummax()).sub(1.0)
    fast_trend = close.ge(close.rolling(63, min_periods=63).mean())
    slow_trend = close.ge(close.rolling(200, min_periods=200).mean())
    high_volatility = realized_volatility.ge(volatility_threshold).fillna(False)
    return_21d = close.pct_change(21, fill_method=None)
    return_63d = close.pct_change(63, fill_method=None)
    rapid_loss = return_21d.le(-0.05) | return_63d.le(-0.08)
    stress = (
        drawdown.le(-0.10) & ~fast_trend & (high_volatility | rapid_loss)
    ) | (rapid_loss & high_volatility & ~slow_trend)
    transition = ~stress & (
        ~fast_trend | ~slow_trend | drawdown.le(-0.05) | high_volatility
    )
    state = pd.Series(
        np.select([stress, transition], ["break", "transition"], default="normal"),
        index=close.index,
        name="market_state",
    )
    return pd.DataFrame(
        {
            "market_state": state,
            "drawdown": drawdown,
            "realized_volatility_63d": realized_volatility,
            "trailing_volatility_75th": volatility_threshold,
            "fast_trend_positive": fast_trend,
            "slow_trend_positive": slow_trend,
        }
    )


def preholdout_regime_diagnostics(
    candidate: pd.Series,
    benchmark: pd.Series,
    states: pd.DataFrame,
) -> dict[str, float]:
    aligned = pd.concat(
        [candidate.rename("candidate"), benchmark.rename("benchmark")],
        axis=1,
    ).dropna()
    labels = states["market_state"].reindex(aligned.index)
    result: dict[str, float] = {}
    for state in POINT_IN_TIME_STATES:
        selected = aligned.loc[labels.eq(state)]
        result[f"{state}_annualized_excess"] = (
            float((selected["candidate"] - selected["benchmark"]).mean() * 252)
            if not selected.empty
            else 0.0
        )
    result["worst_state_annualized_excess"] = min(
        result[f"{state}_annualized_excess"] for state in POINT_IN_TIME_STATES
    )
    return result


def state_conditioned_evidence(
    returns_by_name: Mapping[str, pd.Series],
    states: pd.DataFrame,
    *,
    benchmark_name: str,
) -> pd.DataFrame:
    benchmark = returns_by_name[benchmark_name]
    rows: list[dict[str, object]] = []
    labels = states["market_state"]
    for state in POINT_IN_TIME_STATES:
        state_index = labels.index[labels.eq(state)]
        for name, returns in returns_by_name.items():
            paired = pd.concat(
                [returns.rename("strategy"), benchmark.rename("benchmark")],
                axis=1,
            ).reindex(state_index).dropna()
            if paired.empty:
                continue
            strategy = paired["strategy"]
            benchmark_selected = paired["benchmark"]
            volatility = float(strategy.std(ddof=1) * np.sqrt(252))
            annualized = float(strategy.mean() * 252)
            losses = strategy[strategy <= strategy.quantile(0.05)]
            down = benchmark_selected < 0.0
            up = benchmark_selected > 0.0
            rows.append(
                {
                    "market_state": state,
                    "strategy": name,
                    "sessions": int(len(strategy)),
                    "annualized_arithmetic_return": annualized,
                    "annualized_excess_vs_spy": float(
                        (strategy - benchmark_selected).mean() * 252
                    ),
                    "annualized_volatility": volatility,
                    "sharpe_zero_rf": annualized / volatility if volatility else 0.0,
                    "compounded_state_contribution": float(
                        (1.0 + strategy).prod() - 1.0
                    ),
                    "worst_day": float(strategy.min()),
                    "cvar_95_daily": float(losses.mean()) if not losses.empty else 0.0,
                    "down_market_capture": _capture_ratio(
                        strategy.loc[down],
                        benchmark_selected.loc[down],
                    ),
                    "up_market_capture": _capture_ratio(
                        strategy.loc[up],
                        benchmark_selected.loc[up],
                    ),
                }
            )
    return pd.DataFrame(rows)


def regime_break_event_evidence(
    returns_by_name: Mapping[str, pd.Series],
    states: pd.DataFrame,
    *,
    benchmark_name: str,
    minimum_break_sessions: int = 5,
    merge_gap_sessions: int = 20,
    lead_recovery_sessions: int = 63,
) -> pd.DataFrame:
    index = states.index
    episodes = _stress_episodes(
        states["market_state"].eq("break"),
        minimum_sessions=minimum_break_sessions,
        merge_gap_sessions=merge_gap_sessions,
    )
    benchmark = returns_by_name[benchmark_name].reindex(index)
    rows: list[dict[str, object]] = []
    for number, (start_position, end_position) in enumerate(episodes, start=1):
        phases = {
            "lead_in": (
                max(0, start_position - lead_recovery_sessions),
                max(0, start_position - 1),
            ),
            "break": (start_position, end_position),
            "recovery": (
                min(len(index) - 1, end_position + 1),
                min(len(index) - 1, end_position + lead_recovery_sessions),
            ),
        }
        event = f"break_{number:02d}_{index[start_position].date().isoformat()}"
        for phase, (phase_start, phase_end) in phases.items():
            if phase_end < phase_start:
                continue
            phase_index = index[phase_start : phase_end + 1]
            benchmark_phase = benchmark.reindex(phase_index).fillna(0.0)
            for name, returns in returns_by_name.items():
                selected = returns.reindex(phase_index).fillna(0.0)
                equity = (1.0 + selected).cumprod()
                drawdown = equity.div(equity.cummax()).sub(1.0)
                rows.append(
                    {
                        "event": event,
                        "event_start": index[start_position].date().isoformat(),
                        "event_end": index[end_position].date().isoformat(),
                        "phase": phase,
                        "strategy": name,
                        "sessions": int(len(selected)),
                        "return": float((1.0 + selected).prod() - 1.0),
                        "excess_vs_spy": float(
                            (1.0 + selected).prod()
                            - (1.0 + benchmark_phase).prod()
                        ),
                        "max_drawdown": float(drawdown.min()),
                        "worst_day": float(selected.min()),
                    }
                )
    return pd.DataFrame(rows)


def rolling_outperformance_evidence(
    returns_by_name: Mapping[str, pd.Series],
    *,
    benchmark_names: tuple[str, ...],
    windows: tuple[int, ...] = (252, 756),
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for strategy_name, strategy in returns_by_name.items():
        if strategy_name in benchmark_names:
            continue
        for benchmark_name in benchmark_names:
            benchmark = returns_by_name[benchmark_name]
            paired = pd.concat(
                [strategy.rename("strategy"), benchmark.rename("benchmark")],
                axis=1,
            ).dropna()
            for window in windows:
                if len(paired) < window:
                    continue
                strategy_rolling = np.expm1(
                    np.log1p(paired["strategy"].clip(lower=-0.999999))
                    .rolling(window)
                    .sum()
                    * (252.0 / window)
                )
                benchmark_rolling = np.expm1(
                    np.log1p(paired["benchmark"].clip(lower=-0.999999))
                    .rolling(window)
                    .sum()
                    * (252.0 / window)
                )
                excess = (strategy_rolling - benchmark_rolling).dropna()
                rows.append(
                    {
                        "strategy": strategy_name,
                        "benchmark": benchmark_name,
                        "window_sessions": window,
                        "observations": int(len(excess)),
                        "beat_share": float(excess.gt(0.0).mean()),
                        "median_annualized_excess": float(excess.median()),
                        "p10_annualized_excess": float(excess.quantile(0.10)),
                        "worst_annualized_excess": float(excess.min()),
                        "latest_annualized_excess": float(excess.iloc[-1]),
                    }
                )
    return pd.DataFrame(rows)


def _stress_episodes(
    stress: pd.Series,
    *,
    minimum_sessions: int,
    merge_gap_sessions: int,
) -> list[tuple[int, int]]:
    positions = np.flatnonzero(stress.fillna(False).to_numpy(dtype=bool))
    if not len(positions):
        return []
    raw: list[tuple[int, int]] = []
    start = int(positions[0])
    end = start
    for position in positions[1:]:
        position = int(position)
        if position == end + 1:
            end = position
        else:
            raw.append((start, end))
            start = end = position
    raw.append((start, end))
    merged: list[tuple[int, int]] = []
    for start, end in raw:
        if merged and start - merged[-1][1] - 1 <= merge_gap_sessions:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return [episode for episode in merged if episode[1] - episode[0] + 1 >= minimum_sessions]


def _capture_ratio(strategy: pd.Series, benchmark: pd.Series) -> float:
    benchmark_mean = float(benchmark.mean()) if not benchmark.empty else 0.0
    if abs(benchmark_mean) < 1e-12:
        return 0.0
    return float(strategy.mean() / benchmark_mean)


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
