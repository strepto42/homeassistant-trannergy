"""DataUpdateCoordinator for Trannergy PV Inverter."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, ClassVar

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    TrannergyInverterApi,
    TrannergyInverterConnectionError,
    TrannergyInverterTimeoutError,
)

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY = "trannergy_last_values"


class TrannergyDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Trannergy data from the inverter."""

    # Sensors that should preserve their last known value when offline
    PRESERVE_WHEN_OFFLINE: ClassVar[set[str]] = {"energytotal", "hourstotal"}

    def __init__(
        self,
        hass: HomeAssistant,
        api: TrannergyInverterApi,
        name: str,
        update_interval: int,
        entry_id: str,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance.
            api: API client for the inverter.
            name: Name of the inverter.
            update_interval: Update interval in seconds.
            entry_id: Config entry ID for storage.
        """
        self.api = api
        self._update_interval_seconds = update_interval
        self._unsub_interval = None
        self._last_valid_data: dict[str, Any] = {}
        self._inverter_online = False
        self._entry_id = entry_id
        self._store: Store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry_id}")

        super().__init__(
            hass,
            _LOGGER,
            name=name,
            update_interval=timedelta(seconds=update_interval),
        )

    async def async_load_stored_data(self) -> None:
        """Load last valid data from storage."""
        stored = await self._store.async_load()
        if stored and isinstance(stored, dict):
            self._last_valid_data = stored
            _LOGGER.debug("Loaded stored values: %s", self._last_valid_data)

    async def _async_save_stored_data(self) -> None:
        """Save last valid data to storage."""
        await self._store.async_save(self._last_valid_data)
        _LOGGER.debug("Saved values to storage: %s", self._last_valid_data)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the inverter.

        Returns:
            Dictionary with all sensor data.

        Raises:
            UpdateFailed: If fetching data fails.
        """
        try:
            data = await self.api.async_get_data()
            _LOGGER.debug("Successfully fetched data from inverter: %s", data)

            # Check if inverter is online
            if data.get("status") == "Online":
                self._inverter_online = True
                # Store valid data for sensors that should preserve values when offline
                data_changed = False
                for key in self.PRESERVE_WHEN_OFFLINE:
                    if key in data and data[key] is not None and data[key] != 0.0:
                        if self._last_valid_data.get(key) != data[key]:
                            self._last_valid_data[key] = data[key]
                            data_changed = True
                # Persist to storage if values changed
                if data_changed:
                    await self._async_save_stored_data()
            else:
                self._inverter_online = False
                # When offline, preserve last known values for TOTAL_INCREASING sensors
                for key in self.PRESERVE_WHEN_OFFLINE:
                    if key in self._last_valid_data:
                        data[key] = self._last_valid_data[key]

            return data
        except TrannergyInverterTimeoutError as err:
            # Inverter is likely offline (e.g., at night), return offline data
            _LOGGER.debug("Inverter timeout (likely offline): %s", err)
            self._inverter_online = False
            return self._get_offline_data_with_preserved_values()
        except TrannergyInverterConnectionError as err:
            # Connection error, return offline data
            _LOGGER.debug("Inverter connection error: %s", err)
            self._inverter_online = False
            return self._get_offline_data_with_preserved_values()
        except Exception as err:
            _LOGGER.exception("Unexpected error fetching data from inverter")
            raise UpdateFailed(f"Error fetching data from inverter: {err}") from err

    def _get_offline_data_with_preserved_values(self) -> dict[str, Any]:
        """Get offline data while preserving TOTAL_INCREASING sensor values.

        Returns:
            Dictionary with offline status and preserved values.
        """
        data = self.api._get_offline_data()

        # Preserve last known values for TOTAL_INCREASING sensors
        for key in self.PRESERVE_WHEN_OFFLINE:
            if key in self._last_valid_data:
                data[key] = self._last_valid_data[key]

        return data

    @property
    def inverter_online(self) -> bool:
        """Return whether the inverter is currently online."""
        return self._inverter_online

    @callback
    def async_setup_interval(self) -> None:
        """Set up the update interval using async_track_time_interval."""
        if self._unsub_interval is not None:
            self._unsub_interval()

        async def _async_refresh(_: Any) -> None:
            """Refresh data from the inverter."""
            await self.async_refresh()

        self._unsub_interval = async_track_time_interval(
            self.hass,
            _async_refresh,
            timedelta(seconds=self._update_interval_seconds),
        )

    @callback
    def async_unload(self) -> None:
        """Unload the coordinator."""
        if self._unsub_interval is not None:
            self._unsub_interval()
            self._unsub_interval = None
