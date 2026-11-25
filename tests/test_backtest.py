import pandas as pd
import pytest

from rotation_trader.backtest import BacktestError, run_backtest


def test_close_signal_cannot_earn_return_before_next_open_interval() -> None:
    dates = pd.bdate_range("2026-01-05", periods=4)
    opens = pd.DataFrame({"XLE": [100.0, 110.0, 121.0, 133.1]}, index=dates)
    targets = pd.DataFrame({"XLE": [1.0, 0.0, 0.0, 0.0]}, index=dates)

    result = run_backtest(opens, targets, one_way_cost_bps=0.0)

    assert result.weights_at_open["XLE"].tolist() == [0.0, 1.0, 0.0, 0.0]
    assert result.net_returns.iloc[1] == 0.0
    assert result.net_returns.iloc[2] == pytest.approx(0.10)
    assert result.net_returns.iloc[3] == 0.0


def test_cost_is_charged_on_each_one_way_risky_asset_trade() -> None:
    dates = pd.bdate_range("2026-01-05", periods=3)
    opens = pd.DataFrame({"XLE": [100.0, 100.0, 100.0]}, index=dates)
    targets = pd.DataFrame({"XLE": [1.0, 0.0, 0.0]}, index=dates)

    result = run_backtest(opens, targets, one_way_cost_bps=10.0)

    assert result.transaction_cost.tolist() == [0.0, 0.001, 0.001]


def test_backtest_rejects_leverage_and_short_positions() -> None:
    dates = pd.bdate_range("2026-01-05", periods=2)
    opens = pd.DataFrame({"XLE": [100.0, 101.0], "XLV": [100.0, 101.0]}, index=dates)

    with pytest.raises(BacktestError):
        run_backtest(
            opens,
            pd.DataFrame({"XLE": [0.8, 0.8], "XLV": [0.4, 0.4]}, index=dates),
            one_way_cost_bps=0.0,
        )
    with pytest.raises(BacktestError):
        run_backtest(
            opens,
            pd.DataFrame({"XLE": [-0.1, 0.0], "XLV": [0.0, 0.0]}, index=dates),
            one_way_cost_bps=0.0,
        )
