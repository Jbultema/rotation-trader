"""Expose diagnostics from the frozen native specification without reselection."""

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from rotation_trader.config import load_config
from rotation_trader.strategy import FeatureCache, VariantSpec, build_strategy


def signals(prices, config, specification):
    start = prices.index[config.research.minimum_history_sessions]
    values = dict(specification)
    for key in ("momentum_lookbacks", "momentum_weights"):
        values[key] = tuple(values[key])
    cache = FeatureCache(
        prices.loc[start:, list(config.data.stable_sectors)],
        prices.loc[start:, config.data.benchmark],
        prices.loc[start:, [t for t in config.data.context_tickers if t in prices]],
    )
    native = build_strategy(cache, VariantSpec(**values))
    result = native.diagnostics.copy()
    result["scheduled"] = native.rebalance
    result["target_exposure"] = native.target_weights.sum(axis=1)
    result["reason"] = "frozen_sector_allocation_held"
    result.loc[result.scheduled, "reason"] = "native_sector_selection_review"
    result.loc[result.target_exposure.lt(0.999), "reason"] = "held_target_includes_unallocated_cash"
    result.loc[result.timing_exposure.lt(result.target_exposure - .001) & ~result.scheduled, "reason"] = "timing_warning_waiting_for_native_rebalance"
    for ticker in native.score:
        result[f"score_{ticker}"] = native.score[ticker]
        result[f"rank_{ticker}"] = native.ranks[ticker]
        result[f"target_{ticker}"] = native.target_weights[ticker]
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cutoff")
    args = parser.parse_args()
    config = load_config("config/default.toml")
    specification = json.loads(Path("reports/latest/research_summary.json").read_text())["selected_specification"]
    prices = pd.read_parquet(args.bundle / "prices.parquet").loc[:args.cutoff]
    args.output.mkdir(parents=True, exist_ok=False)
    signals(prices, config, specification).to_parquet(args.output / "signals.parquet")
    (args.output / "manifest.json").write_text(json.dumps({
        "schema_version": 1, "system": "rotation-trader",
        "signals_sha256": hashlib.sha256((args.output / "signals.parquet").read_bytes()).hexdigest(),
        "bundle_sha256": hashlib.sha256((args.bundle / "manifest.json").read_bytes()).hexdigest(),
        "specification": specification,
        "semantics": "frozen_native_specification_reconstruction",
        "driver_columns": ["scheduled", "timing_stage", "timing_exposure", "exposure_scalar", "eligible_count"],
        "monitor_columns": ["breadth", "dispersion_z", "average_sector_correlation"],
        "limitations": ["No reselection or promotion.", "Native execution uses approximate target-weight accounting; dashboard targets are not actual holdings."],
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
