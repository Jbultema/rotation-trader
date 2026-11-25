from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

from rotation_trader.config import DataConfig
from rotation_trader.provenance import file_sha256, frame_sha256, write_hashed_json

REQUIRED_FIELDS = ("Open", "High", "Low", "Close", "Volume")


class MarketDataError(RuntimeError):
    """Raised when a market-data snapshot cannot support an honest decision."""


@dataclass(frozen=True)
class DataAudit:
    passed: bool
    status: str
    latest_session: str | None
    stable_common_start: str | None
    minimum_stable_coverage: float
    missing_tickers: tuple[str, ...]
    stale_sessions: int


@dataclass(frozen=True)
class PriceSnapshot:
    data_path: Path
    manifest_path: Path
    audit: DataAudit


def latest_completed_session_cutoff(captured_at: datetime) -> date:
    eastern = _as_utc(captured_at).astimezone(ZoneInfo("America/New_York"))
    if eastern.weekday() < 5 and eastern.time() < time(16, 15):
        return eastern.date() - timedelta(days=1)
    return eastern.date()


def yahoo_end_exclusive(captured_at: datetime) -> date:
    return latest_completed_session_cutoff(captured_at) + timedelta(days=1)


def download_price_snapshot(
    config: DataConfig,
    output_dir: Path,
    *,
    now: datetime | None = None,
) -> PriceSnapshot:
    captured_at = _as_utc(now or datetime.now(UTC))
    tickers = tuple(
        dict.fromkeys(
            [
                config.benchmark,
                *config.stable_sectors,
                *config.extension_sectors,
                *config.context_tickers,
            ]
        )
    )
    end_exclusive = yahoo_end_exclusive(captured_at)
    raw = yf.download(
        list(tickers),
        start=config.start,
        end=end_exclusive.isoformat(),
        auto_adjust=True,
        actions=False,
        group_by="column",
        progress=False,
        threads=True,
    )
    prices = normalize_yahoo_prices(raw, tickers)
    if prices.empty:
        raise MarketDataError("Yahoo returned no usable prices.")
    prices = prices.loc[prices.index < pd.Timestamp(end_exclusive)]
    audit = audit_prices(prices, config, captured_at=captured_at)
    if not audit.passed:
        raise MarketDataError(f"Price snapshot failed its data gate: {asdict(audit)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = captured_at.strftime("%Y%m%dT%H%M%S%fZ")
    data_path = output_dir / f"prices-{stamp}.parquet"
    manifest_path = output_dir / f"prices-{stamp}.manifest.json"
    prices.to_parquet(data_path)
    manifest = {
        "schema_version": 1,
        "record_type": "rotation_price_snapshot",
        "captured_at_utc": captured_at.isoformat(),
        "requested_start": config.start,
        "requested_end_exclusive": end_exclusive.isoformat(),
        "tickers": list(tickers),
        "fields": list(REQUIRED_FIELDS),
        "data_file": data_path.name,
        "data_file_sha256": file_sha256(data_path),
        "tabular_sha256": frame_sha256(prices),
        "rows": int(len(prices)),
        "first_session": prices.index.min().date().isoformat(),
        "last_session": prices.index.max().date().isoformat(),
        "audit": asdict(audit),
        "provider": "Yahoo Finance via yfinance",
        "adjustment": "auto_adjusted_ohlcv",
    }
    write_hashed_json(manifest_path, manifest)
    return PriceSnapshot(data_path, manifest_path, audit)


def normalize_yahoo_prices(raw: pd.DataFrame, tickers: tuple[str, ...]) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame()
    frame = raw.copy()
    if not isinstance(frame.columns, pd.MultiIndex):
        if len(tickers) != 1:
            raise MarketDataError("Yahoo returned flat columns for a multi-ticker request.")
        frame.columns = pd.MultiIndex.from_product([frame.columns, [tickers[0]]])
    level_zero = set(frame.columns.get_level_values(0).astype(str))
    if not set(REQUIRED_FIELDS).issubset(level_zero):
        level_one = set(frame.columns.get_level_values(1).astype(str))
        if set(REQUIRED_FIELDS).issubset(level_one):
            frame = frame.swaplevel(0, 1, axis=1)
        else:
            missing = sorted(set(REQUIRED_FIELDS) - level_zero)
            raise MarketDataError(f"Yahoo response is missing fields: {missing}")
    frame = frame.reindex(
        columns=pd.MultiIndex.from_product([REQUIRED_FIELDS, tickers])
    ).sort_index(axis=1)
    frame.index = pd.DatetimeIndex(pd.to_datetime(frame.index)).tz_localize(None).normalize()
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    return frame.astype(float)


def audit_prices(
    prices: pd.DataFrame,
    config: DataConfig,
    *,
    captured_at: datetime,
) -> DataAudit:
    if prices.empty or not isinstance(prices.columns, pd.MultiIndex):
        return DataAudit(False, "invalid_schema", None, None, 0.0, (), 9999)
    close = prices["Close"]
    missing = tuple(ticker for ticker in config.stable_sectors if close[ticker].dropna().empty)
    if missing:
        return DataAudit(False, "missing_primary_tickers", None, None, 0.0, missing, 9999)
    common_start = max(close[ticker].first_valid_index() for ticker in config.stable_sectors)
    stable_window = close.loc[common_start:, list(config.stable_sectors)]
    coverage = stable_window.notna().mean()
    minimum_coverage = float(coverage.min()) if not coverage.empty else 0.0
    latest = prices.dropna(how="all").index.max()
    expected = pd.Timestamp(latest_completed_session_cutoff(captured_at))
    stale_sessions = max(0, len(pd.bdate_range(latest + pd.offsets.BDay(1), expected)))
    passed = (
        not missing
        and minimum_coverage >= config.minimum_primary_coverage
        and stale_sessions <= config.maximum_staleness_sessions
        and latest <= expected
    )
    return DataAudit(
        passed,
        "passed" if passed else "failed",
        latest.date().isoformat(),
        common_start.date().isoformat(),
        minimum_coverage,
        missing,
        stale_sessions,
    )


def load_price_snapshot(manifest_path: Path) -> pd.DataFrame:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    data_path = manifest_path.parent / str(manifest["data_file"])
    if file_sha256(data_path) != manifest["data_file_sha256"]:
        raise MarketDataError("Price snapshot data file failed its hash check.")
    frame = pd.read_parquet(data_path)
    frame.columns = pd.MultiIndex.from_tuples(frame.columns, names=["field", "ticker"])
    frame.index = pd.DatetimeIndex(pd.to_datetime(frame.index)).tz_localize(None)
    return frame


def latest_price_manifest(output_dir: Path) -> Path:
    paths = sorted(output_dir.glob("prices-*.manifest.json"))
    if not paths:
        raise FileNotFoundError(f"No price snapshots exist in {output_dir}.")
    return paths[-1]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
