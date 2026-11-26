"""Sector-specific Portfolio Lab export with preserved native evidence."""

from pathlib import Path

import numpy as np
import pandas as pd

from rotation_trader.config import load_config
from rotation_trader.strategy import FeatureCache, VariantSpec, build_strategy

SYSTEM = "rotation-trader"


def research_targets(prices, config, source_dir):
    import hashlib
    import json

    manifest = json.loads((source_dir / "run_manifest.json").read_text())
    for file in (
        "champion_target_weights.parquet",
        "regime_robust_challenger_weights.parquet",
        "allocation_timing_challenger_weights.parquet",
        "research_summary.json",
    ):
        if (
            hashlib.sha256((source_dir / file).read_bytes()).hexdigest()
            != manifest["artifacts"][file]
        ):
            raise ValueError(f"Native target integrity failure: {file}")
    close = prices["Close"][list(config.data.stable_sectors)]
    context = prices["Close"][[t for t in config.data.context_tickers if t in prices["Close"]]]
    cache = FeatureCache(close, prices["Close"][config.data.benchmark], context)
    slow = build_strategy(
        cache,
        VariantSpec(
            family="portfolio_slow126_control", momentum_lookbacks=(126,), momentum_weights=(1.0,)
        ),
    ).target_weights
    fast = build_strategy(
        cache,
        VariantSpec(
            family="portfolio_fast42_control", momentum_lookbacks=(42,), momentum_weights=(1.0,)
        ),
    ).target_weights
    benchmark = prices["Close"][config.data.benchmark]
    pressure = (-benchmark.pct_change(21, fill_method=None) / 0.10).clip(0, 1).fillna(0)
    adaptive = slow.mul(1 - 0.6 * pressure, axis=0).add(fast.mul(0.6 * pressure, axis=0))
    start = close.index[config.research.minimum_history_sessions]
    summary = json.loads((source_dir / "research_summary.json").read_text())
    native_cache = FeatureCache(
        close.loc[start:], prices["Close"][config.data.benchmark].loc[start:], context.loc[start:]
    )

    def frozen_target(spec):
        values = dict(spec)
        values["momentum_lookbacks"] = tuple(values["momentum_lookbacks"])
        values["momentum_weights"] = tuple(values["momentum_weights"])
        return (
            build_strategy(native_cache, VariantSpec(**values))
            .target_weights.reindex(close.index)
            .fillna(0)
        )

    output = {
        "rotation_primary": (
            frozen_target(summary["selected_specification"]),
            start,
            "primary",
        ),
        "rotation_risk_challenger": (
            frozen_target(summary["regime_robust_challenger"]["specification"]),
            start,
            "challenger",
        ),
        "rotation_timing_challenger": (
            frozen_target(summary["allocation_timing_challenger"]["specification"]),
            start,
            "challenger",
        ),
        "rotation_slow126_control": (slow, start, "comparator"),
        "rotation_adaptive_clock": (adaptive, start, "challenger"),
    }
    return output


def export_bundle(output):
    import hashlib
    import json

    config = load_config("config/default.toml")
    source_dir = Path("reports/latest")
    run = json.loads((source_dir / "run_manifest.json").read_text())
    manifest_path = Path(run["price_manifest"])
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != run["price_manifest_sha256"]:
        raise ValueError("Native price manifest hash mismatch")
    metadata = json.loads(manifest_path.read_text())
    source = manifest_path.parent / metadata["data_file"]
    if hashlib.sha256(source.read_bytes()).hexdigest() != metadata["data_file_sha256"]:
        raise ValueError("Native price file hash mismatch")
    prices = pd.read_parquet(source)
    cash = (
        prices["Close"][config.data.cash_yield_ticker]
        .shift(1)
        .clip(lower=0)
        .div(100)
        .add(1)
        .pow(1 / 252)
        .sub(1)
        .fillna(0)
    )
    close = prices["Close"].drop(columns=[config.data.cash_yield_ticker], errors="ignore")
    files = [
        source,
        manifest_path,
        source_dir / "run_manifest.json",
        source_dir / "selection_before_holdout.json",
        source_dir / "research_summary.json",
        Path("config/default.toml"),
    ]
    return _publish(
        output,
        close,
        research_targets(prices, config, source_dir),
        cash,
        files,
        "native next-adjusted-open, open-to-open research engine",
        [
            "4400 previously tested variants; no substantial-edge promotion.",
            "Existing selection is preserved; new timing arms are diagnostics.",
            "Frozen specifications are rebuilt under corrected planned-period scheduling; old cached targets are not silently reused.",
            "Sector funds are surviving ETFs with evolving classifications.",
            "Common replay uses self-financing drift and does not inherit native execution assumptions.",
            "Native execution now funds fees and holds units between changed targets; legacy archives require accounting rebaseline.",
        ],
        "rotation_primary",
    )


def _publish(output, prices, targets, cash, source_inputs, native_execution, notes, primary):
    import hashlib
    import json
    from datetime import UTC, datetime
    from importlib.metadata import version

    output.mkdir(parents=True, exist_ok=False)
    if (
        not isinstance(prices.index, pd.DatetimeIndex)
        or prices.index.hasnans or prices.index.has_duplicates
        or not prices.index.is_monotonic_increasing or not prices.columns.is_unique
        or np.isinf(prices.to_numpy(dtype=float)).any() or prices.le(0).any().any()
    ):
        raise ValueError("Invalid source session index")
    if (
        not cash.index.equals(prices.index) or not np.isfinite(cash).all()
        or cash.le(-1).any()
    ):
        raise ValueError("Cash observations must be finite and aligned")
    prices.to_parquet(output / "prices.parquet")
    cash.reindex(prices.index).fillna(0).rename("cash_return").to_frame().to_parquet(
        output / "cash_returns.parquet"
    )
    experts = []
    for name, (weights, evaluation_start, role) in targets.items():
        if (
            not weights.index.equals(prices.index) or not weights.columns.is_unique
            or not set(weights) <= set(prices)
            or not np.isfinite(weights.to_numpy(dtype=float)).all()
            or weights.lt(-1e-12).any().any()
            or weights.sum(axis=1).gt(1 + 1e-8).any()
        ):
            raise ValueError(f"Invalid native targets: {name}")
        if (weights.gt(1e-12) & prices.reindex(columns=weights.columns).isna()).any().any():
            raise ValueError(f"Unpriced native target: {name}")
        filename = f"{name}.parquet"
        weights.to_parquet(output / filename)
        experts.append(
            {
                "id": name,
                "weights_file": filename,
                "evaluation_start": str(pd.Timestamp(evaluation_start).date()),
                "role": role,
                "evidence_status": "retrospective_research",
                "target_semantics": "close_known_risky_budgets",
            }
        )
    artifacts = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(output.iterdir())
        if p.is_file()
    }
    code = hashlib.sha256()
    for p in sorted(Path("src").rglob("*.py")):
        code.update(str(p).encode())
        code.update(p.read_bytes())
    source_inputs = [*source_inputs, *[
        p for p in (Path("pyproject.toml"), Path("poetry.lock"))
        if p.is_file() and p not in source_inputs
    ]]
    manifest = {
        "schema_version": 1,
        "runtime_versions": {name: version(name) for name in ("numpy", "pandas", "pyarrow", "exchange-calendars")},
        "system": SYSTEM,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "data_end": str(prices.index.max().date()),
        "primary_expert": primary,
        "native_execution": native_execution,
        "authority": "research_only",
        "automatic_promotion_allowed": False,
        "code_sha256": code.hexdigest(),
        "experts": experts,
        "source_inputs": [
            {"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in source_inputs
        ],
        "artifacts": artifacts,
        "notes": notes,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return output / "manifest.json"


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Research-only Portfolio Lab specialist export")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(export_bundle(args.output))


if __name__ == "__main__":
    main()
