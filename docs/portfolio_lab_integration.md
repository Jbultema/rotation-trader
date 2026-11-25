# Portfolio Lab Integration And Causal Schedule Repair

Rotation Trader owns sector leadership and sector transition allocation/timing, not the whole
portfolio budget. Portfolio Lab owns cross-specialist allocation and common evaluation.

```sh
poetry run python -m rotation_trader.portfolio_export --output ../portfolio-lab/data/bundles/RUN/rotation-trader
```

The export verifies native price, target and research-summary hashes, preserves the frozen
selected specifications, and rebuilds their targets under the corrected schedule. It does not
choose a new winner from full-history CAGR. Slow-126 and adaptive-42 timing arms are separate
research controls, not promoted replacements for the existing selection.

## Defect corrected

The old period grouping treated the final captured row as the last session of its month/week,
even when the file stopped mid-period. New schedules use preplanned NYSE regular holidays,
handle Good Friday and year boundaries, and do not anticipate unscheduled emergency closures.
Prefix-invariance tests cover monthly, weekly and biweekly schedules. Biweekly phase remains
anchored to the first input week, so input starts must remain fixed in comparative research.

Old reports remain preserved as old-code evidence. The export reconstructs fixed specifications
rather than silently using their outdated tail targets. Portfolio Lab's next-close, drift-aware
replay is a distinct contract from native next-open results; it must not be called native CAGR.
The earlier 4400-variant search is prior research, not new blind evidence for these corrections.
