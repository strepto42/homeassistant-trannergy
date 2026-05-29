# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Home Assistant **custom integration** (distributed via HACS) that polls a Trannergy/Omnik PV inverter over its local TCP socket (default port 8899) and exposes the readings as Home Assistant sensors. All code lives in `custom_components/trannergy/`. It is a continuation of the archived `hultenvp/home_assistant_omnik_solar` project.

The integration runs inside Home Assistant (min version `2024.1.0`, per `hacs.json`) and at runtime depends only on `homeassistant` core APIs — `manifest.json` `requirements` is empty and the inverter client (`api.py`) uses only the standard library (`asyncio`, `struct`). The repo *does* carry dev tooling (ruff, mypy, pytest) and CI; see **Development** and **Testing** below. To smoke-test against real hardware, copy `custom_components/trannergy/` into a Home Assistant `config/custom_components/` directory and load the integration; enable debug logging with `custom_components.trannergy: debug` under `logger:` in `configuration.yaml`.

## Architecture & data flow

Setup chain (`__init__.py` `async_setup_entry`): read config entry → build `TrannergyInverterApi` → build `TrannergyDataUpdateCoordinator` → `async_load_stored_data()` → `async_config_entry_first_refresh()` → `async_setup_interval()` → forward to the `sensor` platform. Options changes call `async_reload` via the update listener.

- **`api.py` — protocol layer.** `_generate_request()` builds the binary request from the **WiFi/LAN module serial number** (4 fixed bytes + reversed-hex serial twice + fixed bytes + a checksum = `115 + sum(serial_bytes)` + `0x16` terminator). `async_get_data()` opens an async TCP connection, writes the request, reads the response, and `_parse_data()` decodes it by **fixed byte offsets** via `struct.unpack` (`_get_short`/`_get_long`/`_get_string`). These offsets are inverter-firmware-specific and fragile — change them only against a real device capture. A short of `65535` means "no value" (→ `None`). Raises `TrannergyInverterTimeoutError` / `TrannergyInverterConnectionError`, both subclasses of `TrannergyInverterError`.

- **Offline detection.** The inverter powers down at night, so "offline" is a normal, expected state, not an error. It is detected by a response shorter than 80 bytes or a temperature reading > 150°C, in which case `_get_offline_data()` returns an all-zero dict with `status: "Offline"`. Connection/timeout errors during polling are caught in the coordinator and also treated as offline (not surfaced as `UpdateFailed`). The config flow likewise does **not** block setup on a failed connection.

- **`coordinator.py` — state management.** `DataUpdateCoordinator` subclass. Its main job beyond polling is preserving the cumulative `TOTAL_INCREASING` sensors (`PRESERVE_WHEN_OFFLINE = {"energytotal", "hourstotal"}`) across offline periods. Last-known non-zero values are kept in `_last_valid_data` and persisted to disk via Home Assistant `Store` (`trannergy_last_values_<entry_id>`) so they survive restarts. When offline, these keys are backfilled from the preserved values instead of reporting 0.

- **`sensor.py` — entities.** `SENSOR_TYPES` is the source of truth: `key -> [name, unit, icon, device_class, state_class, precision]`. One `TrannergySensor` (a `CoordinatorEntity`) per enabled key; `unique_id` is `{module_serial}_{key}` and all entities share one `DeviceInfo` keyed on the module serial.

- **`config_flow.py` — UI config + options.** Config flow `unique_id` is the module serial (`_abort_if_unique_id_configured` prevents duplicates). The options flow renders a checkbox per `SENSOR_KEYS` entry plus scan interval.

- **`const.py`** — `DOMAIN`, `CONF_*` keys, defaults, `SENSOR_KEYS` (all available) and `DEFAULT_SENSORS` (enabled by default).

## Critical invariant: TOTAL_INCREASING sensors must never report 0

`energytotal` and `hourstotal` feed Home Assistant long-term statistics; emitting a 0 (e.g. when the inverter is offline) permanently corrupts those statistics. This is enforced in **three** places that must stay consistent — most recent commits are bug fixes in exactly this area:
1. `coordinator.PRESERVE_WHEN_OFFLINE` — preserve & persist last non-zero value, backfill when offline.
2. `sensor.native_value` — for `TOTAL_INCREASING`, return `None` (never 0) when the value is missing or zero.
3. `sensor.available` — mark `TOTAL_INCREASING` sensors unavailable when there is no valid non-zero value.

When adding any cumulative/monotonic sensor, give it `SensorStateClass.TOTAL_INCREASING` and add its key to `PRESERVE_WHEN_OFFLINE`. These three behaviours are locked by `tests/ha/test_platforms.py` (online value exposed, never-zero, offline-preserved) — extend those tests rather than relaxing them.

## Conventions when adding a sensor

A sensor key must be added consistently across: `const.SENSOR_KEYS` (and `DEFAULT_SENSORS` if on-by-default) → `sensor.SENSOR_TYPES` → a parse entry producing that key in `api._parse_data()` **and** `api._get_offline_data()` → an entry under `options.step.init.data` in both `strings.json` and `translations/en.json`. The first/last links of that chain are enforced by `tests/test_sensor_consistency.py`, which fails if `SENSOR_KEYS`, `SENSOR_TYPES`, and the translation files drift apart.

## Development

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows; use source .venv/bin/activate elsewhere
pip install -e ".[test,dev]"    # client + guard tests, ruff, mypy (runs on Windows)
pip install -e ".[test-ha]"     # HA integration tests (CI / WSL / Linux / macOS)
```

- Lint/format (the CI gate): `ruff check . && ruff format --check .`
- Types (local only, not gated): `mypy custom_components`. Without `homeassistant`
  installed, mypy reports one false positive on the `ConfigFlow(..., domain=DOMAIN)`
  line; it disappears under the `test-ha` env. Do **not** add a `# type: ignore`
  there — `warn_unused_ignores` would then fail where HA *is* installed.
- `.pre-commit-config.yaml` wires ruff + ruff-format + basic hygiene hooks.

## Testing

Two layers (see `pyproject.toml` extras), mirroring the api/integration split:

- **Client + guard tests** — everything under `tests/` except `tests/ha/`. Pure
  stdlib, no Home Assistant, runs anywhere incl. native Windows. `conftest.py`
  loads `api.py` standalone from its file path (bypassing the HA-importing package
  `__init__.py`). `tests/frames.py` builds synthetic binary inverter frames — there
  is no captured device dump, so the parser is tested as the exact inverse of that
  builder, which locks the fragile byte offsets. The guard tests (`test_manifest`,
  `test_hacs`, `test_relative_imports`, `test_sensor_consistency`) protect repo-wide
  invariants. Run: `pytest tests --ignore=tests/ha -v`.
- **HA integration tests** — `tests/ha/`, using `pytest-homeassistant-custom-component`.
  That harness pulls Unix-only deps (uvloop), so these run in **CI/WSL, not native
  Windows**. The inverter API is mocked (`tests/ha/conftest.py` patches
  `TrannergyInverterApi.async_get_data`); no TCP happens. Run: `pytest tests/ha -v`.

CI (`.github/workflows/ci.yml`) runs five jobs on push/PR to `main`: `lint` (ruff),
`test-client`, `test-ha`, `hacs` (HACS validation), and `hassfest`.

## Workflow conventions

- **TDD.** Write/extend the failing test first, then implement.
- Keep `api.py` free of any `homeassistant` import — that is what lets the client
  tests run standalone. Add a new inverter capability to the client first, then
  expose it as a sensor.
- If you ever capture a real device response, prefer a fixture over the synthetic
  `build_response` for parser tests.

## Releasing

Bump `version` in `custom_components/trannergy/manifest.json` (this is what HACS reports) **and** the matching `version` in `pyproject.toml` — `tests/test_manifest.py` fails if they diverge — then add an entry to the README changelog. Commit messages in this repo follow `<version> <short description>` (e.g. `1.1.6 bug fix for reconfiguration not working`).
