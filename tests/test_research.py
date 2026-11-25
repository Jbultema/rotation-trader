import numpy as np
import pandas as pd

from rotation_trader.research import _equal_sector_backtest


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

    assert result.weights_at_open.iloc[1:].sum(axis=1).eq(1.0).all()
    assert result.weights_at_open.min().min() >= 0.0
