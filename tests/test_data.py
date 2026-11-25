from datetime import UTC, datetime

import pandas as pd

from rotation_trader.data import latest_completed_session_cutoff, normalize_yahoo_prices


def test_completed_session_cutoff_excludes_open_market_day() -> None:
    during_market = datetime(2026, 11, 24, 18, 30, tzinfo=UTC)
    after_market = datetime(2026, 11, 24, 22, 0, tzinfo=UTC)

    assert latest_completed_session_cutoff(during_market).isoformat() == "2026-11-23"
    assert latest_completed_session_cutoff(after_market).isoformat() == "2026-11-24"


def test_normalize_yahoo_prices_reorders_fields_and_tickers() -> None:
    index = pd.to_datetime(["2026-11-20", "2026-11-23"])
    columns = pd.MultiIndex.from_product(
        [["Volume", "Close", "Open", "Low", "High"], ["XLE", "SPY"]]
    )
    raw = pd.DataFrame(1.0, index=index, columns=columns)

    result = normalize_yahoo_prices(raw, ("SPY", "XLE"))

    assert result.columns.names == [None, None]
    assert list(result["Close"].columns) == ["SPY", "XLE"]
    assert result.index.tz is None
