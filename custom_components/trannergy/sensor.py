"""Sensor platform for Trannergy PV Inverter integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_INVERTER_SERIAL,
    CONF_SENSORS,
    DEFAULT_SENSORS,
    DOMAIN,
)
from .coordinator import TrannergyDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Sensor definitions: key -> [name, unit, icon, device_class, state_class, precision]
SENSOR_TYPES: dict[str, list] = {
    "status": ["Status", None, "mdi:weather-sunny", None, None, None],
    "actualpower": [
        "Actual Power",
        "W",
        "mdi:solar-power",
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
        None,
    ],
    "energytoday": [
        "Energy Today",
        "kWh",
        "mdi:chart-bell-curve-cumulative",
        SensorDeviceClass.ENERGY,
        None,
        2,
    ],
    "energytotal": [
        "Energy Total",
        "kWh",
        "mdi:meter-electric-outline",
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL_INCREASING,
        1,
    ],
    "hourstotal": [
        "Hours Total",
        "h",
        "mdi:timer-outline",
        SensorDeviceClass.DURATION,
        SensorStateClass.TOTAL_INCREASING,
        None,
    ],
    "invertersn": [
        "Inverter Serial Number",
        None,
        "mdi:information-outline",
        None,
        None,
        None,
    ],
    "temperature": [
        "Temperature",
        "°C",
        "mdi:thermometer",
        SensorDeviceClass.TEMPERATURE,
        SensorStateClass.MEASUREMENT,
        None,
    ],
    "dcinputvoltage1": [
        "DC Input Voltage 1",
        "V",
        "mdi:flash-outline",
        SensorDeviceClass.VOLTAGE,
        SensorStateClass.MEASUREMENT,
        None,
    ],
    "dcinputcurrent1": [
        "DC Input Current 1",
        "A",
        "mdi:current-dc",
        SensorDeviceClass.CURRENT,
        SensorStateClass.MEASUREMENT,
        None,
    ],
    "dcinputvoltage2": [
        "DC Input Voltage 2",
        "V",
        "mdi:flash-outline",
        SensorDeviceClass.VOLTAGE,
        SensorStateClass.MEASUREMENT,
        None,
    ],
    "dcinputcurrent2": [
        "DC Input Current 2",
        "A",
        "mdi:current-dc",
        SensorDeviceClass.CURRENT,
        SensorStateClass.MEASUREMENT,
        None,
    ],
    "dcinputvoltage3": [
        "DC Input Voltage 3",
        "V",
        "mdi:flash-outline",
        SensorDeviceClass.VOLTAGE,
        SensorStateClass.MEASUREMENT,
        None,
    ],
    "dcinputcurrent3": [
        "DC Input Current 3",
        "A",
        "mdi:current-dc",
        SensorDeviceClass.CURRENT,
        SensorStateClass.MEASUREMENT,
        None,
    ],
    "acoutputvoltage1": [
        "AC Output Voltage 1",
        "V",
        "mdi:flash-outline",
        SensorDeviceClass.VOLTAGE,
        SensorStateClass.MEASUREMENT,
        None,
    ],
    "acoutputcurrent1": [
        "AC Output Current 1",
        "A",
        "mdi:current-ac",
        SensorDeviceClass.CURRENT,
        SensorStateClass.MEASUREMENT,
        None,
    ],
    "acoutputfrequency1": [
        "AC Output Frequency 1",
        "Hz",
        "mdi:sine-wave",
        SensorDeviceClass.FREQUENCY,
        SensorStateClass.MEASUREMENT,
        None,
    ],
    "acoutputpower1": [
        "AC Output Power 1",
        "W",
        "mdi:solar-power",
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
        None,
    ],
    "acoutputvoltage2": [
        "AC Output Voltage 2",
        "V",
        "mdi:flash-outline",
        SensorDeviceClass.VOLTAGE,
        SensorStateClass.MEASUREMENT,
        None,
    ],
    "acoutputcurrent2": [
        "AC Output Current 2",
        "A",
        "mdi:current-ac",
        SensorDeviceClass.CURRENT,
        SensorStateClass.MEASUREMENT,
        None,
    ],
    "acoutputfrequency2": [
        "AC Output Frequency 2",
        "Hz",
        "mdi:sine-wave",
        SensorDeviceClass.FREQUENCY,
        SensorStateClass.MEASUREMENT,
        None,
    ],
    "acoutputpower2": [
        "AC Output Power 2",
        "W",
        "mdi:solar-power",
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
        None,
    ],
    "acoutputvoltage3": [
        "AC Output Voltage 3",
        "V",
        "mdi:flash-outline",
        SensorDeviceClass.VOLTAGE,
        SensorStateClass.MEASUREMENT,
        None,
    ],
    "acoutputcurrent3": [
        "AC Output Current 3",
        "A",
        "mdi:current-ac",
        SensorDeviceClass.CURRENT,
        SensorStateClass.MEASUREMENT,
        None,
    ],
    "acoutputfrequency3": [
        "AC Output Frequency 3",
        "Hz",
        "mdi:sine-wave",
        SensorDeviceClass.FREQUENCY,
        SensorStateClass.MEASUREMENT,
        None,
    ],
    "acoutputpower3": [
        "AC Output Power 3",
        "W",
        "mdi:solar-power",
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
        None,
    ],
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Trannergy sensors based on a config entry.

    Args:
        hass: Home Assistant instance.
        entry: Config entry.
        async_add_entities: Callback to add entities.
    """
    coordinator: TrannergyDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Get configured sensors from options or data
    configured_sensors = entry.options.get(
        CONF_SENSORS, entry.data.get(CONF_SENSORS, DEFAULT_SENSORS)
    )

    name = entry.data.get(CONF_NAME, "Trannergy")
    serial = entry.data[CONF_INVERTER_SERIAL]

    entities: list[TrannergySensor] = []

    for sensor_key in configured_sensors:
        if sensor_key in SENSOR_TYPES:
            sensor_info = SENSOR_TYPES[sensor_key]
            entities.append(
                TrannergySensor(
                    coordinator=coordinator,
                    entry=entry,
                    sensor_key=sensor_key,
                    sensor_name=sensor_info[0],
                    sensor_unit=sensor_info[1],
                    sensor_icon=sensor_info[2],
                    sensor_device_class=sensor_info[3],
                    sensor_state_class=sensor_info[4],
                    sensor_precision=sensor_info[5],
                    inverter_name=name,
                    inverter_serial=serial,
                )
            )

    async_add_entities(entities)


class TrannergySensor(CoordinatorEntity[TrannergyDataUpdateCoordinator], SensorEntity):
    """Representation of a Trannergy sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TrannergyDataUpdateCoordinator,
        entry: ConfigEntry,
        sensor_key: str,
        sensor_name: str,
        sensor_unit: str | None,
        sensor_icon: str,
        sensor_device_class: SensorDeviceClass | None,
        sensor_state_class: SensorStateClass | None,
        sensor_precision: int | None,
        inverter_name: str,
        inverter_serial: int,
    ) -> None:
        """Initialize the sensor.

        Args:
            coordinator: Data update coordinator.
            entry: Config entry.
            sensor_key: Key of the sensor in the data dictionary.
            sensor_name: Human-readable name of the sensor.
            sensor_unit: Unit of measurement.
            sensor_icon: Icon for the sensor.
            sensor_device_class: Device class of the sensor.
            sensor_state_class: State class of the sensor.
            sensor_precision: Number of decimal places for display.
            inverter_name: Name of the inverter.
            inverter_serial: Serial number of the inverter.
        """
        super().__init__(coordinator)

        self._sensor_key = sensor_key
        self._inverter_serial = inverter_serial

        # Entity attributes
        self._attr_name = sensor_name
        self._attr_unique_id = f"{inverter_serial}_{sensor_key}"
        self._attr_native_unit_of_measurement = sensor_unit
        self._attr_icon = sensor_icon
        self._attr_device_class = sensor_device_class
        self._attr_state_class = sensor_state_class
        if sensor_precision is not None:
            self._attr_suggested_display_precision = sensor_precision

        # Device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(inverter_serial))},
            name=inverter_name,
            manufacturer="Trannergy",
            model="PV Inverter",
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor.

        Returns:
            Current value of the sensor.
        """
        if self.coordinator.data is None:
            if self._sensor_key == "status":
                return "Offline"
            # Return None for other sensors when no data available
            return None

        value = self.coordinator.data.get(self._sensor_key)

        # Handle status sensor
        if self._sensor_key == "status":
            return str(value) if value else "Offline"

        # Handle inverter serial
        if self._sensor_key == "invertersn":
            return str(value) if value else ""

        # For TOTAL_INCREASING sensors, NEVER return 0 - return None instead
        # This prevents corrupting long-term statistics
        if self._attr_state_class == SensorStateClass.TOTAL_INCREASING:
            if value is None or value == 0.0:
                return None
            try:
                float_val = float(value)
                return float_val if float_val > 0 else None
            except (ValueError, TypeError):
                return None

        # For other sensors when offline, return None to make them unavailable
        if not self.coordinator.inverter_online:
            return None

        # For numeric values when online, ensure we return a float
        if value is None:
            return 0.0

        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    @property
    def available(self) -> bool:
        """Return True if entity is available.

        Returns:
            True if the coordinator has data and sensor should be available.
        """
        if not self.coordinator.last_update_success:
            return False

        # Status sensor is always available when coordinator is working
        if self._sensor_key == "status":
            return True

        # TOTAL_INCREASING sensors need a valid non-zero value to be available
        if self._attr_state_class == SensorStateClass.TOTAL_INCREASING:
            value = (
                self.coordinator.data.get(self._sensor_key)
                if self.coordinator.data
                else None
            )
            if value is None or value == 0.0:
                return False
            try:
                return float(value) > 0
            except (ValueError, TypeError):
                return False

        # Other sensors are only available when the inverter is online
        return self.coordinator.inverter_online
