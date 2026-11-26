import numpy as np
import pandas as pd

from rotation_trader.research import _cash_returns_from_annual_yield, _equal_sector_backtest


def test_equal_sector_comparator_is_long_only_and_fully_invested() -> None:
    dates = pd.bdate_range("2020-01-02", periods=10)
    opens = pd.DataFrame(
        {
            "XLE": np.linspace(100.0, 110.0, len(dates)),
            "XLV": np.linspace(100.0, 105.0, len(dates)),
        },
        index=dates,
    )

    result = _equal_sector_backtest(opens, cost_bps=0.0)

    np.testing.assert_allclose(result.weights_at_open.iloc[1:].sum(axis=1), 1., atol=1e-12)
    assert result.weights_at_open.min().min() >= 0.0
    assert result.one_way_turnover.iloc[2:].eq(0).all()
    assert result.weights_at_open.iloc[-1, 0] > 0.5


def test_cash_returns_use_only_prior_completed_yield() -> None:
    dates = pd.bdate_range("2026-01-02", periods=3)
    yields = pd.Series([3.0, 6.0, 9.0], index=dates)

    result = _cash_returns_from_annual_yield(yields)

    assert result.iloc[0] == 0.0
    assert abs(result.iloc[1] - ((1.03 ** (1 / 252)) - 1)) < 1e-12
    assert abs(result.iloc[2] - ((1.06 ** (1 / 252)) - 1)) < 1e-12
