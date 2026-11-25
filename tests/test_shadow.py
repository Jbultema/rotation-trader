import json
from pathlib import Path

import rotation_trader.shadow as shadow_module
from rotation_trader.audit import AuditResult
from rotation_trader.shadow import _read_records, record_shadow_decisions


def test_read_records_ignores_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "shadow.jsonl"
    path.write_text(json.dumps({"record_id": "one"}) + "\n\n", encoding="utf-8")

    assert _read_records(path) == [{"record_id": "one"}]


def test_records_selector_and_allocation_timing_challenger_idempotently(
    tmp_path: Path,
    monkeypatch,
) -> None:
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    summary = {
        "selected_variant_id": "selector-one",
        "protocol_phase": "post_holdout_allocation_timing_wave_3",
        "promotion_status": "research_candidate_not_promoted",
        "historical_gates_passed": False,
        "latest_decision": {
            "as_of_close": "2026-11-24",
            "leadership_state": "transition",
            "target_weights": {},
            "cash_weight": 1.0,
            "effective_at": "next_open",
        },
        "allocation_timing_challenger": {
            "variant_id": "challenger-one",
            "latest_decision": {
                "as_of_close": "2026-11-24",
                "leadership_state": "transition",
                "target_weights": {"XLV": 0.4},
                "cash_weight": 0.6,
                "timing_stage": 1,
                "sleeve_exposure": 0.4,
                "effective_at": "next_open",
            },
        },
    }
    (report_dir / "research_summary.json").write_text(
        json.dumps(summary),
        encoding="utf-8",
    )
    (report_dir / "run_manifest.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        shadow_module,
        "audit_research_run",
        lambda _: AuditResult(
            status="passed",
            passed=True,
            artifacts_checked=2,
            selected_variant_id="selector-one",
            promoted=False,
        ),
    )
    journal = tmp_path / "shadow.jsonl"

    first = record_shadow_decisions(report_dir, journal)
    second = record_shadow_decisions(report_dir, journal)

    assert len(first) == 2
    assert first == second
    assert len(_read_records(journal)) == 2
    assert [record["candidate_role"] for record in first] == [
        "selected_candidate",
        "allocation_timing_challenger",
    ]
    assert first[1]["timing_stage"] == 1
