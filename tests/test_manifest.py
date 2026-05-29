"""Manifest / packaging guards.

HACS reads ``version`` to detect updates, and newer HA cores warn when
``integration_type`` is missing. These also keep manifest.json and
pyproject.toml from drifting apart.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_MANIFEST = _ROOT / "custom_components" / "trannergy" / "manifest.json"
_PYPROJECT = _ROOT / "pyproject.toml"

_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def _manifest() -> dict:
    return json.loads(_MANIFEST.read_text(encoding="utf-8"))


def test_manifest_core_fields() -> None:
    m = _manifest()
    assert m["domain"] == "trannergy"
    assert m["config_flow"] is True
    # A single inverter endpoint is a "device", polled locally.
    assert m["integration_type"] == "device"
    assert m["iot_class"] == "local_polling"


def test_manifest_version_is_semver() -> None:
    assert _SEMVER.match(_manifest()["version"]), "version must be X.Y.Z for HACS"


def test_manifest_version_matches_pyproject() -> None:
    manifest_version = _manifest()["version"]
    text = _PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert match, "pyproject.toml must declare a version"
    assert match.group(1) == manifest_version, (
        f"pyproject version {match.group(1)} != manifest version {manifest_version}"
    )
