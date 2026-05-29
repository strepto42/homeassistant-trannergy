"""Shared test fixtures.

The API-client tests must run on any OS (including native Windows) without
Home Assistant installed. Importing ``custom_components.trannergy.api`` the
normal way would execute the package ``__init__.py``, which imports Home
Assistant. To avoid that, we load ``api.py`` directly from its file path — it is
deliberately self-contained (only stdlib: asyncio, struct, logging).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_API_PATH = _REPO_ROOT / "custom_components" / "trannergy" / "api.py"


def _load_module(name: str, path: Path) -> ModuleType:
    """Load a module from a file path, bypassing the HA package __init__."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def api_module() -> ModuleType:
    """The standalone-loaded Trannergy API client module."""
    return _load_module("trannergy_api", _API_PATH)
