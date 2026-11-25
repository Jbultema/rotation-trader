from __future__ import annotations

import math

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def performance_metrics(
    returns: pd.Series,
    *,
    turnover: pd.Series | None = None,
) -> dict[str, float | int | str]:
    clean = returns.fillna(0.0).astype(float)
    if clean.empty:
        raise ValueError("Returns cannot be empty.")
    years = max(len(clean) / TRADING_DAYS, 1.0 / TRADING_DAYS)
    equity = (1.0 + clean).cumprod()
    final = float(equity.iloc[-1])
    cagr = final ** (1.0 / years) - 1.0
    volatility = float(clean.std(ddof=1) * math.sqrt(TRADING_DAYS))
    annual_return = float(clean.mean() * TRADING_DAYS)
    downside = clean.clip(upper=0.0)
    downside_vol = float(np.sqrt((downside**2).mean()) * math.sqrt(TRADING_DAYS))
    drawdown = equity / equity.cummax() - 1.0
    losses = clean[clean <= clean.quantile(0.05)]
    result: dict[str, float | int | str] = {
        "start": clean.index.min().date().isoformat(),
        "end": clean.index.max().date().isoformat(),
        "sessions": int(len(clean)),
        "years": years,
        "final_equity": final,
        "cagr": cagr,
        "annualized_volatility": volatility,
        "sharpe_zero_rf": annual_return / volatility if volatility > 0 else 0.0,
        "sortino_zero_rf": annual_return / downside_vol if downside_vol > 0 else 0.0,
        "max_drawdown": float(drawdown.min()),
        "calmar": cagr / abs(float(drawdown.min())) if drawdown.min() < 0 else 0.0,
        "worst_day": float(clean.min()),
        "cvar_95_daily": float(losses.mean()) if not losses.empty else 0.0,
        "positive_day_rate": float((clean > 0.0).mean()),
    }
    if turnover is not None:
        aligned = turnover.reindex(clean.index).fillna(0.0)
        result["average_daily_turnover"] = float(aligned.mean())
        result["annualized_turnover"] = float(aligned.mean() * TRADING_DAYS)
    return result


def max_drawdown(returns: pd.Series) -> float:
    equity = (1.0 + returns.fillna(0.0)).cumprod()
    return float((equity / equity.cummax() - 1.0).min())
