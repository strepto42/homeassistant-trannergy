"""Cross-file sensor-key consistency guard.

A sensor key must line up across four files (see CLAUDE.md):
  const.SENSOR_KEYS  <->  sensor.SENSOR_TYPES  <->  strings.json  <->  en.json

This catches the classic "added a sensor in one place but not the others" bug
without importing Home Assistant (sensor.py is read via AST, const.py is pure
constants and loaded standalone).
"""

from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
from types import ModuleType

_PKG = Path(__file__).resolve().parent.parent / "custom_components" / "trannergy"


def _load_const() -> ModuleType:
    spec = importlib.util.spec_from_file_location("trannergy_const", _PKG / "const.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sensor_types_keys() -> set[str]:
    """Extract the string keys of the SENSOR_TYPES dict literal via AST.

    Handles both plain (``SENSOR_TYPES = {...}``) and annotated
    (``SENSOR_TYPES: dict[...] = {...}``) assignments.
    """
    tree = ast.parse((_PKG / "sensor.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        targets = (
            node.targets
            if isinstance(node, ast.Assign)
            else [node.target]
            if isinstance(node, ast.AnnAssign)
            else []
        )
        for target in targets:
            if isinstance(target, ast.Name) and target.id == "SENSOR_TYPES":
                assert isinstance(node.value, ast.Dict)
                return {
                    k.value
                    for k in node.value.keys
                    if isinstance(k, ast.Constant) and isinstance(k.value, str)
                }
    raise AssertionError("SENSOR_TYPES dict not found in sensor.py")


def _options_data_keys(filename: str) -> set[str]:
    data = json.loads((_PKG / filename).read_text(encoding="utf-8"))
    return set(data["options"]["step"]["init"]["data"]) - {"scan_interval"}


def test_sensor_keys_match_sensor_types() -> None:
    const = _load_const()
    assert set(const.SENSOR_KEYS) == _sensor_types_keys()


def test_default_sensors_subset_of_keys() -> None:
    const = _load_const()
    assert set(const.DEFAULT_SENSORS) <= set(const.SENSOR_KEYS)


def test_sensor_keys_present_in_strings_and_translations() -> None:
    const = _load_const()
    keys = set(const.SENSOR_KEYS)
    assert keys <= _options_data_keys("strings.json")
    assert keys <= _options_data_keys("translations/en.json")
