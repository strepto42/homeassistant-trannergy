"""Sensor platform behaviour, focused on the offline / TOTAL_INCREASING rules.

The central invariant (see CLAUDE.md): the cumulative TOTAL_INCREASING sensors
(energytotal, hourstotal) must NEVER report 0 — a 0 corrupts HA long-term
statistics — and must be preserved across offline periods.
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.trannergy.api import TrannergyInverterTimeoutError
from custom_components.trannergy.const import DOMAIN

from .conftest import SERIAL, make_online_data


def _state(hass: HomeAssistant, key: str) -> str | None:
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{SERIAL}_{key}"
    )
    assert entity_id is not None, f"entity for {key} not registered"
    state = hass.states.get(entity_id)
    return state.state if state else None


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_online_values_exposed(
    hass: HomeAssistant, mock_api, mock_config_entry: MockConfigEntry
) -> None:
    await _setup(hass, mock_config_entry)

    assert _state(hass, "status") == "Online"
    assert _state(hass, "actualpower") == "1500.0"
    assert _state(hass, "energytotal") == "5678.9"
    assert _state(hass, "acoutputvoltage1") == "240.0"


async def test_total_increasing_never_reports_zero(
    hass: HomeAssistant, mock_api, mock_config_entry: MockConfigEntry
) -> None:
    await _setup(hass, mock_config_entry)

    # Inverter reports 0 for the cumulative total while still "online".
    mock_api.return_value = {**make_online_data(), "energytotal": 0.0}
    coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    # Must go unavailable rather than emit 0 into long-term statistics.
    assert _state(hass, "energytotal") == "unavailable"


async def test_offline_preserves_total_increasing(
    hass: HomeAssistant, mock_api, mock_config_entry: MockConfigEntry
) -> None:
    await _setup(hass, mock_config_entry)
    # First good poll stored energytotal=5678.9.

    # Inverter goes offline (timeout, e.g. at night).
    mock_api.side_effect = TrannergyInverterTimeoutError("night")
    coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert coordinator.last_update_success is True
    assert _state(hass, "status") == "Offline"
    # Cumulative total is preserved at its last known value.
    assert _state(hass, "energytotal") == "5678.9"
    # A plain measurement sensor goes unavailable while offline.
    assert _state(hass, "temperature") == "unavailable"
