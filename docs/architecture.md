# Architecture and Ownership Boundaries

## System boundary

Rotation Trader owns one decision: which economic sectors are gaining or losing durable
leadership, and whether a sector transition has enough independent confirmation to merit
a long-only sector allocation candidate.

It does not own:

- the investor's total risk budget, macro crash posture, or whole-portfolio allocation;
- general stock or cross-asset swing selection;
- brokerage execution, tax-lot choice, leverage, options, derivatives, or shorting.

## Non-duplication controls

Trade-bot remains the broad portfolio and macro/cycle risk system. Swing Trader remains
the general momentum/swing system. Rotation Trader uses a plain 12-month sector
dual-momentum implementation only as a named control. It cannot be selected as a
Rotation Trader innovation.

The code has no imports from either repository. Comparison occurs through the versioned
`comparison_contract.json`, which contains mandate, timestamp, status, target weights,
period metrics, and behavioral overlap. Promotion requires return correlation below
0.97 and mean portfolio-weight overlap below 0.90 versus the Swing sector control.

## Data flow

1. `data.py` downloads adjusted public OHLCV through the last completed regular session.
2. A hash-locked Parquet snapshot and manifest pass coverage and staleness gates.
3. `strategy.py` computes close-known sector-relative features.
4. `backtest.py` shifts targets to the next open and charges one-way turnover costs.
5. `research.py` selects using development and validation only, hashes that selection,
   then evaluates later periods.
6. `audit.py` verifies artifact hashes and the sealed selection record.
7. `shadow.py` appends immutable, unactionable records for both the frozen selector and
   the separately identified allocation/timing challenger.

## Research waves

Wave 1 contained the original transition families and opened the 2019-2023 holdout once.
Wave 2 added adversarial mechanisms after that opening. Wave 2 results are useful for
falsification but cannot claim a pristine holdout. Any historically successful Wave 2
candidate requires prospective shadow validation.

Wave 3 adds native portfolio construction and timing: dynamic top-N, score and
inverse-volatility weighting, concentration caps, staged market confirmation,
target-volatility sizing, dispersion-aware exposure, and fast re-entry. Unallocated cash
earns the lagged `^IRX` yield. Because Wave 3 also postdates the original holdout, its
best candidate is tracked as a separate prospective challenger and cannot be promoted
from historical evidence alone.

Wave 4 separates active break protection from transition participation through continuous
exposure, asymmetric confirmation, and defensive-sector fallback. Wave 5 adds a
diversified equal- or inverse-volatility sector core beneath the concentrated rotation
sleeve. The reporting layer compares every candidate with SPY, QQQ, RSP, equal-weight
sectors, and each sector ETF over full history, fixed periods, rolling one- and three-year
windows, point-in-time states, and detected break episodes.

## Known limits

- The stable universe is today's nine original sector ETFs, not a reconstructed
  survivor-free stock-industry universe.
- Yahoo Finance is a convenient public-data source, not an institutional point-in-time
  master. Every downloaded snapshot is therefore retained and hashed.
- Current sector taxonomy extensions XLC and XLRE do not have full-history comparability
  and are not part of primary selection.
- ETF context proxies have different inception dates and may only confirm leadership;
  they do not create a whole-portfolio macro signal.
