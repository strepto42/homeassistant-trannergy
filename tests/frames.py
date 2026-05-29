"""Helpers to build synthetic Trannergy inverter response frames.

The inverter speaks a fixed-byte-offset binary protocol (see
``custom_components/trannergy/api.py`` ``_parse_data``). We have no captured
device dump to ship, so tests construct frames here from engineering values,
packing each field big-endian at the exact offset/scale the parser reads it
back from. This lets the client tests assert the parser is the precise inverse
of this builder — locking the byte layout against accidental drift.
"""

from __future__ import annotations

import struct

# Default field values used to build a realistic "online" frame. Engineering
# units (V, A, Hz, W, kWh, h, °C) — the builder applies the on-wire scaling.
DEFAULTS: dict[str, object] = {
    "temperature": 25.0,
    "invertersn": "NLDN1234567890AB",  # 16 chars exactly fills bytes [15:31]
    "dc_voltage": (320.0, 0.0, 0.0),
    "dc_current": (5.0, 0.0, 0.0),
    "ac_voltage": (240.0, 0.0, 0.0),
    "ac_current": (6.5, 0.0, 0.0),
    "ac_frequency": (50.0, 0.0, 0.0),
    "ac_power": (1500, 0, 0),
    "energytoday": 12.34,  # kWh
    "energytotal": 5678.9,  # kWh
    "hourstotal": 4321,  # h
}


def build_response(size: int = 100, **overrides: object) -> bytes:
    """Build a valid binary response frame.

    Keyword overrides match the keys in :data:`DEFAULTS`. ``size`` must be at
    least 80 bytes or the parser treats the frame as offline.
    """
    v = {**DEFAULTS, **overrides}
    buf = bytearray(size)

    def put_short(offset: int, value: float) -> None:
        struct.pack_into("!H", buf, offset, round(value) & 0xFFFF)

    def put_long(offset: int, value: float) -> None:
        struct.pack_into("!I", buf, offset, round(value) & 0xFFFFFFFF)

    # Inverter serial string, bytes [15:31].
    sn = str(v["invertersn"]).encode("ascii")[:16].ljust(16, b"\x00")
    buf[15:31] = sn

    # Temperature, short at [31], scale /10.
    put_short(31, float(v["temperature"]) * 10)

    dc_voltage = v["dc_voltage"]
    dc_current = v["dc_current"]
    ac_voltage = v["ac_voltage"]
    ac_current = v["ac_current"]
    ac_frequency = v["ac_frequency"]
    ac_power = v["ac_power"]

    for i in range(3):
        put_short(33 + i * 2, dc_voltage[i] * 10)  # dc voltage /10
        put_short(39 + i * 2, dc_current[i] * 10)  # dc current /10
        put_short(45 + i * 2, ac_current[i] * 10)  # ac current /10
        put_short(51 + i * 2, ac_voltage[i] * 10)  # ac voltage /10
        put_short(57 + i * 4, ac_frequency[i] * 100)  # ac frequency /100
        put_short(59 + i * 4, ac_power[i])  # ac power /1

    # Energy today, short at [69], scale /100.
    put_short(69, float(v["energytoday"]) * 100)
    # Energy total, long at [71], scale /10.
    put_long(71, float(v["energytotal"]) * 10)
    # Hours total, long at [75], scale /1.
    put_long(75, float(v["hourstotal"]))

    return bytes(buf)
