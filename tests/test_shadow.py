import json
from pathlib import Path

from rotation_trader.shadow import _read_records


def test_read_records_ignores_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "shadow.jsonl"
    path.write_text(json.dumps({"record_id": "one"}) + "\n\n", encoding="utf-8")

    assert _read_records(path) == [{"record_id": "one"}]
