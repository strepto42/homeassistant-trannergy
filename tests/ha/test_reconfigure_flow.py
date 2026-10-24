"""Reconfigure flow: change the inverter host/port of an existing entry in place."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigEntryState
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.trannergy.api import TrannergyInverterTimeoutError
from custom_components.trannergy.const import (
    CONF_INVERTER_HOST,
    CONF_INVERTER_PORT,
    CONF_INVERTER_SERIAL,
    CONF_SCAN_INTERVAL,
    CONF_SENSORS,
    DOMAIN,
)

from .conftest import SERIAL

NEW_HOST = "192.168.50.60"
NEW_PORT = 9999


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def _start(hass: HomeAssistant, entry: MockConfigEntry):
    return await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
    )


def _energytotal_state(hass: HomeAssistant) -> str | None:
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{SERIAL}_energytotal"
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    return state.state if state else None


async def test_form_defaults_to_current_values(
    hass: HomeAssistant, mock_api, mock_config_entry: MockConfigEntry
) -> None:
    await _setup(hass, mock_config_entry)

    result = await _start(hass, mock_config_entry)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    defaults = {str(key): key.default() for key in result["data_schema"].schema}
    # Only host and port are editable, pre-filled with the current values.
    assert defaults == {CONF_INVERTER_HOST: "1.2.3.4", CONF_INVERTER_PORT: 8899}


async def test_reconfigure_updates_entry_in_place(
    hass: HomeAssistant, mock_api, mock_config_entry: MockConfigEntry
) -> None:
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry, options={CONF_SCAN_INTERVAL: 45, CONF_SENSORS: ["status"]}
    )
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    entry_id = mock_config_entry.entry_id

    result = await _start(hass, mock_config_entry)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_INVERTER_HOST: NEW_HOST, CONF_INVERTER_PORT: NEW_PORT},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.entry_id == entry_id
    assert entry.data[CONF_INVERTER_HOST] == NEW_HOST
    assert entry.data[CONF_INVERTER_PORT] == NEW_PORT
    # Everything else is untouched.
    assert entry.data[CONF_INVERTER_SERIAL] == SERIAL
    assert entry.data[CONF_NAME] == "Trannergy"
    assert entry.unique_id == str(SERIAL)
    assert entry.options == {CONF_SCAN_INTERVAL: 45, CONF_SENSORS: ["status"]}


async def test_reconfigure_reloads_with_new_host(
    hass: HomeAssistant, mock_api, mock_config_entry: MockConfigEntry
) -> None:
    await _setup(hass, mock_config_entry)
    old_coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
    assert old_coordinator.api._host == "1.2.3.4"

    result = await _start(hass, mock_config_entry)
    await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_INVERTER_HOST: NEW_HOST, CONF_INVERTER_PORT: NEW_PORT},
    )
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    new_coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]
    assert new_coordinator is not old_coordinator
    assert new_coordinator.api._host == NEW_HOST
    assert new_coordinator.api._port == NEW_PORT


async def test_reconfigure_succeeds_while_inverter_offline(
    hass: HomeAssistant, mock_api, mock_config_entry: MockConfigEntry
) -> None:
    await _setup(hass, mock_config_entry)

    # Night time: the inverter does not answer.
    mock_api.side_effect = TrannergyInverterTimeoutError("offline")

    result = await _start(hass, mock_config_entry)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_INVERTER_HOST: NEW_HOST, CONF_INVERTER_PORT: NEW_PORT},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.data[CONF_INVERTER_HOST] == NEW_HOST
    assert mock_config_entry.state is ConfigEntryState.LOADED


async def test_reconfigure_keeps_preserved_totals(
    hass: HomeAssistant, mock_api, mock_config_entry: MockConfigEntry
) -> None:
    await _setup(hass, mock_config_entry)
    assert _energytotal_state(hass) == "5678.9"
    entry_id = mock_config_entry.entry_id

    # Reconfigure at night. The entry is reloaded with a fresh coordinator that
    # only knows the last total because it is persisted under the (unchanged)
    # entry_id Store key and loaded back from storage.
    mock_api.side_effect = TrannergyInverterTimeoutError("night")
    result = await _start(hass, mock_config_entry)
    await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_INVERTER_HOST: NEW_HOST, CONF_INVERTER_PORT: NEW_PORT},
    )
    await hass.async_block_till_done()

    assert mock_config_entry.entry_id == entry_id
    assert hass.data[DOMAIN][entry_id].api._host == NEW_HOST
    assert _energytotal_state(hass) == "5678.9"


async def test_reconfigure_unexpected_error_leaves_entry_unchanged(
    hass: HomeAssistant, mock_api, mock_config_entry: MockConfigEntry
) -> None:
    await _setup(hass, mock_config_entry)

    result = await _start(hass, mock_config_entry)
    with patch(
        "custom_components.trannergy.config_flow.validate_input",
        side_effect=Exception("boom"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_INVERTER_HOST: NEW_HOST, CONF_INVERTER_PORT: NEW_PORT},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    assert result["errors"] == {"base": "unknown"}
    assert mock_config_entry.data[CONF_INVERTER_HOST] == "1.2.3.4"
    assert mock_config_entry.data[CONF_INVERTER_PORT] == 8899
