# Research Findings

Evidence date: completed session 2026-11-23.

## Bottom line

The project found a credible sector-transition candidate, not a production strategy.
The selected model combines medium-term sector momentum with acceleration, rank
migration, leadership persistence, and a rank buffer. It currently ranks XLV first and
XLE second and produces a 50%/50% research target, but no action is authorized.

## Scale and selection

- 2,174 variants across 17 families were tested.
- 10 variants passed all pre-holdout development/validation gates.
- The selected family was the original transition ensemble, not a Wave 2 extension.
- Only 1 of 17 nearby parameter variants passed every pre-holdout gate, although their
  median validation CAGR was 8.7%. This is evidence of a useful neighborhood with a
  narrow full-gate result, not broad parameter indifference.
- PBO was 34.3%. The nominal 2,174-trial deflated-Sharpe probability was 24.6%, below the
  50% promotion threshold.

## Performance

| Period | Rotation candidate CAGR | Swing sector control | SPY | Candidate max drawdown |
| --- | ---: | ---: | ---: | ---: |
| Development through 2011 | 6.1% | 2.2% | 0.6% | -38.3% |
| Validation 2012-2018 | 7.7% | 8.0% | 12.5% | -19.6% |
| One-time holdout 2019-2023 | 20.6% | 20.0% | 15.7% | -32.5% |
| Forward diagnostic 2024-2026-11-23 | 15.2% | 15.6% | 16.9% | -13.3% |

The holdout excess-return bootstrap median versus SPY was 5.5% annualized, but its 95%
interval ranged from -5.8% to 16.9%. Pre-holdout excess evidence also crossed zero.

## Orthogonality

The selected candidate is not a renamed Swing strategy:

- pre-holdout return correlation to the Swing sector control: 0.914;
- mean target-weight overlap: 63.8%;
- different-weight days: 86.3%.

This clears the explicit non-duplication gates while still showing that both systems
share a material momentum component.

## Regime read

The candidate was most useful in credit expansion, the GFC relative to equity controls,
the 2020 shock/recovery, and the 2021-2023 inflation/rate shock. It lagged SPY in the
post-GFC recovery and 2013-2019 low-vol expansion. Since 2024 it has lagged both SPY and
the Swing sector control, so there is no evidence that it is presently the superior
standalone engine.

## Wave 2 conclusions

- Confirmed transition produced one pre-holdout pass but degraded after selection.
- Rank crossing had an attractive 2019-2023 result but failed development and
  walk-forward stability. It is rejected as a selection trap.
- Sector-pair transitions helped some later periods but did not pass the frozen gate.
- Context echo, leadership crowding, and correlation conditioning did not improve the
  selected model.
- The adversarial ensemble did not beat the simpler original ensemble.

The correct next evidence is prospective, not another threshold search over the same
history.
