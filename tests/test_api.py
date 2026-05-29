"""Client-layer tests for the Trannergy inverter API.

Pure stdlib; no Home Assistant. Runs on any OS.
"""

from __future__ import annotations

from types import ModuleType

import pytest

from tests.frames import build_response


# --------------------------------------------------------------------------- #
# Request generation
# --------------------------------------------------------------------------- #
def test_generate_request_structure(api_module: ModuleType) -> None:
    serial = 1612345603
    req = api_module.TrannergyInverterApi._generate_request(serial)

    # Fixed 4-byte header and 1-byte terminator.
    assert req[:4] == bytes([0x68, 0x02, 0x40, 0x30])
    assert req[-1] == 0x16

    # Reconstruct the serial bytes the same way the protocol does.
    double_hex = hex(serial)[2:] * 2
    serial_bytes = bytearray.fromhex(double_hex)
    serial_bytes.reverse()

    # Layout: header(4) + serial + [0x01, 0x00] + checksum(1) + terminator(1).
    assert req[4 : 4 + len(serial_bytes)] == bytes(serial_bytes)
    marker_at = 4 + len(serial_bytes)
    assert req[marker_at : marker_at + 2] == bytes([0x01, 0x00])

    checksum = req[marker_at + 2]
    assert checksum == (115 + sum(serial_bytes)) & 0xFF
    assert len(req) == 4 + len(serial_bytes) + 2 + 1 + 1


# --------------------------------------------------------------------------- #
# Parsing — the byte layout is the inverse of tests/frames.build_response
# --------------------------------------------------------------------------- #
def _parse(api_module: ModuleType, raw: bytes) -> dict:
    api = api_module.TrannergyInverterApi("1.2.3.4", 8899, 1612345603)
    api._raw_msg = raw
    return api._parse_data()


def test_parse_online_frame(api_module: ModuleType) -> None:
    data = _parse(api_module, build_response())

    assert data["status"] == "Online"
    assert data["temperature"] == 25.0
    assert data["invertersn"] == "NLDN1234567890AB"
    assert data["actualpower"] == 1500.0
    assert data["energytoday"] == pytest.approx(12.34)
    assert data["energytotal"] == pytest.approx(5678.9)
    assert data["hourstotal"] == 4321.0

    assert data["dcinputvoltage1"] == 320.0
    assert data["dcinputcurrent1"] == 5.0
    assert data["acoutputvoltage1"] == 240.0
    assert data["acoutputcurrent1"] == 6.5
    assert data["acoutputfrequency1"] == pytest.approx(50.0)
    assert data["acoutputpower1"] == 1500.0
    # actualpower is read from the same offset as AC output power channel 1.
    assert data["actualpower"] == data["acoutputpower1"]


def test_parse_short_frame_is_offline(api_module: ModuleType) -> None:
    # Fewer than 80 bytes => offline.
    data = _parse(api_module, b"\x00" * 40)
    assert data["status"] == "Offline"
    assert data["actualpower"] == 0.0
    assert data["energytotal"] == 0.0


def test_parse_empty_frame_is_offline(api_module: ModuleType) -> None:
    data = _parse(api_module, b"")
    assert data["status"] == "Offline"


def test_parse_implausible_temperature_is_offline(api_module: ModuleType) -> None:
    # Temperature > 150 °C is the inverter's "offline/garbage" tell.
    data = _parse(api_module, build_response(temperature=200.0))
    assert data["status"] == "Offline"


def test_get_short_sentinel_is_none(api_module: ModuleType) -> None:
    api = api_module.TrannergyInverterApi("1.2.3.4", 8899, 1)
    api._raw_msg = b"\xff\xff\xff\xff"
    # 0xFFFF is the "no value" sentinel.
    assert api._get_short(0) is None


def test_safe_float_defaults(api_module: ModuleType) -> None:
    sf = api_module.TrannergyInverterApi._safe_float
    assert sf(None, 0.0) == 0.0
    assert sf(3, 0.0) == 3.0
    assert sf("nope", 1.5) == 1.5


# --------------------------------------------------------------------------- #
# Connection handling — fake the asyncio stream
# --------------------------------------------------------------------------- #
class _FakeWriter:
    def __init__(self) -> None:
        self.written = b""
        self.closed = False

    def write(self, data: bytes) -> None:
        self.written += data

    async def drain(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        pass


class _FakeReader:
    def __init__(self, data: bytes) -> None:
        self._data = data

    async def read(self, _n: int) -> bytes:
        return self._data


async def test_async_get_data_success(api_module, monkeypatch) -> None:
    frame = build_response()

    async def fake_open(host, port):
        return _FakeReader(frame), _FakeWriter()

    monkeypatch.setattr(api_module.asyncio, "open_connection", fake_open)

    api = api_module.TrannergyInverterApi("1.2.3.4", 8899, 1612345603)
    data = await api.async_get_data()
    assert data["status"] == "Online"
    assert data["actualpower"] == 1500.0


async def test_async_get_data_connection_error(api_module, monkeypatch) -> None:
    async def fake_open(host, port):
        raise OSError("refused")

    monkeypatch.setattr(api_module.asyncio, "open_connection", fake_open)

    api = api_module.TrannergyInverterApi("1.2.3.4", 8899, 1)
    with pytest.raises(api_module.TrannergyInverterConnectionError):
        await api.async_get_data()


async def test_async_get_data_timeout(api_module, monkeypatch) -> None:
    async def fake_open(host, port):
        raise TimeoutError

    monkeypatch.setattr(api_module.asyncio, "open_connection", fake_open)

    api = api_module.TrannergyInverterApi("1.2.3.4", 8899, 1)
    with pytest.raises(api_module.TrannergyInverterTimeoutError):
        await api.async_get_data()
