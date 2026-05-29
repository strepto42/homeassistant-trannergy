"""HACS metadata guard: hacs.json must stay valid for the HACS validator."""

from __future__ import annotations

import json
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_HACS = _ROOT / "hacs.json"


def test_hacs_json_valid() -> None:
    data = json.loads(_HACS.read_text(encoding="utf-8"))
    assert data.get("name"), "hacs.json must declare a name"


def test_hacs_min_homeassistant_is_versioned() -> None:
    data = json.loads(_HACS.read_text(encoding="utf-8"))
    min_ha = data.get("homeassistant")
    assert min_ha, "hacs.json should pin a minimum homeassistant version"
    assert re.match(r"^\d+\.\d+", str(min_ha)), f"unparseable HA version: {min_ha}"
