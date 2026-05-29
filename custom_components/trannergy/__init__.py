"""The Trannergy PV Inverter integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import HomeAssistant

from .api import TrannergyInverterApi
from .const import (
    CONF_INVERTER_HOST,
    CONF_INVERTER_PORT,
    CONF_INVERTER_SERIAL,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import TrannergyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Trannergy PV Inverter from a config entry.

    Args:
        hass: Home Assistant instance.
        entry: Config entry.

    Returns:
        True if setup was successful.
    """
    hass.data.setdefault(DOMAIN, {})

    # Get configuration
    host = entry.data[CONF_INVERTER_HOST]
    port = entry.data.get(CONF_INVERTER_PORT, DEFAULT_PORT)
    serial = entry.data[CONF_INVERTER_SERIAL]
    name = entry.data.get(CONF_NAME, "Trannergy")

    # Get scan interval from options or data
    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )

    # Create API client
    api = TrannergyInverterApi(host=host, port=port, serial_number=serial)

    # Create coordinator
    coordinator = TrannergyDataUpdateCoordinator(
        hass=hass,
        api=api,
        name=name,
        update_interval=scan_interval,
        entry_id=entry.entry_id,
    )

    # Load stored data (for preserved values after restart)
    await coordinator.async_load_stored_data()

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Set up the interval timer
    coordinator.async_setup_interval()

    # Store coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener for options
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update.

    Args:
        hass: Home Assistant instance.
        entry: Config entry.
    """
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    Args:
        hass: Home Assistant instance.
        entry: Config entry.

    Returns:
        True if unload was successful.
    """
    # Unload coordinator
    coordinator: TrannergyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.async_unload()

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
