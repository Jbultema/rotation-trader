# Hypothesis Registry

Registered before performance search on 2026-11-24.

## Rotation-specific families

1. Relative-strength acceleration and deceleration.
2. Rank migration velocity and rank-crossing events.
3. Leadership persistence and leadership half-life.
4. Leadership diffusion versus narrow concentration.
5. Sector breadth confirmation and breadth divergence.
6. Cross-sector dispersion and correlation-regime conditioning.
7. Defensive-to-cyclical and cyclical-to-defensive transition meshes.
8. Sector-pair relative trends tied to growth, inflation, rates, and credit.
9. Early versus confirmed transition staging.
10. Transition ensembles that require independent sector-level confirmation.
11. Rank buffers, minimum holding periods, and no-trade bands.
12. Monthly, biweekly, and weekly observation/execution schedules.
13. Equal weight, inverse volatility, and correlation-aware sector sizing.
14. Stable nine-sector universe versus inception-aware taxonomy extensions.
15. Market-based context from credit, duration, commodities, the dollar, small caps,
    equal-weight breadth, and semiconductor leadership.

## Mandatory comparators, not innovations

1. SPY buy and hold.
2. Equal-weight nine sectors.
3. SPY 200-day trend.
4. Plain top-three 12-month dual momentum matching Swing Trader semantics.
5. Defensive cash and defensive-sector fallback variants.

## Adversarial tests

- Shift every signal by an additional session.
- Compare next-open execution with the impossible same-close upper bound.
- Remove XLK and remove each sector one at a time.
- Raise costs to 20 and 40 basis points.
- Perturb lookbacks, trend windows, top-N, and rebalance dates.
- Test crisis, inflation, rate-shock, and narrow-leadership subperiods.
- Measure behavioral correlation and decision overlap with the Swing baseline.
- Measure degradation from development to validation and holdout.
- Count all trials in PBO and deflated-Sharpe diagnostics.

No family is entitled to promotion. A null result is acceptable.

## Wave 2 registration

Registered on 2026-11-24 after Wave 1 had opened the sealed holdout. These are
adversarial extensions, not fresh-holdout hypotheses:

1. `rank_crossing_event`: reward actual entries into the leadership set and penalize exits.
2. `sector_pair_transition`: combine XLY/XLP, XLI/XLU, XLK/XLU, XLF/XLV,
   XLE/XLK, and XLB/XLK relative transitions.
3. `confirmed_transition`: require agreement among acceleration, rank velocity,
   persistence, and pair transitions.
4. `leadership_crowding`: penalize an isolated leader when its score gap is extreme.
5. `correlation_conditioned_rotation`: reduce only the incremental rotation score when
   sectors are moving as one market.
6. `context_echo_confirmation`: use public ETF proxies to confirm sector leadership;
   proxies are never traded and never set the portfolio-wide risk budget.
7. `adversarial_transition_ensemble`: limited combinations of the mechanisms above.

Wave 2 is permanently marked in the machine-readable registry and requires prospective
shadow validation even if all historical gates pass.

## Wave 3 registration

Registered on 2026-11-24 after the sealed holdout had already been opened. These 1,098
variants test allocation and timing jointly:

1. `adaptive_confidence_allocation`: dynamic holding counts plus capped score-softmax or
   inverse-volatility confidence sizing.
2. `staged_market_timing`: risk-on, watch, warning, and defensive exposure budgets from
   fast/slow market trend, sector breadth, and positive sector momentum.
3. `adaptive_timed_rotation`: dynamic sector selection combined with staged timing and
   timing-transition rebalances.
4. `fast_defensive_reentry`: asymmetric confirmation that seeks to re-enter faster after
   market repair without weakening the initial defensive gate.
5. `volatility_managed_rotation`: staged timing plus target-volatility and cross-sector
   dispersion controls.

The search spans holding-count bounds, weighting temperature, sector caps, fast/slow
trend windows, confirmation windows, stage exposure budgets, target volatility, and
dispersion penalties. Every combination remains in the frozen registry and trial count.

## Wave 4 registration

Registered after every historical holdout had been opened. The 480 variants test:

1. `continuous_regime_exposure`: continuous evidence-scaled exposure instead of discrete
   threshold jumps.
2. `asymmetric_transition_timing`: separate deterioration and repair confirmation delays.
3. `defensive_rotation_blend`: rotate part of removed exposure into ranked defensive
   sectors rather than cash.
4. `regime_balanced_rotation`: combine continuous or staged timing, volatility control,
   dispersion control, and defensive substitution.

## Wave 5 registration

Registered after Wave 4 failed its substantial-edge gate. The 648 variants test:

1. `core_satellite_rotation`: an always-invested diversified sector core plus a ranked
   rotation tilt.
2. `timed_core_satellite_rotation`: independent core size, core weighting, defensive
   core floor, satellite weighting, timing mode, and volatility control.

Wave 5 tests whether maintaining broad sector exposure repairs normal-market opportunity
cost without discarding break protection. It is prospective-only and cannot be promoted
from the already-examined historical periods.
