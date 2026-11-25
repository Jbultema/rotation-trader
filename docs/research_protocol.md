# Frozen Research Protocol

Protocol version: rotation-v1-2026-11-24

This document is frozen before the first Rotation Trader performance search.

## Non-duplication contract

Rotation Trader is not a replacement for Trade-bot or Swing Trader.

- It does not produce a whole-portfolio macro risk budget.
- It does not search a general cross-asset or individual-stock momentum universe.
- It does not claim plain 12-month dual momentum, a SPY moving-average filter, or a
  generic volatility target as a new sector-rotation result.
- It treats those mechanisms as baselines or controls.
- A candidate must add sector-transition information and must be behaviorally distinct
  from the Swing Trader dual-momentum baseline to qualify as Rotation Trader research.
- It contains no imports from the other repositories. Future comparison uses serialized
  result contracts, not cross-project strategy calls.

## Question

Can sector rank migration, leadership diffusion, persistence, acceleration, breadth,
dispersion, or defensive transition information improve the risk-adjusted outcome of
plain dual momentum after realistic costs?

## Primary universe

The primary universe is XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, and XLY. These funds
share a December 1998 start and avoid backfilling XLC and XLRE into periods when the
current 11-sector taxonomy was not investable. XLC and XLRE are extension diagnostics.

This ETF universe is still today's surviving fund set and does not reconstruct historical
constituent membership. Conclusions apply to rotation among these investable funds, not
to a survivor-free stock-industry portfolio.

## Timing and costs

Signals are measured at a completed regular-session close. New weights become effective
at the next regular-session open. Returns are measured open to open. The primary cost is
10 basis points for each unit of one-way risky-asset turnover. Sensitivities include 5,
20, and 40 basis points.

## Data partitions

- Development: inception through 2011-12-30.
- Validation: 2012-01-03 through 2018-12-31.
- Sealed holdout: 2019-01-02 through 2023-12-29.
- Forward diagnostic: 2024-01-02 onward.

Variant selection may use only development and validation. The holdout is opened once,
after the candidate registry and selector are fixed. Post-2024 results are diagnostic,
not a replacement holdout.

## Multiple testing

Every generated variant counts as a trial. Reports include the full registry,
family-level winners, parameter-neighborhood sensitivity, combinatorially symmetric
cross-validation/PBO, a deflated Sharpe diagnostic, block-bootstrap uncertainty, and
walk-forward stability. Failed hypotheses remain in the experiment log.

## Promotion

Promotion requires positive development and validation CAGR, validation Sharpe of at
least 0.45, validation drawdown no worse than -35%, annual turnover no greater than 12x,
positive relative results in at least 60% of walk-forward windows, and behavior that is
not effectively identical to plain dual momentum. Holdout and bootstrap evidence can
reject promotion but cannot tune the frozen candidate.

## Forward-looking drivers

Drivers without long point-in-time histories are monitoring-only until they earn
prospective evidence. Revised macro series, current classifications, news narratives,
and provider-derived estimates may not silently enter the historical selector.

## Post-holdout adversarial extension

Wave 1 opened the 2019-2023 holdout once and did not promote its selected candidate.
All mechanisms added after that event are labeled `research_wave=2`. They may be tested
against every historical period for falsification and diagnosis, but 2019-2023 is no
longer a pristine holdout for those mechanisms. No Wave 2 result can be historically
promoted. A candidate that clears all historical gates must still complete a prospective
shadow period before it can become an actionable model.

Wave 2 adds only sector-relative mechanisms: rank-entry events, named sector-pair
transitions, multi-signal transition confirmation, leader-crowding penalties,
correlation-conditioned rotation-signal strength, and market-proxy echo confirmation.
Context proxies may confirm sector leadership but may not set a broad macro risk budget.

## Wave 3 allocation and timing extension

Wave 3 was registered after the original holdout had been opened. It evaluates whether
sector selection and exposure timing can operate as one native strategy rather than as a
post-strategy overlay. Its 1,098 variants add dynamic holding counts, confidence-weighted
and inverse-volatility allocations, sector caps, staged market confirmation, transition
rebalances, target-volatility sizing, dispersion penalties, and faster defensive re-entry.

Timing uses only completed-close market evidence: fast and slow SPY trends, sector
breadth, and the share of sectors with positive momentum. The staged states are risk-on,
watch, warning, and defensive, each with an explicit exposure budget. Unallocated cash
earns a lagged public 13-week Treasury-bill yield proxy (`^IRX`); the prior completed
close is converted from annual yield to a daily return so no contemporaneous yield leaks
into the backtest.

Wave 3 is diagnostic and prospective-only. It cannot regain a pristine historical
holdout. A separate challenger is reported so a simple frozen selector cannot hide the
best native allocation/timing model, but the same promotion gates remain binding.

## Waves 4 and 5 regime robustness

Wave 4 adds continuous rather than threshold-only exposure, asymmetric exit/re-entry
confirmation, defensive-sector substitution, and combined regime-balanced variants.
Wave 5 adds always-invested and timed core-satellite portfolios: a diversified sector
core plus a concentrated rotation sleeve. These mechanisms directly test whether missed
normal-market compounding is caused by cash substitution rather than weak ranking.

The regime challenger is selected using pre-2019 evidence only. Its gate requires
competitive development and validation returns, no more than two percentage points of
annualized normal-market lag, positive transition and active-break excess return, at
least two percentage points of validation drawdown improvement, acceptable turnover,
and positive relative performance in at least 60% of walk-forward windows.

Point-in-time market states use only current and trailing SPY information. `normal`
requires intact trend and non-extreme volatility. `break` requires active rapid loss or
a drawdown of at least 10% combined with weak fast trend and high volatility. Remaining
sessions are `transition`, including repair periods. State labels are evaluation strata,
not additional trading inputs. Waves 4 and 5 are permanently prospective-only because
the historical holdout had already been opened.
