"""Approved contract schemas, used to validate HTTP input and canonical forms."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

SCHEMA = json.loads((Path(__file__).resolve().parents[3] / "contracts/schemas/f1.schema.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def _validator(name: str) -> Draft202012Validator:
    return Draft202012Validator({"$ref": f"#/$defs/{name}", "$defs": SCHEMA["$defs"]}, format_checker=FormatChecker())


def is_valid(name: str, value) -> bool:
    return _validator(name).is_valid(value)


def canonical(value) -> bytes:
    """Canonical JSON shared with the database: sorted keys, no spaces, raw UTF-8."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_hex(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()
