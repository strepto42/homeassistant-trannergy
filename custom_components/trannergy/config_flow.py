"""Config flow for Trannergy PV Inverter integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .api import (
    TrannergyInverterApi,
    TrannergyInverterConnectionError,
    TrannergyInverterTimeoutError,
)
from .const import (
    CONF_INVERTER_HOST,
    CONF_INVERTER_PORT,
    CONF_INVERTER_SERIAL,
    CONF_SCAN_INTERVAL,
    CONF_SENSORS,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SENSORS,
    DOMAIN,
    SENSOR_KEYS,
)

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Args:
        hass: Home Assistant instance.
        data: User input data.

    Returns:
        Dictionary with title for the config entry.

    Raises:
        CannotConnect: If we cannot connect to the inverter.
    """
    api = TrannergyInverterApi(
        host=data[CONF_INVERTER_HOST],
        port=data[CONF_INVERTER_PORT],
        serial_number=data[CONF_INVERTER_SERIAL],
    )

    try:
        await api.async_test_connection()
    except (TrannergyInverterConnectionError, TrannergyInverterTimeoutError) as err:
        _LOGGER.warning("Cannot connect to inverter: %s", err)
        # We don't raise an error here because the inverter might be offline at night
        # Instead, we allow the configuration to proceed

    return {"title": data.get(CONF_NAME, DEFAULT_NAME)}


class TrannergyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Trannergy PV Inverter."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate serial number is a valid integer
                serial = int(user_input[CONF_INVERTER_SERIAL])
                user_input[CONF_INVERTER_SERIAL] = serial
            except ValueError:
                errors[CONF_INVERTER_SERIAL] = "invalid_serial"

            if not errors:
                # Check if already configured
                await self.async_set_unique_id(str(user_input[CONF_INVERTER_SERIAL]))
                self._abort_if_unique_id_configured()

                try:
                    info = await validate_input(self.hass, user_input)
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception("Unexpected exception")
                    errors["base"] = "unknown"
                else:
                    # Add default sensors if not specified
                    if CONF_SENSORS not in user_input:
                        user_input[CONF_SENSORS] = DEFAULT_SENSORS

                    return self.async_create_entry(title=info["title"], data=user_input)

        # Show form
        data_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_INVERTER_SERIAL): str,
                vol.Required(CONF_INVERTER_HOST): str,
                vol.Optional(CONF_INVERTER_PORT, default=DEFAULT_PORT): vol.Coerce(int),
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): vol.Coerce(int),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> TrannergyOptionsFlowHandler:
        """Get the options flow for this handler."""
        return TrannergyOptionsFlowHandler()


class TrannergyOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Trannergy options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Convert selected sensors to list
            selected_sensors = [
                key for key, value in user_input.items() if key in SENSOR_KEYS and value
            ]

            # Get non-sensor options
            options = {
                CONF_SCAN_INTERVAL: user_input.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                ),
                CONF_SENSORS: selected_sensors,
            }

            return self.async_create_entry(title="", data=options)

        # Get current settings
        current_scan_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        current_sensors = self.config_entry.options.get(
            CONF_SENSORS,
            self.config_entry.data.get(CONF_SENSORS, DEFAULT_SENSORS),
        )

        # Build schema with sensor checkboxes
        schema_dict: dict[vol.Required | vol.Optional, Any] = {
            vol.Optional(CONF_SCAN_INTERVAL, default=current_scan_interval): vol.Coerce(
                int
            ),
        }

        # Add checkbox for each sensor type
        for sensor_key in SENSOR_KEYS:
            schema_dict[
                vol.Optional(sensor_key, default=sensor_key in current_sensors)
            ] = bool

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
