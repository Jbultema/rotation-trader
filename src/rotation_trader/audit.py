from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from rotation_trader.provenance import file_sha256, verify_hashed_json


@dataclass(frozen=True)
class AuditResult:
    passed: bool
    status: str
    artifacts_checked: int
    selected_variant_id: str | None
    promoted: bool


def audit_research_run(run_dir: Path) -> AuditResult:
    manifest_path = run_dir / "run_manifest.json"
    summary_path = run_dir / "research_summary.json"
    selection_path = run_dir / "selection_before_holdout.json"
    if not all(path.exists() for path in (manifest_path, summary_path, selection_path)):
        return AuditResult(False, "missing_required_artifact", 0, None, False)
    if not all(verify_hashed_json(path) for path in (manifest_path, summary_path, selection_path)):
        return AuditResult(False, "record_hash_failed", 0, None, False)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checked = 0
    for name, expected in manifest.get("artifacts", {}).items():
        path = run_dir / name
        if not path.exists() or file_sha256(path) != expected:
            return AuditResult(False, f"artifact_hash_failed:{name}", checked, None, False)
        checked += 1
    return AuditResult(
        True,
        "passed",
        checked,
        manifest.get("selected_variant_id"),
        bool(manifest.get("promoted")),
    )
