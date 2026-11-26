"""Resolve the actual frozen selection without reselecting a historical winner."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def identity(root=Path(".")):
    config = root / "config/default.toml"
    summary = root / "reports/latest/research_summary.json"
    manifest = root / "reports/latest/run_manifest.json"
    selected, verified = None, False
    if summary.exists() and manifest.exists():
        metadata = json.loads(manifest.read_text())
        verified = metadata.get("artifacts", {}).get(summary.name) == hashlib.sha256(summary.read_bytes()).hexdigest()
        if verified:
            selected = json.loads(summary.read_text())["selected_specification"]
    return {"schema_version": 1, "system": "rotation-trader", "role": "sector_leadership",
        "primary": "rotation_primary" if verified else None, "native_specification": selected,
        "configuration_consistent": verified, "primary_source": "reports/latest/research_summary.json:selected_specification",
        "native_clock": "next_adjusted_open_open_to_open",
        "configuration_sha256": {"config/default.toml": hashlib.sha256(config.read_bytes()).hexdigest()},
        "selected_artifact_sha256": hashlib.sha256(summary.read_bytes()).hexdigest() if verified else None,
        "action_authorized": False, "portfolio_allocation_allowed": False}


if __name__ == "__main__":
    print(json.dumps(identity(), sort_keys=True))
