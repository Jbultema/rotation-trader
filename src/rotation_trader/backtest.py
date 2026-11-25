from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


class BacktestError(ValueError):
    """Raised when a target portfolio violates the long-only execution contract."""


@dataclass(frozen=True)
class BacktestResult:
    net_returns: pd.Series
    gross_returns: pd.Series
    equity: pd.Series
    weights_at_open: pd.DataFrame
    one_way_turnover: pd.Series
    transaction_cost: pd.Series


def run_backtest(
    adjusted_open: pd.DataFrame,
    target_at_close: pd.DataFrame,
    *,
    one_way_cost_bps: float,
    minimum_trade_weight: float = 0.0,
    cash_returns: pd.Series | None = None,
) -> BacktestResult:
    """Execute close-known targets at the next open and value open to open."""
    opens = adjusted_open.astype(float).sort_index()
    target = target_at_close.reindex(index=opens.index, columns=opens.columns).fillna(0.0)
    _validate_targets(target)

    weights = target.shift(1).fillna(0.0)
    if minimum_trade_weight > 0:
        weights = _apply_no_trade_band(weights, minimum_trade_weight)
    risky_changes = weights.diff().fillna(weights)
    turnover = risky_changes.abs().sum(axis=1)
    cost = turnover * (one_way_cost_bps / 10_000.0)

    open_returns = opens.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan)
    held_during_interval = weights.shift(1).fillna(0.0)
    gross = (held_during_interval * open_returns).sum(axis=1, min_count=1).fillna(0.0)
    cash_weight = (1.0 - held_during_interval.sum(axis=1)).clip(lower=0.0, upper=1.0)
    if cash_returns is not None:
        gross = gross.add(
            cash_weight * cash_returns.reindex(gross.index).fillna(0.0),
            fill_value=0.0,
        )
    net = gross - cost
    equity = (1.0 + net).cumprod()
    return BacktestResult(net, gross, equity, weights, turnover, cost)


def _validate_targets(target: pd.DataFrame) -> None:
    if target.isna().any(axis=None):
        raise BacktestError("Target weights contain missing values.")
    if (target < -1e-12).any(axis=None):
        raise BacktestError("Short positions are not allowed.")
    if (target.sum(axis=1) > 1.0 + 1e-9).any():
        raise BacktestError("Gross risky-asset exposure cannot exceed 100%.")


def _apply_no_trade_band(weights: pd.DataFrame, threshold: float) -> pd.DataFrame:
    desired = weights.to_numpy(dtype=float)
    result = np.zeros(desired.shape, dtype=float)
    previous = np.zeros(desired.shape[1], dtype=float)
    for position in range(len(weights.index)):
        changed = np.abs(desired[position] - previous) >= threshold
        previous = np.where(changed, desired[position], previous)
        result[position] = previous
    return pd.DataFrame(result, index=weights.index, columns=weights.columns)
