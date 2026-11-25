import pandas as pd

from rotation_trader.strategy import rebalance_mask


def test_partial_week_and_month_do_not_create_rebalance():
    index = pd.bdate_range("2026-03-02", "2026-03-10")
    assert not rebalance_mask(index, "monthly").any()
    assert rebalance_mask(index, "weekly").loc["2026-03-06"]
    assert not rebalance_mask(index, "weekly").loc["2026-03-10"]


def test_good_friday_month_end_is_known_without_future_price_rows():
    index = pd.bdate_range("2024-03-01", "2024-03-28")
    assert rebalance_mask(index, "monthly").iloc[-1]


def test_prefix_invariance_including_good_friday_and_partial_week():
    index = pd.bdate_range("2024-01-02", "2026-11-25")
    for cadence in ("monthly", "weekly", "biweekly"):
        full = rebalance_mask(index, cadence)
        for stop in (63, 150, 307, 410, 509):
            pd.testing.assert_series_equal(full.iloc[:stop], rebalance_mask(index[:stop], cadence))


def test_emergency_closure_is_not_anticipated():
    index = pd.to_datetime(["2001-09-07", "2001-09-10", "2001-09-17", "2001-09-18"])
    assert not rebalance_mask(index, "weekly").loc["2001-09-10"]


def test_year_end_partial_week_is_not_a_friday():
    short = pd.bdate_range("2025-12-01", "2025-12-31")
    full = pd.bdate_range("2025-12-01", "2026-01-06")
    assert not rebalance_mask(short, "weekly").iloc[-1]
    pd.testing.assert_series_equal(
        rebalance_mask(full, "weekly").loc[short], rebalance_mask(short, "weekly")
    )
