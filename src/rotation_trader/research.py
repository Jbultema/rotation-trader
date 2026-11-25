from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from rotation_trader.backtest import BacktestResult, run_backtest
from rotation_trader.config import AppConfig
from rotation_trader.evidence import (
    annual_evidence,
    family_evidence,
    parameter_neighborhood,
    regime_evidence,
)
from rotation_trader.hypotheses import generate_registered_variants, registry_frame
from rotation_trader.metrics import performance_metrics
from rotation_trader.provenance import file_sha256, write_hashed_json
from rotation_trader.strategy import FeatureCache, StrategyRun, VariantSpec, build_strategy
from rotation_trader.validation import (
    behavioral_similarity,
    combinatorial_pbo,
    deflated_sharpe_diagnostic,
    evaluate_periods,
    paired_block_bootstrap,
    period_masks,
    select_pre_holdout_candidate,
    walk_forward_relative_stability,
)


@dataclass(frozen=True)
class ResearchResult:
    run_dir: Path
    latest_dir: Path
    selected_variant_id: str | None
    promoted: bool
    variants_tested: int


def run_research(
    prices: pd.DataFrame,
    config: AppConfig,
    output_root: Path,
    *,
    price_manifest_path: Path | None = None,
    progress: Callable[[str], None] | None = None,
) -> ResearchResult:
    report = progress or (lambda _message: None)
    captured_at = datetime.now(UTC)
    run_id = captured_at.strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = output_root / "runs" / run_id
    latest_dir = output_root / "latest"
    run_dir.mkdir(parents=True, exist_ok=False)

    sectors = list(config.data.stable_sectors)
    close = prices["Close"][sectors].dropna(how="all")
    adjusted_open = prices["Open"][sectors].reindex(close.index)
    benchmark_close = prices["Close"][config.data.benchmark].reindex(close.index)
    benchmark_open = prices["Open"][config.data.benchmark].reindex(close.index)
    context_symbols = [
        ticker
        for ticker in config.data.context_tickers
        if ticker in prices["Close"].columns
    ]
    context_close = prices["Close"][context_symbols].reindex(close.index)
    common_start = max(close[ticker].first_valid_index() for ticker in sectors)
    analysis_start_position = (
        close.index.get_loc(common_start) + config.research.minimum_history_sessions
    )
    if analysis_start_position >= len(close):
        raise ValueError("Price history is too short for the configured research warmup.")
    analysis_start = close.index[analysis_start_position]
    close = close.loc[analysis_start:]
    adjusted_open = adjusted_open.loc[analysis_start:]
    benchmark_close = benchmark_close.loc[analysis_start:]
    benchmark_open = benchmark_open.loc[analysis_start:]
    context_close = context_close.loc[analysis_start:]
    if close.isna().any(axis=None) or adjusted_open.isna().any(axis=None):
        raise ValueError("Primary stable-sector history contains gaps after the research warmup.")

    cache = FeatureCache(close, benchmark_close, context_close)
    variants = generate_registered_variants()
    registry = registry_frame(variants)
    registry.to_csv(run_dir / "variant_registry_frozen.csv", index=False)
    report(f"Frozen {len(variants)} registered variants.")

    benchmark_result = _benchmark_backtest(
        benchmark_open,
        cost_bps=config.execution.total_one_way_cost_bps,
    )
    equal_sector_result = _equal_sector_backtest(
        adjusted_open,
        cost_bps=config.execution.total_one_way_cost_bps,
    )
    swing_spec = next(
        variant for variant in variants if variant.family == "comparator_swing_dual_momentum"
    )
    swing_run, swing_result = _run_variant(cache, adjusted_open, swing_spec, config)

    return_series_by_variant: dict[str, pd.Series] = {}
    turnover_series_by_variant: dict[str, pd.Series] = {}
    preholdout_metric_rows: list[dict[str, object]] = []
    preholdout_end = pd.Timestamp(config.research.validation_end)
    swing_preholdout = swing_result.net_returns.loc[:preholdout_end]
    benchmark_preholdout = benchmark_result.net_returns.loc[:preholdout_end]
    registry_updates: dict[str, dict[str, float]] = {}

    ordered = [swing_spec, *[variant for variant in variants if variant != swing_spec]]
    for position, variant in enumerate(ordered, start=1):
        if variant == swing_spec:
            strategy_run, result = swing_run, swing_result
        else:
            strategy_run, result = _run_variant(cache, adjusted_open, variant, config)
        return_series_by_variant[variant.variant_id] = result.net_returns.astype(np.float32)
        turnover_series_by_variant[variant.variant_id] = result.one_way_turnover.astype(
            np.float32
        )
        preholdout_metric_rows.extend(
            evaluate_periods(
                variant.variant_id,
                result.net_returns,
                result.one_way_turnover,
                config.research,
                periods=("development", "validation"),
            )
        )
        candidate_preholdout = result.net_returns.loc[:preholdout_end]
        correlation = float(
            pd.concat([candidate_preholdout, swing_preholdout], axis=1).corr().iloc[0, 1]
        )
        stability = walk_forward_relative_stability(
            candidate_preholdout,
            benchmark_preholdout,
        )
        registry_updates[variant.variant_id] = {
            "preholdout_return_correlation_to_swing": correlation,
            "walk_forward_positive_share": float(stability["positive_window_share"]),
        }
        if position % 100 == 0 or position == len(ordered):
            report(f"Evaluated {position}/{len(ordered)} variants without opening holdout metrics.")

    returns_by_variant = pd.DataFrame(return_series_by_variant, index=close.index)
    turnover_by_variant = pd.DataFrame(turnover_series_by_variant, index=close.index)
    registry = registry.join(
        pd.DataFrame.from_dict(registry_updates, orient="index"),
        on="variant_id",
    )
    registry.to_csv(run_dir / "variant_registry_preholdout.csv", index=False)
    preholdout_metrics = pd.DataFrame(preholdout_metric_rows)
    preholdout_metrics.to_csv(run_dir / "preholdout_metrics.csv", index=False)

    selection, selection_scores = select_pre_holdout_candidate(
        preholdout_metrics,
        registry,
        config.promotion,
    )
    selection_scores.to_csv(run_dir / "preholdout_selection_scores.csv", index=False)
    family_evidence(selection_scores).to_csv(
        run_dir / "family_preholdout_evidence.csv",
        index=False,
    )
    selection_payload = {
        "schema_version": 1,
        "record_type": "frozen_preholdout_selection",
        "selected_at_utc": datetime.now(UTC).isoformat(),
        "selected_variant_id": selection.selected_variant_id,
        "eligible_variants": selection.eligible_variants,
        "family_winners": list(selection.family_winners),
        "reason": selection.reason,
        "development_end": config.research.development_end,
        "validation_end": config.research.validation_end,
        "holdout_was_not_used_for_selection": True,
        "variant_registry_sha256": file_sha256(run_dir / "variant_registry_preholdout.csv"),
        "preholdout_metrics_sha256": file_sha256(run_dir / "preholdout_metrics.csv"),
        "selection_scores_sha256": file_sha256(run_dir / "preholdout_selection_scores.csv"),
    }
    write_hashed_json(run_dir / "selection_before_holdout.json", selection_payload)
    if selection.selected_variant_id is not None:
        parameter_neighborhood(
            selection.selected_variant_id,
            registry,
            selection_scores,
        ).to_csv(run_dir / "selected_parameter_neighborhood.csv", index=False)
    report(
        "Sealed pre-holdout selection: "
        + (selection.selected_variant_id or "no eligible candidate")
    )

    all_metric_rows: list[dict[str, object]] = []
    selected_ids = set(selection.family_winners)
    if selection.selected_variant_id is not None:
        selected_ids.add(selection.selected_variant_id)
    selected_ids.update(
        registry.loc[registry["family"].str.startswith("comparator_"), "variant_id"].tolist()
    )
    for variant_id in sorted(selected_ids):
        all_metric_rows.extend(
            evaluate_periods(
                variant_id,
                returns_by_variant[variant_id].astype(float),
                turnover_by_variant[variant_id].astype(float),
                config.research,
            )
        )
    for name, result in (
        ("benchmark_spy_buy_hold", benchmark_result),
        ("benchmark_equal_weight_sectors", equal_sector_result),
    ):
        all_metric_rows.extend(
            evaluate_periods(
                name,
                result.net_returns,
                result.one_way_turnover,
                config.research,
            )
        )
    all_metrics = pd.DataFrame(all_metric_rows)
    all_metrics.to_csv(run_dir / "selected_and_family_metrics.csv", index=False)

    preholdout_columns = returns_by_variant.index <= preholdout_end
    pbo = combinatorial_pbo(
        returns_by_variant.loc[preholdout_columns].astype(float),
        partitions=config.research.pbo_partitions,
    )
    write_hashed_json(run_dir / "pbo.json", pbo)

    promoted = False
    historical_gates_passed = False
    summary: dict[str, object] = {
        "run_id": run_id,
        "variants_tested": len(variants),
        "selected_variant_id": selection.selected_variant_id,
        "preholdout_eligible_variants": selection.eligible_variants,
        "pbo": pbo,
        "promotion_status": "no_preholdout_candidate",
        "protocol_phase": "post_holdout_adversarial_wave_2",
        "eligible_for_pristine_historical_promotion": False,
    }
    champion_run: StrategyRun | None = None
    champion_result: BacktestResult | None = None
    if selection.selected_variant_id is not None:
        champion_spec = next(
            variant for variant in variants if variant.variant_id == selection.selected_variant_id
        )
        champion_run, champion_result = _run_variant(
            cache,
            adjusted_open,
            champion_spec,
            config,
        )
        preholdout_returns = champion_result.net_returns.loc[:preholdout_end]
        holdout_mask = period_masks(champion_result.net_returns.index, config.research)["holdout"]
        holdout_index = holdout_mask[holdout_mask].index
        holdout_returns = champion_result.net_returns.reindex(holdout_index)
        holdout_benchmark = benchmark_result.net_returns.reindex(holdout_index)
        distinctness = behavioral_similarity(
            preholdout_returns,
            swing_preholdout,
            champion_run.target_weights.loc[:preholdout_end],
            swing_run.target_weights.loc[:preholdout_end],
        )
        walk_forward = walk_forward_relative_stability(
            preholdout_returns,
            benchmark_preholdout,
        )
        dsr = deflated_sharpe_diagnostic(
            preholdout_returns,
            returns_by_variant.loc[preholdout_columns].astype(float),
        )
        bootstrap_preholdout = paired_block_bootstrap(
            preholdout_returns,
            benchmark_preholdout,
            samples=config.research.bootstrap_samples,
            block_sessions=config.research.bootstrap_block_sessions,
            seed=config.research.random_seed,
        )
        bootstrap_holdout = paired_block_bootstrap(
            holdout_returns,
            holdout_benchmark,
            samples=config.research.bootstrap_samples,
            block_sessions=config.research.bootstrap_block_sessions,
            seed=config.research.random_seed + 1,
        )
        holdout_metrics = performance_metrics(
            holdout_returns,
            turnover=champion_result.one_way_turnover.reindex(holdout_index),
        )
        promotion_gates = {
            "return_correlation_below_0_97": distinctness["return_correlation"] < 0.97,
            "mean_weight_overlap_below_0_90": distinctness["mean_weight_overlap"] < 0.90,
            "walk_forward_positive_share": walk_forward["positive_window_share"]
            >= config.promotion.minimum_positive_walk_forward_windows,
            "positive_holdout_cagr": holdout_metrics["cagr"] > 0.0,
            "holdout_drawdown_within_limit": holdout_metrics["max_drawdown"]
            >= config.promotion.maximum_validation_drawdown,
            "deflated_sharpe_probability_at_least_0_50": dsr[
                "deflated_sharpe_probability"
            ]
            >= 0.50,
        }
        historical_gates_passed = all(promotion_gates.values())
        robustness = _robustness_checks(
            cache,
            adjusted_open,
            champion_spec,
            champion_run,
            config,
        )
        decision = _latest_decision(champion_spec, champion_run)
        summary.update(
            {
                "selected_specification": asdict(champion_spec),
                "behavioral_distinctness": distinctness,
                "walk_forward": walk_forward,
                "deflated_sharpe": dsr,
                "bootstrap_preholdout_vs_spy": bootstrap_preholdout,
                "bootstrap_holdout_vs_spy": bootstrap_holdout,
                "holdout_metrics": holdout_metrics,
                "robustness": robustness,
                "latest_decision": decision,
                "promotion_gates": promotion_gates,
                "historical_gates_passed": historical_gates_passed,
                "promotion_status": "historical_gates_passed_prospective_shadow_required"
                if historical_gates_passed
                else "research_candidate_not_promoted",
            }
        )
        champion_run.target_weights.to_parquet(run_dir / "champion_target_weights.parquet")
        swing_run.target_weights.to_parquet(run_dir / "swing_control_target_weights.parquet")
        champion_result.net_returns.rename("net_return").to_frame().to_parquet(
            run_dir / "champion_returns.parquet"
        )
        champion_run.diagnostics.to_parquet(run_dir / "champion_diagnostics.parquet")
        comparison_returns = {
            "rotation_candidate": champion_result.net_returns,
            "swing_sector_control": swing_result.net_returns,
            "spy_buy_hold": benchmark_result.net_returns,
            "equal_weight_sectors": equal_sector_result.net_returns,
        }
        pd.DataFrame(comparison_returns).to_parquet(run_dir / "comparison_returns.parquet")
        annual_evidence(comparison_returns).to_csv(
            run_dir / "annual_comparison.csv",
            index=False,
        )
        regime_evidence(comparison_returns).to_csv(
            run_dir / "regime_comparison.csv",
            index=False,
        )
        comparison_contract = {
            "schema_version": 1,
            "system": "rotation-trader",
            "mandate": "sector_leadership_transition",
            "protocol_phase": summary["protocol_phase"],
            "as_of_close": decision["as_of_close"],
            "selected_variant_id": selection.selected_variant_id,
            "promotion_status": summary["promotion_status"],
            "action_authorized": False,
            "target_weights": decision["target_weights"],
            "cash_weight": decision["cash_weight"],
            "leadership_state": decision["leadership_state"],
            "historical_gates_passed": historical_gates_passed,
            "behavioral_distinctness_from_swing_control": distinctness,
            "period_metrics": all_metrics.loc[
                all_metrics["variant_id"].isin(
                    [
                        selection.selected_variant_id,
                        swing_spec.variant_id,
                        "benchmark_spy_buy_hold",
                        "benchmark_equal_weight_sectors",
                    ]
                )
            ].to_dict(orient="records"),
            "execution": {
                "signal_observed": "completed_regular_session_close",
                "earliest_effective": "next_regular_session_open_after_human_review",
                "human_execution_required": True,
                "broker_integration": False,
            },
        }
        write_hashed_json(run_dir / "comparison_contract.json", comparison_contract)

    write_hashed_json(run_dir / "research_summary.json", summary)
    (run_dir / "research_report.md").write_text(
        _render_report(summary, all_metrics),
        encoding="utf-8",
    )
    manifest = {
        "schema_version": 1,
        "record_type": "rotation_research_run",
        "run_id": run_id,
        "created_at_utc": captured_at.isoformat(),
        "price_manifest": None if price_manifest_path is None else str(price_manifest_path),
        "price_manifest_sha256": (
            None if price_manifest_path is None else file_sha256(price_manifest_path)
        ),
        "variants_tested": len(variants),
        "selected_variant_id": selection.selected_variant_id,
        "promoted": promoted,
        "artifacts": {
            path.name: file_sha256(path) for path in sorted(run_dir.iterdir()) if path.is_file()
        },
    }
    write_hashed_json(run_dir / "run_manifest.json", manifest)
    _replace_latest(run_dir, latest_dir)
    return ResearchResult(
        run_dir,
        latest_dir,
        selection.selected_variant_id,
        promoted,
        len(variants),
    )


def _run_variant(
    cache: FeatureCache,
    adjusted_open: pd.DataFrame,
    spec: VariantSpec,
    config: AppConfig,
) -> tuple[StrategyRun, BacktestResult]:
    strategy_run = build_strategy(cache, spec)
    result = run_backtest(
        adjusted_open,
        strategy_run.target_weights,
        one_way_cost_bps=config.execution.total_one_way_cost_bps,
        minimum_trade_weight=config.execution.minimum_trade_weight,
    )
    return strategy_run, result


def _benchmark_backtest(open_prices: pd.Series, *, cost_bps: float) -> BacktestResult:
    frame = open_prices.rename("SPY").to_frame()
    target = pd.DataFrame(1.0, index=frame.index, columns=frame.columns)
    return run_backtest(frame, target, one_way_cost_bps=cost_bps)


def _equal_sector_backtest(open_prices: pd.DataFrame, *, cost_bps: float) -> BacktestResult:
    target = pd.DataFrame(
        1.0 / len(open_prices.columns),
        index=open_prices.index,
        columns=open_prices.columns,
    )
    return run_backtest(open_prices, target, one_way_cost_bps=cost_bps)


def _robustness_checks(
    cache: FeatureCache,
    adjusted_open: pd.DataFrame,
    spec: VariantSpec,
    run: StrategyRun,
    config: AppConfig,
) -> dict[str, object]:
    cost_sensitivity: list[dict[str, object]] = []
    for cost in (5.0, 10.0, 20.0, 40.0):
        result = run_backtest(
            adjusted_open,
            run.target_weights,
            one_way_cost_bps=cost,
            minimum_trade_weight=config.execution.minimum_trade_weight,
        )
        cost_sensitivity.append(
            {"one_way_cost_bps": cost, **performance_metrics(result.net_returns)}
        )
    delayed = run_backtest(
        adjusted_open,
        run.target_weights.shift(1).fillna(0.0),
        one_way_cost_bps=config.execution.total_one_way_cost_bps,
        minimum_trade_weight=config.execution.minimum_trade_weight,
    )
    leave_one_out: list[dict[str, object]] = []
    for removed in adjusted_open.columns:
        reduced_open = adjusted_open.drop(columns=removed)
        reduced_close = cache.close.drop(columns=removed)
        reduced_run = build_strategy(
            FeatureCache(reduced_close, cache.benchmark, cache.context),
            spec,
        )
        reduced_result = run_backtest(
            reduced_open,
            reduced_run.target_weights,
            one_way_cost_bps=config.execution.total_one_way_cost_bps,
            minimum_trade_weight=config.execution.minimum_trade_weight,
        )
        leave_one_out.append(
            {"removed_sector": removed, **performance_metrics(reduced_result.net_returns)}
        )
    return {
        "cost_sensitivity": cost_sensitivity,
        "one_additional_session_delay": performance_metrics(delayed.net_returns),
        "leave_one_sector_out": leave_one_out,
    }


def _latest_decision(spec: VariantSpec, run: StrategyRun) -> dict[str, object]:
    latest = run.target_weights.index[-1]
    current = run.target_weights.loc[latest]
    previous = run.target_weights.iloc[-2]
    rankings = run.ranks.loc[latest].dropna().sort_values()
    diagnostics = run.diagnostics.loc[latest]
    targets = {ticker: float(weight) for ticker, weight in current.items() if weight > 0.0}
    actions = []
    for ticker in run.target_weights.columns:
        change = float(current[ticker] - previous[ticker])
        if abs(change) >= 0.005:
            actions.append(
                {
                    "ticker": ticker,
                    "action": "BUY" if change > 0 else "SELL",
                    "change_weight": change,
                    "target_weight": float(current[ticker]),
                }
            )
    breadth = float(diagnostics["breadth"])
    if breadth >= 2 / 3:
        leadership_state = "broadening"
    elif breadth <= 1 / 3:
        leadership_state = "narrow_or_defensive"
    else:
        leadership_state = "transition"
    return {
        "as_of_close": latest.date().isoformat(),
        "effective_at": "next_regular_session_open_after_human_review",
        "action_authorized": False,
        "variant_id": spec.variant_id,
        "family": spec.family,
        "target_weights": targets,
        "cash_weight": float(1.0 - current.sum()),
        "actions": actions,
        "sector_ranks": {ticker: float(rank) for ticker, rank in rankings.items()},
        "leadership_state": leadership_state,
        "breadth": breadth,
        "dispersion_z": float(diagnostics["dispersion_z"]),
        "group_rotation_signal": float(diagnostics["group_rotation_signal"]),
    }


def _render_report(summary: dict[str, object], metrics: pd.DataFrame) -> str:
    selected = summary.get("selected_variant_id") or "none"
    lines = [
        "# Rotation Trader Research Report",
        "",
        f"- Variants tested: {summary['variants_tested']}",
        f"- Frozen pre-holdout selection: {selected}",
        f"- Promotion status: {summary['promotion_status']}",
        f"- PBO estimate: {summary['pbo']['probability_selected_below_oos_median']:.1%}",
        "",
        "## Interpretation",
        "",
        "The selected candidate, if any, was chosen without holdout metrics. Holdout and",
        "robustness evidence can reject promotion but cannot be used to tune this run.",
        "Backtests do not authorize a trade.",
        "",
        "## Selected and family metrics",
        "",
        metrics.to_string(index=False),
        "",
    ]
    if "behavioral_distinctness" in summary:
        distinctness = summary["behavioral_distinctness"]
        lines.extend(
            [
                "## Non-duplication",
                "",
                f"- Return correlation to Swing control: {distinctness['return_correlation']:.3f}",
                f"- Mean weight overlap: {distinctness['mean_weight_overlap']:.1%}",
                f"- Materially different days: {distinctness['different_weight_day_share']:.1%}",
                "",
            ]
        )
    return "\n".join(lines)


def _replace_latest(run_dir: Path, latest_dir: Path) -> None:
    temporary = latest_dir.with_name(latest_dir.name + ".tmp")
    if temporary.exists():
        shutil.rmtree(temporary)
    shutil.copytree(run_dir, temporary)
    if latest_dir.exists():
        shutil.rmtree(latest_dir)
    temporary.replace(latest_dir)
