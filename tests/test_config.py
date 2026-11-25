from pathlib import Path

from rotation_trader.config import load_config


def test_default_config_is_long_history_and_stable_universe() -> None:
    config = load_config(Path("config/default.toml"))

    assert config.data.start == "1998-12-22"
    assert len(config.data.stable_sectors) == 9
    assert "XLC" not in config.data.stable_sectors
    assert config.data.cash_yield_ticker == "^IRX"
    assert config.execution.total_one_way_cost_bps == 10.0
