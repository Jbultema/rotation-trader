"""Revalue frozen strategies without reselection under old and funded accounting."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd

from rotation_trader.backtest import run_backtest
from rotation_trader.config import load_config
from rotation_trader.data import load_price_snapshot
from rotation_trader.metrics import performance_metrics
from rotation_trader.portfolio_export import research_targets


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(output, legacy_ref):
    source = Path("reports/latest")
    config = load_config("config/default.toml")
    manifest = json.loads((source / "run_manifest.json").read_text())
    price_manifest = Path(manifest["price_manifest"])
    if sha(price_manifest) != manifest["price_manifest_sha256"]:
        raise ValueError("Price manifest changed")
    prices = load_price_snapshot(price_manifest)
    targets = research_targets(prices, config, source)
    raw = subprocess.run(["git", "show", f"{legacy_ref}:src/rotation_trader/backtest.py"],
                         check=True, capture_output=True).stdout
    output.mkdir(parents=True, exist_ok=False)
    (output / "protocol.json").write_text(json.dumps({
        "selection": "frozen_existing_primary_and_challengers_no_reselection",
        "legacy_ref": legacy_ref, "legacy_source_sha256": hashlib.sha256(raw).hexdigest(),
        "cost_bps": [0, 10, 25, 50], "additional_delay_sessions": [0, 1],
        "data_limitation": "surviving_sector_ETFs_evolving_classifications_not_survivor_free_stocks",
        "historical_labels": "previously_examined_not_new_holdout", "action_authorized": False,
    }, indent=2) + "\n")
    rows = []
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "legacy_rotation.py"
        path.write_bytes(raw)
        spec = importlib.util.spec_from_file_location("legacy_rotation", path)
        legacy = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = legacy
        spec.loader.exec_module(legacy)
        start = min(v[1] for v in targets.values())
        opens = prices["Open"].loc[start:]
        cash = prices["Close"][config.data.cash_yield_ticker].shift(1).clip(lower=0).div(100).add(1).pow(1/252).sub(1).fillna(0).loc[start:]
        targets = {name: value[0].loc[start:] for name, value in targets.items() if name in {
            "rotation_primary", "rotation_risk_challenger", "rotation_timing_challenger"}}
        targets["buy_hold_SPY"] = pd.DataFrame({"SPY": 1.}, index=opens.index)
        sectors = list(config.data.stable_sectors)
        targets["buy_hold_equal_sectors"] = pd.DataFrame(1/len(sectors), index=opens.index, columns=sectors)
        for name, weights in targets.items():
            quotes = opens[list(weights)]
            for cost in (0, 10, 25, 50):
                for delay in (0, 1):
                    delayed = weights.shift(delay).fillna(0)
                    for engine, function in (("legacy", legacy.run_backtest), ("funded", run_backtest)):
                        result = function(quotes, delayed, one_way_cost_bps=cost,
                                          minimum_trade_weight=config.execution.minimum_trade_weight,
                                          cash_returns=cash)
                        for period, left, right in (("full", None, None), ("pre2019", None, "2018-12-31"),
                                                    ("later", "2019-01-01", None)):
                            rows.append({"strategy": name, "engine": engine, "cost_bps": cost,
                                "extra_delay": delay, "period": period,
                                **performance_metrics(result.net_returns.loc[left:right], turnover=result.one_way_turnover)})
    pd.DataFrame(rows).to_csv(output / "metrics.csv", index=False)
    bound = [Path(__file__), *sorted(Path("src/rotation_trader").rglob("*.py")), Path("config/default.toml"),
             source / "run_manifest.json", source / "research_summary.json", price_manifest]
    (output / "manifest.json").write_text(json.dumps({"sources": {str(p): sha(p) for p in bound},
        "artifacts": {p.name: sha(p) for p in output.iterdir()}, "paths": len(rows)//3,
        "automatic_promotion_allowed": False}, indent=2) + "\n")
    print(pd.DataFrame(rows).query("cost_bps == 10 and extra_delay == 0 and period == 'full'")[["strategy", "engine", "cagr", "max_drawdown"]].to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--legacy-ref", required=True)
    args = parser.parse_args()
    run(args.output, args.legacy_ref)
