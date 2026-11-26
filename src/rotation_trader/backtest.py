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
    """Fund changed close-known targets at the next open; otherwise hold units.

    Weights drift between decisions. Fees reduce NAV before sizing the new
    basket, including a fully invested basket; no external cash funds fees.
    """
    opens = adjusted_open.astype(float)
    if (
        opens.empty or not isinstance(opens.index, pd.DatetimeIndex)
        or opens.index.hasnans or opens.index.has_duplicates
        or not opens.index.is_monotonic_increasing or not opens.columns.is_unique
        or not target_at_close.columns.is_unique
        or not target_at_close.index.equals(opens.index)
        or not set(target_at_close) <= set(opens)
    ):
        raise BacktestError("Unique, ordered and aligned price/target frames required.")
    if (
        not np.isfinite(one_way_cost_bps) or not 0 <= one_way_cost_bps <= 100
        or not np.isfinite(minimum_trade_weight) or not 0 <= minimum_trade_weight <= 1
    ):
        raise BacktestError("Invalid transaction costs or no-trade threshold.")
    if np.isinf(opens.to_numpy()).any() or opens.le(0).any(axis=None):
        raise BacktestError("Observed adjusted opens must be positive and finite.")
    target = target_at_close.reindex(columns=opens.columns, fill_value=0.0).astype(float)
    _validate_targets(target)

    desired = target.shift(1).fillna(0.0).to_numpy(float)
    quotes = opens.to_numpy(float)
    cash = np.zeros(len(opens)) if cash_returns is None else cash_returns.reindex(opens.index).to_numpy(float)
    if not np.isfinite(cash).all() or np.any(cash <= -1):
        raise BacktestError("Cash returns must be finite and aligned.")
    held = np.zeros(len(opens.columns))
    previous_target = np.zeros(len(opens.columns))
    cash_value = nav = 1.0
    rows, net, gross, turnover, costs = [], [], [], [], []
    rate = one_way_cost_bps / 10000.0
    for i, requested in enumerate(desired):
        prior_nav = nav
        if i:
            valid = np.isfinite(quotes[i]) & np.isfinite(quotes[i - 1])
            if np.any((held > 1e-12) & ~valid):
                raise BacktestError("Unpriced held interval; no missing-return substitution.")
            growth = np.ones(len(held))
            np.divide(quotes[i], quotes[i - 1], out=growth, where=valid)
            held *= growth
            cash_value *= 1.0 + cash[i]
        pre = float(held.sum() + cash_value)
        gross.append(pre / prior_nav - 1.0)
        traded = fee = 0.0
        if not np.allclose(requested, previous_target, atol=1e-12, rtol=0):
            drifted = held / pre
            changed = np.abs(requested - drifted) >= minimum_trade_weight
            candidate = np.where(changed, requested, drifted)
            # Partial baskets can retain old risk while adding new positions.
            if candidate.sum() > 1.0 + 1e-12:
                candidate = requested.copy()
                changed[:] = True
            if changed.any():
                if np.any(((candidate > 1e-12) | (held > 1e-12)) & ~np.isfinite(quotes[i])):
                    raise BacktestError("Unpriced target holding.")
                post = pre
                for _ in range(24):
                    post = pre - rate * np.abs(candidate * post - held).sum()
                assets = candidate * post
                traded = float(np.abs(assets - held).sum() / pre)
                fee = pre - post
                held = assets
                cash_value = post - float(held.sum())
            previous_target = requested.copy()
        nav = float(held.sum() + cash_value)
        if not np.isfinite(nav) or nav <= 0 or cash_value < -1e-10:
            raise BacktestError("Self-financing invariant failed.")
        rows.append(held / nav)
        net.append(nav / prior_nav - 1.0)
        turnover.append(traded)
        costs.append(fee / pre)
    index = opens.index
    returns = pd.Series(net, index=index)
    return BacktestResult(
        returns, pd.Series(gross, index=index), returns.add(1).cumprod(),
        pd.DataFrame(rows, index=index, columns=opens.columns),
        pd.Series(turnover, index=index), pd.Series(costs, index=index),
    )


def _validate_targets(target: pd.DataFrame) -> None:
    if not np.isfinite(target.to_numpy(dtype=float)).all():
        raise BacktestError("Target weights contain missing values.")
    if (target < -1e-12).any(axis=None):
        raise BacktestError("Short positions are not allowed.")
    if (target.sum(axis=1) > 1.0 + 1e-9).any():
        raise BacktestError("Gross risky-asset exposure cannot exceed 100%.")
