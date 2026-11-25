# Cleanup And Quality: November 25, 2026

Calendar scheduling now uses planned regular exchange holidays rather than the last row of
a partial input file. Frozen target specifications are rebuilt for export under that calendar;
cached selections are verified, never silently reselected by the exporter.

Adversarial execution tests reject missing target sessions, unknown instruments, duplicate
dates, nonfinite costs, missing cash and unpriced holding intervals. Actual frozen-slate replay
exposed a no-trade-band defect: independently retaining small old positions while adding new
ones could produce more than 100% exposure. The engine now executes the complete desired
basket whenever partial application would over-invest, including the required sell costs.

This is not a full accounting rewrite. Native returns still use target-weight resetting and
an approximate cost convention; common Portfolio Lab replay uses drifting, self-financing
holdings. Native performance must be fully rebaselined under corrected drift accounting before
claiming execution realism. A passed landscape rerun does not remove that limitation.

The full 4,400-variant validation is written separately under
`reports/cleanup_validation_final_20261125/`, leaving the existing primary selection untouched.
No new strategy is promoted by this cleanup. All generated datasets/reports remain local.

The cross-system verifier and assessment are in Portfolio Lab at
`scripts/verify_workspace.py` and `docs/system_assessment_20261125.md`.
