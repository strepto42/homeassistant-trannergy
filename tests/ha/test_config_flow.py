"""Config flow for the Trannergy integration."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
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

_VALID_INPUT = {
    CONF_NAME: "My Inverter",
    CONF_INVERTER_SERIAL: str(SERIAL),
    CONF_INVERTER_HOST: "1.2.3.4",
    CONF_INVERTER_PORT: 8899,
    CONF_SCAN_INTERVAL: 30,
}


async def test_user_flow_creates_entry(hass: HomeAssistant, mock_api) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], dict(_VALID_INPUT)
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "My Inverter"
    # Serial is coerced to int and default sensors are populated.
    assert result["data"][CONF_INVERTER_SERIAL] == SERIAL
    assert result["data"][CONF_SENSORS]


async def test_invalid_serial_shows_error(hass: HomeAssistant, mock_api) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**_VALID_INPUT, CONF_INVERTER_SERIAL: "not-a-number"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"][CONF_INVERTER_SERIAL] == "invalid_serial"


async def test_duplicate_serial_aborts(
    hass: HomeAssistant, mock_api, mock_config_entry: MockConfigEntry
) -> None:
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], dict(_VALID_INPUT)
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_offline_inverter_still_creates_entry(
    hass: HomeAssistant, mock_api
) -> None:
    # The inverter is offline (e.g. at night); setup must still proceed.
    mock_api.side_effect = TrannergyInverterTimeoutError("offline")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], dict(_VALID_INPUT)
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
