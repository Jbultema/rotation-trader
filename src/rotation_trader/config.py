from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DataConfig:
    start: str
    benchmark: str
    stable_sectors: tuple[str, ...]
    extension_sectors: tuple[str, ...]
    context_tickers: tuple[str, ...]
    maximum_staleness_sessions: int
    minimum_primary_coverage: float


@dataclass(frozen=True)
class ExecutionConfig:
    initial_capital: float
    commission_bps: float
    slippage_bps: float
    minimum_trade_weight: float

    @property
    def total_one_way_cost_bps(self) -> float:
        return self.commission_bps + self.slippage_bps


@dataclass(frozen=True)
class ResearchConfig:
    development_end: str
    validation_start: str
    validation_end: str
    holdout_start: str
    holdout_end: str
    forward_diagnostic_start: str
    minimum_history_sessions: int
    bootstrap_samples: int
    bootstrap_block_sessions: int
    pbo_partitions: int
    random_seed: int


@dataclass(frozen=True)
class PromotionConfig:
    minimum_development_cagr: float
    minimum_validation_cagr: float
    minimum_validation_sharpe: float
    maximum_validation_drawdown: float
    maximum_annual_turnover: float
    minimum_positive_walk_forward_windows: float


@dataclass(frozen=True)
class AppConfig:
    data: DataConfig
    execution: ExecutionConfig
    research: ResearchConfig
    promotion: PromotionConfig


def load_config(path: Path | str) -> AppConfig:
    with Path(path).open("rb") as handle:
        raw = tomllib.load(handle)
    data = raw["data"]
    return AppConfig(
        data=DataConfig(
            **data
            | {
                "stable_sectors": tuple(data["stable_sectors"]),
                "extension_sectors": tuple(data["extension_sectors"]),
                "context_tickers": tuple(data["context_tickers"]),
            }
        ),
        execution=ExecutionConfig(**raw["execution"]),
        research=ResearchConfig(**raw["research"]),
        promotion=PromotionConfig(**raw["promotion"]),
    )
