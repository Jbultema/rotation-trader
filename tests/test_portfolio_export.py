import hashlib
import json
from dataclasses import asdict

import numpy as np
import pandas as pd
import pytest

from rotation_trader.config import load_config
from rotation_trader.portfolio_export import research_targets
from rotation_trader.strategy import FeatureCache, VariantSpec, build_strategy


def inputs(tmp_path):
    config = load_config("config/default.toml")
    dates = pd.bdate_range("2010-01-01", periods=500)
    names = list(dict.fromkeys([*config.data.stable_sectors, *config.data.context_tickers, "SPY"]))
    rng = np.random.default_rng(121)
    close = pd.DataFrame(
        100 * np.exp(rng.normal(0.0007, 0.01, (500, len(names))).cumsum(axis=0)),
        index=dates,
        columns=names,
    )
    targets = close[list(config.data.stable_sectors)] * 0 + 1 / 9
    artifacts = {}
    for file in (
        "champion_target_weights.parquet",
        "regime_robust_challenger_weights.parquet",
        "allocation_timing_challenger_weights.parquet",
    ):
        targets.to_parquet(tmp_path / file)
        artifacts[file] = hashlib.sha256((tmp_path / file).read_bytes()).hexdigest()
    spec = asdict(
        VariantSpec(family="frozen_test", momentum_lookbacks=(126,), momentum_weights=(1.0,))
    )
    (tmp_path / "research_summary.json").write_text(
        json.dumps(
            {
                "selected_specification": spec,
                "regime_robust_challenger": {"specification": spec},
                "allocation_timing_challenger": {"specification": spec},
            }
        )
    )
    artifacts["research_summary.json"] = hashlib.sha256(
        (tmp_path / "research_summary.json").read_bytes()
    ).hexdigest()
    (tmp_path / "run_manifest.json").write_text(json.dumps({"artifacts": artifacts}))
    return config, pd.concat({"Close": close}, axis=1)


def test_native_selection_is_preserved_and_new_clock_is_bounded(tmp_path):
    config, p = inputs(tmp_path)
    result = research_targets(p, config, tmp_path)
    close = p["Close"][list(config.data.stable_sectors)].iloc[
        config.research.minimum_history_sessions :
    ]
    expected = (
        build_strategy(
            FeatureCache(
                close,
                p["Close"].SPY.reindex(close.index),
                p["Close"][[t for t in config.data.context_tickers if t in p["Close"]]].reindex(
                    close.index
                ),
            ),
            VariantSpec(family="frozen_test", momentum_lookbacks=(126,), momentum_weights=(1.0,)),
        )
        .target_weights.reindex(p.index)
        .fillna(0)
    )
    pd.testing.assert_frame_equal(result["rotation_primary"][0], expected)
    for frame, _, _ in result.values():
        assert frame.min().min() >= 0
        assert frame.sum(axis=1).max() <= 1 + 1e-12


def test_tampered_native_selection_cannot_be_exported(tmp_path):
    config, p = inputs(tmp_path)
    with (tmp_path / "champion_target_weights.parquet").open("ab") as file:
        file.write(b"tamper")
    with pytest.raises(ValueError, match="integrity"):
        research_targets(p, config, tmp_path)


def test_interpretation_reconciles_and_distinguishes_pending_timing(tmp_path):
    from rotation_trader.interpretation_export import signals

    config, p = inputs(tmp_path)
    spec = json.loads((tmp_path / "research_summary.json").read_text())["selected_specification"]
    result = signals(p["Close"], config, spec)
    expected = research_targets(p, config, tmp_path)["rotation_primary"][0].reindex(result.index)
    target_columns = [c for c in result if c.startswith("target_") and c[7:] in expected]
    pd.testing.assert_frame_equal(result[target_columns].rename(columns=lambda c: c[7:]), expected)
    pd.testing.assert_frame_equal(result.loc[:p.index[417]], signals(p["Close"].iloc[:418], config, spec))
    pending = result.timing_exposure.lt(result.target_exposure - .001) & ~result.scheduled
    assert result.loc[pending, "reason"].eq("timing_warning_waiting_for_native_rebalance").all()
