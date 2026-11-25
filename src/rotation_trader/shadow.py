from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from rotation_trader.audit import audit_research_run
from rotation_trader.provenance import file_sha256


def record_shadow_decision(report_dir: Path, journal_path: Path) -> dict[str, object]:
    audit = audit_research_run(report_dir)
    if not audit.passed:
        raise ValueError("Research artifacts failed audit; shadow decision was not recorded.")
    summary_path = report_dir / "research_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    decision = summary.get("latest_decision")
    if not isinstance(decision, dict):
        raise ValueError("Research run has no selected decision to shadow.")
    identity = "|".join(
        [
            str(summary.get("selected_variant_id")),
            str(decision.get("as_of_close")),
            str(summary.get("protocol_phase")),
        ]
    )
    record_id = hashlib.sha256(identity.encode()).hexdigest()[:20]
    existing = _read_records(journal_path)
    matched = next((record for record in existing if record.get("record_id") == record_id), None)
    if matched is not None:
        return matched
    record = {
        "schema_version": 1,
        "record_type": "rotation_shadow_decision",
        "record_id": record_id,
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        "as_of_close": decision["as_of_close"],
        "selected_variant_id": summary["selected_variant_id"],
        "protocol_phase": summary["protocol_phase"],
        "promotion_status": summary["promotion_status"],
        "historical_gates_passed": summary.get("historical_gates_passed", False),
        "leadership_state": decision["leadership_state"],
        "target_weights": decision["target_weights"],
        "cash_weight": decision["cash_weight"],
        "effective_at": decision["effective_at"],
        "action_authorized": False,
        "research_summary_sha256": file_sha256(summary_path),
        "run_manifest_sha256": file_sha256(report_dir / "run_manifest.json"),
    }
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    with journal_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    return record


def _read_records(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
