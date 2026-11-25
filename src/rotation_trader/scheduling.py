"""Planned exchange dates, independent of the end of a captured file."""

from functools import lru_cache

import exchange_calendars as xcals
import pandas as pd


@lru_cache(maxsize=16)
def planned_period_ends(start_year: int, end_year: int, cadence: str) -> pd.DatetimeIndex:
    start, end = f"{start_year}-01-01", f"{end_year + 1}-01-10"
    calendar = xcals.get_calendar("XNYS", start=start, end=end)
    # Only regularly scheduled holidays. Do not anticipate future emergency
    # closures by treating the preceding observed date as period end.
    holidays = calendar.regular_holidays.holidays(start, end)
    dates = pd.date_range(start, end, freq=pd.offsets.CustomBusinessDay(holidays=holidays))
    periods = dates.to_period("M" if cadence == "monthly" else "W-FRI")
    return pd.DatetimeIndex(pd.Series(dates, index=dates).groupby(periods).max().to_numpy())
