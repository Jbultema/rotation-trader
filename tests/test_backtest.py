import numpy as np
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


@pytest.mark.parametrize("kind", [
    "nan_target", "infinite_target", "unknown_asset", "missing_session",
    "duplicate_session", "missing_holding_price", "nonpositive_price",
    "negative_cost", "nan_cost", "missing_cash",
])
def test_invalid_inputs_are_not_silently_filled_or_dropped(kind):
    dates = pd.bdate_range("2026-01-05", periods=4)
    opens = pd.DataFrame(100.0, index=dates, columns=["XLE", "XLV"])
    targets = opens * 0 + 0.5
    cash = pd.Series(0.0, index=dates)
    cost, band = 10.0, 0.0
    if kind == "nan_target":
        targets.iloc[1, 0] = np.nan
    elif kind == "infinite_target":
        targets.iloc[1, 0] = np.inf
    elif kind == "unknown_asset":
        targets["UNKNOWN"] = 0.1
    elif kind == "missing_session":
        targets = targets.iloc[:-1]
    elif kind == "duplicate_session":
        opens.index = [dates[0], dates[0], dates[2], dates[3]]
    elif kind == "missing_holding_price":
        opens.iloc[2, 0] = np.nan
    elif kind == "nonpositive_price":
        opens.iloc[2, 0] = 0.0
    elif kind == "negative_cost":
        cost = -1.0
    elif kind == "nan_cost":
        cost = np.nan
    elif kind == "missing_cash":
        cash.iloc[2] = np.nan
    with pytest.raises(BacktestError):
        run_backtest(opens, targets, one_way_cost_bps=cost,
                     minimum_trade_weight=band, cash_returns=cash)


def test_no_trade_band_executes_full_basket_when_partial_trade_would_leverage():
    dates = pd.bdate_range("2026-01-05", periods=4)
    opens = pd.DataFrame(100.0, index=dates, columns=["XLE", "XLV"])
    target = pd.DataFrame([[0.5, 0.4], [0.45, 0.55], [0.45, 0.55], [0.45, 0.55]],
                          index=dates, columns=opens.columns)
    result = run_backtest(opens, target, one_way_cost_bps=10.0, minimum_trade_weight=0.1)
    assert result.weights_at_open.sum(axis=1).le(1.0 + 1e-9).all()
    assert result.weights_at_open.iloc[2].tolist() == [0.45, 0.55]
    assert result.one_way_turnover.iloc[2] == pytest.approx(0.20)
