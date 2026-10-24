# Home Assistant Trannergy PV Inverter Custom Component

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)

The Trannergy PV Inverter custom component uses local polling to retrieve data from a Trannergy PV inverter.
The values will be presented as sensors in [Home Assistant](https://home-assistant.io/).

> ❤️ This integration is a continuation of [hultenvp/home_assistant_omnik_solar](https://github.com/hultenvp/home_assistant_omnik_solar), which is now archived.

![Home Assistant dashboard showing Trannergy PV Inverter custom component](https://raw.githubusercontent.com/strepto42/home-assistant-omnik-trannergy-pv-inverter/master/images/omnik_sensor_ui.png)

## Features

- **Config Flow Setup**: Easy configuration through the Home Assistant UI (no YAML required!)
- **Async Communication**: Fully async TCP communication for better performance
- **Configurable Polling**: Set custom scan intervals (default 30 seconds)
- **Offline Handling**: Gracefully handles inverter going offline at night
- **Multiple Sensors**: Support for all inverter data points including DC input, AC output, power, energy, and more
- **Options Flow**: Change scan interval and enable/disable sensors without reconfiguring
- **Reconfigure**: Change the inverter IP address or port in place, keeping history and totals

## Supported Inverters

This integration has been tested with a Trannergy SGN5400TL that has a wifi kit with serial number starting with 645xxxxxx.

Please comment on your experience with this integration in the [GitHub discussion](https://github.com/strepto42/home-assistant-omnik-trannergy-pv-inverter/discussions).

## Installation

### HACS Installation (Recommended)

Click here to add the repository: [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=strepto42&repository=home-assistant-omnik-trannergy-pv-inverter&category=integration)

Or manually:

1. Open the HACS dashboard by clicking on HACS in the left-hand menu
2. Click on the 3 dots in the top right corner
3. Select "Custom repositories"
4. Add the URL: `https://github.com/strepto42/home-assistant-omnik-trannergy-pv-inverter/`
5. Select "Integration"
6. Click the "ADD" button
7. Search for "Trannergy" and install

### Manual Installation

1. Create a directory called `trannergy` in the `<config directory>/custom_components/` directory
2. Copy all files from [`/custom_components/trannergy/`](https://github.com/strepto42/home-assistant-omnik-trannergy-pv-inverter/tree/master/custom_components/trannergy) into the new directory

Your `custom_components/` directory should look like this:

```
custom_components/
└── trannergy/
    ├── __init__.py
    ├── api.py
    ├── config_flow.py
    ├── const.py
    ├── coordinator.py
    ├── manifest.json
    ├── sensor.py
    ├── strings.json
    └── translations/
        └── en.json
```

## Configuration

### Adding the Integration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Trannergy PV Inverter"
4. Enter the required configuration:
   - **Name**: A friendly name for your inverter (e.g., "Solar Inverter")
   - **Inverter Serial Number**: The serial number of your WiFi/LAN module (e.g., 1612345603)
   - **Inverter IP Address**: The local IP address of your inverter (e.g., 192.168.1.123)
   - **Inverter Port**: TCP port (default: 8899)
   - **Scan Interval**: How often to poll the inverter in seconds (default: 30)

5. Click **Submit**

> **Note**: The inverter may be offline at night when solar production stops. This is normal behavior and the integration handles it gracefully.

### Configuring Options

After adding the integration, you can configure options:

1. Go to **Settings** → **Devices & Services**
2. Find your Trannergy integration and click **Configure**
3. Adjust the scan interval and enable/disable individual sensors

### Changing the IP Address or Port

If your inverter gets a new IP address (or you need a different port):

1. Go to **Settings** → **Devices & Services**
2. Find your Trannergy integration, click the **⋮** menu and choose **Reconfigure**
3. Enter the new IP address and/or port

The existing entry is updated in place, so your sensor history and the preserved energy/hours totals are kept. You can do this while the inverter is offline.

## Available Sensors

| Sensor | Description | Unit |
|--------|-------------|------|
| `status` | Inverter online/offline status | - |
| `actualpower` | Current power output | W |
| `energytoday` | Energy generated today | kWh |
| `energytotal` | Total energy generated | kWh |
| `hourstotal` | Total operating hours | h |
| `invertersn` | Inverter serial number | - |
| `temperature` | Inverter temperature | °C |
| `dcinputvoltage1-3` | DC input voltage (channels 1-3) | V |
| `dcinputcurrent1-3` | DC input current (channels 1-3) | A |
| `acoutputvoltage1-3` | AC output voltage (channels 1-3) | V |
| `acoutputcurrent1-3` | AC output current (channels 1-3) | A |
| `acoutputfrequency1-3` | AC output frequency (channels 1-3) | Hz |
| `acoutputpower1-3` | AC output power (channels 1-3) | W |

## Troubleshooting

### Inverter Shows Offline

- **At night**: This is normal. The inverter powers down when there's no solar production.
- **During the day**: Check that:
  - The IP address is correct
  - The inverter is connected to your network
  - Port 8899 is not blocked by a firewall
  - The serial number matches your WiFi/LAN module

### Connection Timeouts

The integration uses a 10-second timeout for connections. If your network is slow, ensure the inverter has a stable connection.

### Debug Logging

To enable debug logging, add the following to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.trannergy: debug
```

## File Structure

```
custom_components/trannergy/
├── __init__.py       # Integration setup and config entry handling
├── api.py            # Async API client for inverter communication
├── config_flow.py    # Config flow and options flow handlers
├── const.py          # Constants and sensor definitions
├── coordinator.py    # Data update coordinator
├── manifest.json     # Integration manifest
├── sensor.py         # Sensor entity definitions
├── strings.json      # Localization strings
└── translations/
    └── en.json       # English translations
```

## Thanks 🌞

Big thanks to:

* [@heinoldenhuis](https://github.com/heinoldenhuis) for the original integration
* [@hultenvp](https://github.com/hultenvp) for previously maintaining this HACS custom component

## Similar Projects

If this custom component is not working for you, please try these similar projects:

* [davidrapan/ha-solarman](https://github.com/davidrapan/ha-solarman): Solarman Stick Logger integration for Home Assistant
* [StephanJoubert/home_assistant_solarman](https://github.com/StephanJoubert/home_assistant_solarman): Home Assistant component for Solarman collectors

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

### v1.1.7

- Added a **Reconfigure** step so the inverter IP address and port can be changed without deleting the integration (history and preserved totals are kept)

### v1.0.0

- **Breaking Change**: Migrated from YAML configuration to Config Flow (UI-based setup)
- Renamed integration from "Omnik" to "Trannergy"
- Fully async API client for improved performance
- Added DataUpdateCoordinator for efficient data updates
- Added options flow to configure sensors and scan interval
- Improved error handling for offline inverter scenarios
- Added proper device info and unique IDs for all entities
