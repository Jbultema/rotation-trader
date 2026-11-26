import hashlib
import json

from rotation_trader.system_identity import identity


def test_native_primary_requires_the_hash_bound_actual_selection(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "config/default.toml").write_text("test = true\n")
    assert identity(tmp_path)["primary"] is None
    root = tmp_path / "reports/latest"
    root.mkdir(parents=True)
    path = root / "research_summary.json"
    path.write_text(json.dumps({"selected_specification": {"family": "frozen"}}))
    (root / "run_manifest.json").write_text(json.dumps({"artifacts": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()}}))
    assert identity(tmp_path)["native_specification"] == {"family": "frozen"}
    path.write_text(json.dumps({"selected_specification": {"family": "tampered"}}))
    assert identity(tmp_path)["primary"] is None
