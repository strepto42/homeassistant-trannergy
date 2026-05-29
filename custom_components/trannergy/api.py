"""Async API client for Trannergy PV Inverter."""

from __future__ import annotations

import asyncio
import logging
import struct
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Timeout for TCP connections (seconds)
CONNECTION_TIMEOUT = 10
READ_TIMEOUT = 10


class TrannergyInverterError(Exception):
    """Base exception for Trannergy Inverter errors."""


class TrannergyInverterConnectionError(TrannergyInverterError):
    """Connection error to the inverter."""


class TrannergyInverterTimeoutError(TrannergyInverterError):
    """Timeout error when connecting to the inverter."""


class TrannergyInverterApi:
    """Async API client for Trannergy PV Inverter."""

    def __init__(self, host: str, port: int, serial_number: int) -> None:
        """Initialize the API client.

        Args:
            host: IP address of the inverter.
            port: TCP port of the inverter.
            serial_number: Serial number of the wifi/lan module.
        """
        self._host = host
        self._port = port
        self._serial_number = serial_number
        self._raw_msg: bytes | None = None

    @staticmethod
    def _generate_request(serial_number: int) -> bytes:
        """Create request string for inverter.

        The request string is built from several parts:
        - Fixed 4 char string
        - Reversed hex notation of the serial number (twice)
        - Fixed string of two chars
        - Checksum of the double serial number with an offset
        - Fixed ending char

        Args:
            serial_number: Serial number of the inverter

        Returns:
            Information request bytes for inverter
        """
        double_hex = hex(serial_number)[2:] * 2
        serial_bytes = bytearray.fromhex(double_hex)
        serial_bytes.reverse()

        cs_count = 115 + sum(serial_bytes)
        checksum = bytearray.fromhex(hex(cs_count)[-2:])

        request_data = bytearray([0x68, 0x02, 0x40, 0x30])
        request_data.extend(serial_bytes)
        request_data.extend([0x01, 0x00])
        request_data.extend(checksum)
        request_data.append(0x16)

        _LOGGER.debug("Request: %s", request_data.hex(" "))
        return bytes(request_data)

    async def async_get_data(self) -> dict[str, Any]:
        """Fetch data from the inverter.

        Returns:
            Dictionary with all sensor data.

        Raises:
            TrannergyInverterConnectionError: If connection fails.
            TrannergyInverterTimeoutError: If connection times out.
        """
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=CONNECTION_TIMEOUT,
            )
        except TimeoutError as err:
            _LOGGER.debug(
                "Timeout connecting to inverter at %s:%s", self._host, self._port
            )
            raise TrannergyInverterTimeoutError(
                f"Timeout connecting to inverter at {self._host}:{self._port}"
            ) from err
        except OSError as err:
            _LOGGER.debug(
                "Could not connect to inverter at %s:%s: %s",
                self._host,
                self._port,
                err,
            )
            raise TrannergyInverterConnectionError(
                f"Could not connect to inverter at {self._host}:{self._port}"
            ) from err

        try:
            request = self._generate_request(self._serial_number)
            writer.write(request)
            await writer.drain()

            self._raw_msg = await asyncio.wait_for(
                reader.read(1024), timeout=READ_TIMEOUT
            )
            _LOGGER.debug(
                "Response: %s", self._raw_msg.hex(" ") if self._raw_msg else "None"
            )
        except TimeoutError as err:
            _LOGGER.debug("Timeout reading data from inverter")
            raise TrannergyInverterTimeoutError(
                "Timeout reading data from inverter"
            ) from err
        except OSError as err:
            _LOGGER.debug("Error reading data from inverter: %s", err)
            raise TrannergyInverterConnectionError(
                f"Error reading data from inverter: {err}"
            ) from err
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

        return self._parse_data()

    def _parse_data(self) -> dict[str, Any]:
        """Parse the raw message into sensor data.

        Returns:
            Dictionary with all sensor data.
        """
        data: dict[str, Any] = {}

        # Check if we have valid data
        if not self._raw_msg or len(self._raw_msg) < 80:
            _LOGGER.debug("Invalid or empty response from inverter")
            return self._get_offline_data()

        # Check if inverter is online by checking temperature
        temperature = self._get_short(31)
        if temperature is None or temperature > 150:
            _LOGGER.debug(
                "Inverter appears to be offline (temperature: %s)", temperature
            )
            return self._get_offline_data()

        # Status
        data["status"] = "Online"

        # Power and energy
        data["actualpower"] = self._safe_float(self._get_short(59, 1), 0.0)
        data["energytoday"] = self._safe_float(self._get_short(69, 100), 0.0)
        data["energytotal"] = self._safe_float(self._get_long(71), 0.0)
        data["hourstotal"] = self._safe_float(self._get_long(75, 1), 0.0)

        # Inverter serial
        data["invertersn"] = self._get_string(15, 31) or ""

        # Temperature
        data["temperature"] = self._safe_float(temperature, 0.0)

        # DC Input (3 channels)
        for i in range(1, 4):
            data[f"dcinputvoltage{i}"] = self._safe_float(
                self._get_short(33 + (i - 1) * 2), 0.0
            )
            data[f"dcinputcurrent{i}"] = self._safe_float(
                self._get_short(39 + (i - 1) * 2), 0.0
            )

        # AC Output (3 channels)
        for i in range(1, 4):
            data[f"acoutputvoltage{i}"] = self._safe_float(
                self._get_short(51 + (i - 1) * 2), 0.0
            )
            data[f"acoutputcurrent{i}"] = self._safe_float(
                self._get_short(45 + (i - 1) * 2), 0.0
            )
            data[f"acoutputfrequency{i}"] = self._safe_float(
                self._get_short(57 + (i - 1) * 4, 100), 0.0
            )
            data[f"acoutputpower{i}"] = self._safe_float(
                self._get_short(59 + (i - 1) * 4, 1), 0.0
            )

        return data

    def _get_offline_data(self) -> dict[str, Any]:
        """Return data structure for offline inverter.

        Returns:
            Dictionary with all sensor data set to offline/zero values.
        """
        data: dict[str, Any] = {
            "status": "Offline",
            "actualpower": 0.0,
            "energytoday": 0.0,
            "energytotal": 0.0,
            "hourstotal": 0.0,
            "invertersn": "",
            "temperature": 0.0,
        }

        for i in range(1, 4):
            data[f"dcinputvoltage{i}"] = 0.0
            data[f"dcinputcurrent{i}"] = 0.0
            data[f"acoutputvoltage{i}"] = 0.0
            data[f"acoutputcurrent{i}"] = 0.0
            data[f"acoutputfrequency{i}"] = 0.0
            data[f"acoutputpower{i}"] = 0.0

        return data

    @staticmethod
    def _safe_float(value: float | None, default: float) -> float:
        """Safely convert value to float.

        Args:
            value: Value to convert.
            default: Default value if conversion fails.

        Returns:
            Float value or default.
        """
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def _get_string(self, begin: int, end: int) -> str | None:
        """Extract string from message.

        Args:
            begin: Starting byte index of string.
            end: End byte index of string.

        Returns:
            String in the message from start to end.
        """
        try:
            if self._raw_msg:
                return self._raw_msg[begin:end].decode().strip("\x00")
        except (UnicodeDecodeError, IndexError):
            pass
        return None

    def _get_short(self, begin: int, divider: int = 10) -> float | None:
        """Extract short from message.

        The shorts in the message could be a decimal number, stored multiplied.
        Dividing retrieves the original decimal number.

        Args:
            begin: Index of short in message.
            divider: Divider to change short to float.

        Returns:
            Value stored at location begin.
        """
        try:
            if self._raw_msg:
                num = struct.unpack("!H", self._raw_msg[begin : begin + 2])[0]
                if num == 65535:
                    return None
                return float(num) / divider
        except (struct.error, IndexError):
            pass
        return None

    def _get_long(self, begin: int, divider: int = 10) -> float | None:
        """Extract long from message.

        The longs in the message could be a decimal number.
        Dividing retrieves the original decimal number.

        Args:
            begin: Index of long in message.
            divider: Divider to change long to float.

        Returns:
            Value stored at location begin.
        """
        try:
            if self._raw_msg:
                return (
                    float(struct.unpack("!I", self._raw_msg[begin : begin + 4])[0])
                    / divider
                )
        except (struct.error, IndexError):
            pass
        return None

    async def async_test_connection(self) -> bool:
        """Test connection to the inverter.

        Returns:
            True if connection is successful.

        Raises:
            TrannergyInverterConnectionError: If connection fails.
            TrannergyInverterTimeoutError: If connection times out.
        """
        await self.async_get_data()
        return True
