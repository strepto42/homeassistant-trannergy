"""Options flow: toggling sensors and scan interval."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.trannergy.const import (
    CONF_SCAN_INTERVAL,
    CONF_SENSORS,
    SENSOR_KEYS,
)


async def test_options_flow_updates_sensors_and_interval(
    hass: HomeAssistant, mock_api, mock_config_entry: MockConfigEntry
) -> None:
    mock_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    # Disable everything except two sensors, and change the scan interval.
    user_input = {key: False for key in SENSOR_KEYS}
    user_input["energytotal"] = True
    user_input["energytoday"] = True
    user_input[CONF_SCAN_INTERVAL] = 60

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert set(result["data"][CONF_SENSORS]) == {"energytotal", "energytoday"}
    assert result["data"][CONF_SCAN_INTERVAL] == 60
