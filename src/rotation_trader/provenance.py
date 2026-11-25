from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def frame_sha256(frame: pd.DataFrame) -> str:
    normalized = frame.copy()
    normalized.index = pd.Index(normalized.index.astype(str))
    payload = normalized.to_csv(index=True, lineterminator="\n").encode()
    return hashlib.sha256(payload).hexdigest()


def canonical_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def write_hashed_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = dict(payload)
    record_hash = canonical_sha256(record)
    record["record_sha256"] = record_hash
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
    return record_hash


def verify_hashed_json(path: Path) -> bool:
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = payload.pop("record_sha256", None)
    return isinstance(expected, str) and canonical_sha256(payload) == expected
