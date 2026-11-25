from pathlib import Path

from rotation_trader.audit import audit_research_run
from rotation_trader.provenance import file_sha256, write_hashed_json


def test_audit_detects_artifact_tampering(tmp_path: Path) -> None:
    artifact = tmp_path / "metrics.csv"
    artifact.write_text("value\n1\n", encoding="utf-8")
    write_hashed_json(
        tmp_path / "selection_before_holdout.json",
        {"selected_variant_id": "candidate"},
    )
    write_hashed_json(
        tmp_path / "research_summary.json",
        {"promotion_status": "candidate"},
    )
    write_hashed_json(
        tmp_path / "run_manifest.json",
        {
            "selected_variant_id": "candidate",
            "promoted": False,
            "artifacts": {"metrics.csv": file_sha256(artifact)},
        },
    )

    assert audit_research_run(tmp_path).passed is True
    artifact.write_text("value\n2\n", encoding="utf-8")
    result = audit_research_run(tmp_path)
    assert result.passed is False
    assert result.status == "artifact_hash_failed:metrics.csv"
