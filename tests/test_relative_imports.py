"""Integration modules must import siblings via relative imports.

``from custom_components.trannergy.X import Y`` couples the integration to its
on-disk path. HA convention is ``from .X import Y``.
"""

from __future__ import annotations

from pathlib import Path

_PACKAGE = Path(__file__).resolve().parent.parent / "custom_components" / "trannergy"


def test_no_module_uses_absolute_self_imports() -> None:
    offenders: list[str] = []
    for py in _PACKAGE.glob("*.py"):
        if "from custom_components.trannergy" in py.read_text(encoding="utf-8"):
            offenders.append(py.name)

    assert not offenders, (
        f"these modules use absolute self-imports instead of relative: {offenders}"
    )
