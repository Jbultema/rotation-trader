# Research Findings

Evidence date: completed session 2026-11-25 using data through 2026-11-24.

## Bottom line

The expanded research found useful risk-control behavior but not a durable standalone
sector-rotation winner. The best core-satellite strategy improved full-history CAGR and
drawdown relative to SPY, but it did not beat SPY consistently in validation, holdout,
forward, or rolling-window tests. The strongest reproducible result remains drawdown
reduction during objectively detected regime breaks. No action is authorized.

## Scale and selection

- 4,400 variants across 28 families were tested.
- 1,746 variants in Waves 3-5 tested allocation, timing, staged exposure,
  transition-specific controls, defensive rotation, and core-satellite construction.
- 24 variants passed the original pre-holdout gates. The frozen breadth selector failed
  the holdout bootstrap and multiple-testing tests.
- Probability of backtest overfitting was 42.9%.
- Neither the allocation/timing challenger nor the regime-robust challenger passed its
  complete promotion gate.

## Full-history comparison

| Strategy | CAGR | Sharpe | Max drawdown |
| --- | ---: | ---: | ---: |
| SPY buy and hold | 8.0% | 0.50 | -55.4% |
| QQQ buy and hold | 8.3% | 0.43 | -83.1% |
| Equal-weight sectors | 9.2% | 0.57 | -52.6% |
| Swing sector control | 8.5% | 0.56 | -38.3% |
| Best core-satellite rotation | 8.8% | 0.60 | -32.1% |
| Frozen breadth selector | 6.5% | 0.55 | -27.3% |
| Volatility-managed challenger | 6.6% | 0.73 | -12.9% |
| Regime-robust challenger | 6.5% | 0.66 | -14.6% |

RSP produced an 11.1% CAGR, 0.64 Sharpe, and -59.9% maximum drawdown after its
2003-05-01 inception. It is shown in the artifacts but is not directly comparable over
the full 1999-present history.

The core-satellite result is the strongest compromise found: it kept a broad sector
core while rotating a satellite sleeve, producing higher full-history CAGR and a much
smaller drawdown than SPY. It is not promoted because the apparent edge did not survive
all out-of-sample views.

## Out-of-sample performance

| Period | SPY CAGR | Core-satellite CAGR | Volatility challenger CAGR | Regime challenger CAGR |
| --- | ---: | ---: | ---: | ---: |
| Development through 2011 | 0.6% | 5.8% | 6.0% | 5.5% |
| Validation 2012-2018 | 12.5% | 9.3% | 6.3% | 6.4% |
| One-time holdout 2019-2023 | 15.7% | 14.2% | 4.7% | 6.2% |
| Forward diagnostic 2024-2026-11-24 | 16.4% | 11.0% | 13.5% | 11.7% |

The core-satellite strategy helped most in the weak early-development era, but trailed
SPY in validation, holdout, and forward diagnostics. The defensive challengers cut
drawdown sharply, but paid too much opportunity cost in normal and transition periods.

## Rolling durability

The percentage of rolling windows that beat SPY was below 50% for every candidate:

| Strategy | One-year windows | Three-year windows |
| --- | ---: | ---: |
| Swing sector control | 43.3% | 43.0% |
| Frozen breadth selector | 38.7% | 37.8% |
| Volatility-managed challenger | 32.9% | 29.6% |
| Regime-robust challenger | 30.0% | 25.0% |

This is decisive evidence against claiming a persistent total-return edge from the
current search.

## Normal times versus regime breaks

Market states are assigned point in time from lagged SPY trend, drawdown, recent loss,
and a trailing volatility threshold. They are not named after historical crises.
Annualized arithmetic returns by state were:

| Strategy | Normal | Transition | Break |
| --- | ---: | ---: | ---: |
| SPY buy and hold | 30.4% | 15.6% | -62.5% |
| QQQ buy and hold | 37.8% | 20.9% | -84.1% |
| Equal-weight sectors | 27.7% | 18.1% | -57.8% |
| Swing sector control | 27.5% | 13.5% | -46.2% |
| Frozen breadth selector | 21.6% | 4.4% | -17.6% |
| Volatility-managed challenger | 20.0% | 5.2% | -18.5% |
| Regime-robust challenger | 21.5% | 4.8% | -20.5% |

These state rows aggregate non-contiguous sessions, so they are diagnostic annualized
returns rather than investable period CAGRs. They isolate the central trade-off: the
rotation systems protect during breaks, but the same controls create large return drag
before and after damage.

Across 27 detected break episodes, the volatility-managed challenger had a median
excess return of 2.2 percentage points versus SPY and a worst event drawdown of -8.1%,
compared with SPY's -50.4% worst event drawdown. The frozen selector had the best median
episode excess return at 3.4 percentage points, but weaker overall risk control.

## Current regime read

As of the 2026-11-24 close, the point-in-time market classifier is in `break`: SPY is
7.7% below its trailing peak, its fast and slow trends are weak, and 63-day volatility
is 19.6% versus a trailing 75th-percentile threshold of 14.5%.

The regime-robust challenger targets 51.9% sector exposure and 48.1% cash, allocated to
14.1% XLE, 19.6% XLP, and 18.2% XLV. This is a research observation, not a trade
instruction.

## Conclusion

The search has not established a standalone sector-rotation replacement for simple
buy and hold. It has established that a sector sleeve can materially reshape crash
exposure, and that a broad core plus rotating satellite is more promising than moving
the entire portfolio between sectors and cash. The next valid evidence is prospective
shadow operation and a new untouched future holdout, not additional threshold tuning on
the same history.
