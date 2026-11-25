# Research Findings

Evidence date: completed session 2026-11-24.

## Bottom line

The project now has a broad sector-transition search and a native allocation/timing
search, but no production strategy. The simple frozen selector failed after selection.
The stronger risk-control result is a volatility-managed challenger that combines sector
ranking, inverse-volatility allocation, staged exposure, a 10% volatility target, and a
dispersion penalty. No action is authorized.

## Scale and selection

- 3,272 variants across 22 families were tested.
- 1,098 variants jointly tested allocation and timing mechanisms.
- 24 variants passed the original pre-holdout gates; the selected breadth model later
  failed the holdout bootstrap and multiple-testing test.
- PBO was 34.3%. The selected model's deflated-Sharpe probability was 32.4%, below the
  50% promotion threshold.
- The allocation/timing challenger passed all primary pre-holdout level gates except
  walk-forward consistency: 40% of windows were positive versus the required 60%.

## Performance

| Period | Allocation/timing CAGR | SPY | Challenger max drawdown |
| --- | ---: | ---: | ---: |
| Development through 2011 | 6.0% | 0.6% | -11.7% |
| Validation 2012-2018 | 6.3% | 12.5% | -12.5% |
| One-time holdout 2019-2023 | 4.7% | 15.7% | -12.9% |
| Forward diagnostic 2024-2026-11-24 | 13.5% | 16.4% | -8.0% |

The challenger substantially reduced drawdown, but it gave up too much return in
validation and holdout. That is risk control, not evidence of superior total-return
timing. The strongest honest conclusion is that staged timing can control damage while
remaining invested, but its opportunity cost is still too high.

## Orthogonality

The allocation/timing challenger is not a renamed Swing strategy:

- return correlation to the Swing sector control: 0.784;
- mean target-weight overlap: 69.2%;
- different-weight days: 88.5%.

It remains related through momentum, but timing and sizing create materially different
behavior.

## Regime read

The challenger averaged 46% sector exposure in development, 75% in validation, 59% in
holdout, and 70% since 2024. It was risk-on 83% of sessions since 2024 and defensive only
3%, so it is not a static 50/50 portfolio. Its current state is warning: 40.0% sector
exposure and 60.0% cash after volatility and dispersion scaling.

## Wave 2 conclusions

- Confirmed transition produced one pre-holdout pass but degraded after selection.
- Rank crossing had an attractive 2019-2023 result but failed development and
  walk-forward stability. It is rejected as a selection trap.
- Sector-pair transitions helped some later periods but did not pass the frozen gate.
- Context echo, leadership crowding, and correlation conditioning did not improve the
  selected model.
- The adversarial ensemble did not beat the simpler original ensemble.

## Current allocation/timing read

As of the 2026-11-24 close, the prospective challenger targets 10.9% XLE, 15.1% XLP,
14.0% XLV, and 60.0% cash. Its timing stage is warning, with a nominal 50% stage budget
reduced to 40.0% by volatility and dispersion controls. This is a research observation,
not a trade instruction.

The correct next evidence is prospective shadow behavior and a truly new future holdout,
not more threshold optimization over the same history.
