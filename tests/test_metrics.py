import pandas as pd
import pytest

from rotation_trader.metrics import performance_metrics


def test_metrics_report_drawdown_and_turnover() -> None:
    dates = pd.bdate_range("2026-01-05", periods=4)
    returns = pd.Series([0.0, 0.10, -0.20, 0.05], index=dates)
    turnover = pd.Series([0.0, 1.0, 0.0, 0.5], index=dates)

    metrics = performance_metrics(returns, turnover=turnover)

    assert metrics["max_drawdown"] == pytest.approx(-0.2)
    assert metrics["annualized_turnover"] == 94.5
