# Rotation Trader

Rotation Trader is a personal, research-only sector leadership and transition system.
It produces explainable allocations for human review and execution. It has no broker
connection, never places orders, and supports only long positions in unlevered public
ETFs or cash.

## Distinct mandate

- Trade-bot owns broad portfolio construction, macro/cycle state, and risk budgets.
- Swing Trader owns general momentum and swing research across assets and stocks.
- Rotation Trader owns sector rank migration, leadership diffusion, transition timing,
  and allocation among economic sectors.

The existing Swing Trader 12-month dual-momentum strategy is a comparator here, not a
Rotation Trader invention. Rotation Trader does not import or depend on either project.

The primary historical universe is the nine original Select Sector SPDR ETFs. XLC and
XLRE are extension diagnostics because they did not exist for the full history.

## Safety contract

- Signals use information available at a completed close.
- A changed allocation can execute no earlier than the next regular-session open.
- Costs and turnover are charged explicitly.
- Missing or stale required data fails closed.
- Backtests never authorize a trade.
- Every recommendation remains human-executed.

See the frozen research protocol and hypothesis registry under docs.

## Current research status

As of the completed 2026-11-24 session, 3,272 registered variants across 22 families
have been tested. Of these, 1,098 Wave 3 variants jointly search sector allocation and
market timing. The frozen selector and the best native allocation/timing challenger both
remain research candidates, not actionable strategies. The challenger materially lowers
historical drawdown, but failed the predeclared walk-forward consistency gate and requires
prospective shadow evidence.

## Quick start

```bash
poetry install --sync
poetry run rotation-trader fetch-data
poetry run rotation-trader research
poetry run rotation-trader audit
poetry run rotation-trader record-shadow
poetry run rotation-trader dashboard --port 8503
```

`poetry run rotation-trader run` performs the refresh, full frozen research, audit-backed
shadow record, and no brokerage action. The dashboard is available at
`http://localhost:8503` while its command is running.

## Repository map

- `strategy.py`: sector-relative leadership and transition mechanics.
- `backtest.py`: next-open, long-only, cost-aware execution simulator.
- `validation.py`: blind selection, PBO, deflated Sharpe, bootstrap, and stability gates.
- `research.py`: frozen experiment orchestration and hashed artifacts.
- `shadow.py`: idempotent prospective journal for both the selector and the native
  allocation/timing challenger.
- `dashboard.py`: operational evidence and current sector read.
- `docs/`: protocol, architecture, findings, operations, and roadmap.

The research basis includes published work on
[industry momentum](https://doi.org/10.1111/0022-1082.00146),
[time-series momentum](https://doi.org/10.1016/j.jfineco.2011.11.003),
[probability of backtest overfitting](https://doi.org/10.3905/jpm.2016.42.4.069), and
[deflated Sharpe ratios](https://doi.org/10.3905/jpm.2014.40.5.094).
