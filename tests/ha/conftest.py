"""Fixtures for the Home Assistant integration tests.

Loaded only when running under pytest-homeassistant-custom-component (CI/WSL).
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_NAME
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.trannergy.const import (
    CONF_INVERTER_HOST,
    CONF_INVERTER_PORT,
    CONF_INVERTER_SERIAL,
    CONF_SCAN_INTERVAL,
    CONF_SENSORS,
    DOMAIN,
    SENSOR_KEYS,
)

SERIAL = 1612345603


def make_online_data() -> dict[str, Any]:
    """A realistic parsed 'online' payload covering every sensor key.

    Mirrors what ``TrannergyInverterApi._parse_data`` returns for the synthetic
    frame in ``tests/frames.py``: channel 1 carries real values, 2 and 3 zero.
    """
    data: dict[str, Any] = {
        "status": "Online",
        "actualpower": 1500.0,
        "energytoday": 12.34,
        "energytotal": 5678.9,
        "hourstotal": 4321.0,
        "invertersn": "NLDN1234567890AB",
        "temperature": 25.0,
    }
    for i in range(1, 4):
        first = i == 1
        data[f"dcinputvoltage{i}"] = 320.0 if first else 0.0
        data[f"dcinputcurrent{i}"] = 5.0 if first else 0.0
        data[f"acoutputvoltage{i}"] = 240.0 if first else 0.0
        data[f"acoutputcurrent{i}"] = 6.5 if first else 0.0
        data[f"acoutputfrequency{i}"] = 50.0 if first else 0.0
        data[f"acoutputpower{i}"] = 1500.0 if first else 0.0
    return data


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None]:
    """Allow Home Assistant to load this custom integration in tests."""
    yield


@pytest.fixture
def mock_api() -> Generator[AsyncMock]:
    """Patch the inverter API so no TCP access occurs.

    Patching ``async_get_data`` covers both the coordinator's polling and the
    config flow's ``async_test_connection`` (which calls it). Tests can override
    ``return_value`` / ``side_effect`` to simulate offline behaviour.
    """
    with patch(
        "custom_components.trannergy.api.TrannergyInverterApi.async_get_data",
        new=AsyncMock(return_value=make_online_data()),
    ) as mocked:
        yield mocked


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """A configured Trannergy entry with every sensor enabled."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Trannergy",
        unique_id=str(SERIAL),
        data={
            CONF_NAME: "Trannergy",
            CONF_INVERTER_SERIAL: SERIAL,
            CONF_INVERTER_HOST: "1.2.3.4",
            CONF_INVERTER_PORT: 8899,
            CONF_SCAN_INTERVAL: 30,
            CONF_SENSORS: list(SENSOR_KEYS),
        },
    )
