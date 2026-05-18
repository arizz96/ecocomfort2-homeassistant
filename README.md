# Ecocomfort 2 — Home Assistant Custom Component

A direct Bluetooth integration for the **Fantini Cosmi Ecocomfort 2** ventilation unit (VMC) with Home Assistant, eliminating the need for ESPHome middleware.

## Features

- **Direct BLE Connection**: No WiFi relay or gateway needed; communicates directly with the device
- **Ventilation Control**: 4-speed fan (Sleep/Vel1/Vel2/Vel3) + 4 preset modes (In/Out/In-Out/Sensor)
- **Sensor Thresholds**: Adjust humidity, luminosity, and VOC sensitivity independently
- **Calibration Offsets**: Fine-tune temperature and humidity readings (±5.0)
- **Seasonal Control**: Winter heat recovery vs. summer bypass mode
- **Free Cooling**: Intensity levels (Off/Low/Medium/High) for passive ventilation
- **Real-time Monitoring**: Temperature, humidity, VOC (ppb), air direction
- **State Readback**: Actual speed/mode confirmation from device
- **Connection Status**: Binary sensor for device connectivity
- **Boost Indicator**: Active boost mode detection
- **Automatic Discovery**: Detects Ecocomfort 2 devices via BLE broadcast
- **Clock Sync**: Automatic device time synchronization (hourly)

## Quick Start

### Installation

1. Copy the integration to Home Assistant:
   ```bash
   cp -r custom_components/ecocomfort2 ~/.homeassistant/custom_components/
   ```

2. Restart Home Assistant

3. Go to **Settings > Devices & Services > Create Integration**

4. Search for **Ecocomfort 2**

5. Either:
   - Select a discovered device, or
   - Manually enter your device's MAC address (find it on the device or in its manual)

### Basic Automations

#### Auto-switch season at temperature threshold
```yaml
automation:
  - alias: Winter to Summer
    trigger:
      platform: numeric_state
      entity_id: sensor.ecocomfort_temperature
      above: 20  # Switch to summer when temp exceeds 20°C
    action:
      service: select.select_option
      entity_id: select.ecocomfort_season
      data:
        option: Summer
```

#### Humidity-triggered boost
```yaml
automation:
  - alias: Boost on high humidity
    trigger:
      platform: numeric_state
      entity_id: sensor.ecocomfort_humidity
      above: 75
    action:
      service: fan.turn_on
      entity_id: fan.ecocomfort
      data:
        percentage: 100  # Max speed
```

## Entities

### Fan (Ventilation Control)
- **`fan.ecocomfort`** — Main ventilation control
  - Speed: 25% (Sleep) / 50% (Vel1) / 75% (Vel2) / 100% (Vel3)
  - Presets: In (inlet only) / Out (exhaust only) / In-Out (alternating) / Sensor (auto)

### Sensors (Read-only)
- **`sensor.ecocomfort_temperature`** — Current room temperature (°C)
- **`sensor.ecocomfort_humidity`** — Current humidity (%)
- **`sensor.ecocomfort_voc`** — Volatile organic compounds (ppb)
- **`sensor.ecocomfort_direction`** — Air flow direction (0-3)
- **`sensor.ecocomfort_actual_mode`** — Currently active mode
- **`sensor.ecocomfort_actual_speed`** — Currently active speed (%)
- **`sensor.ecocomfort_firmware`** — Device firmware version

### Binary Sensors
- **`binary_sensor.ecocomfort_connected`** — Device connectivity status
- **`binary_sensor.ecocomfort_boost_active`** — Boost mode active indicator

### Controls

#### Switches
- **`switch.ecocomfort_humidity_advanced`** — Enable advanced humidity sensitivity
- **`switch.ecocomfort_voc_advanced`** — Enable advanced VOC sensitivity

#### Number Entities (Sliders)
- **`number.ecocomfort_humidity_threshold`** — Humidity sensitivity (0=disabled … 3=high)
- **`number.ecocomfort_luminosity_threshold`** — Light sensor sensitivity
- **`number.ecocomfort_voc_threshold`** — VOC sensitivity
- **`number.ecocomfort_temp_offset`** — Temperature reading offset (±5.0°C)
- **`number.ecocomfort_hum_offset`** — Humidity reading offset (±5.0%)

#### Selects (Dropdowns)
- **`select.ecocomfort_season`** — Winter (heat recovery) / Summer (bypass)
- **`select.ecocomfort_free_cooling`** — Passive cooling intensity
  - Off: Disabled
  - Low: 2°C temperature delta threshold
  - Medium: 4°C delta
  - High: 6°C delta

#### Button
- **`button.ecocomfort_pair`** — Manual BLE reconnection trigger (useful if device goes offline)

## System Requirements

- **Home Assistant** 2023.12+
- **Python** 3.11+
- **Bluetooth** capable system (most Home Assistant installations have this)
- **Fantini Cosmi Ecocomfort 2** device with BLE support

## Troubleshooting

### Device Not Discovered

1. Ensure the Ecocomfort 2 is powered on
2. Check that it's in Bluetooth range (~10+ meters line-of-sight)
3. On the device, enable Bluetooth pairing mode (consult your manual)
4. Restart Home Assistant Bluetooth
5. Try manual MAC address entry instead of auto-discovery

**Finding the MAC address:**
- Check the device's Bluetooth settings
- Look for `BLE_ADDR` in device documentation
- Use a Bluetooth scanner app on your phone

### Connection Drops

- The integration auto-reconnects on next coordinator refresh (30 seconds)
- Press the **Pair** button to manually trigger reconnection
- Check Bluetooth interference in your area (cordless phones, WiFi)
- Ensure your Home Assistant system's Bluetooth antenna is not blocked

### Slow Response

- Default refresh interval is 30 seconds (see `SCAN_INTERVAL` in `__init__.py`)
- Each read fetches 5 characteristics from the device
- Bluetooth latency typically adds 100–500ms per operation
- Consider increasing refresh interval if device/network is struggling

### Data Not Syncing

- Check `binary_sensor.ecocomfort_connected` — if off, BLE is disconnected
- Verify the device isn't controlled by another app (e.g., official Fantini Cosmi app)
- Check Home Assistant logs for BLE errors: `Settings > System > Logs > search "ecocomfort"`

## Technical Details

### Bluetooth Protocol

The device uses BLE GATT with one service containing 5 characteristics:

| Characteristic | Purpose |
|---|---|
| **C_INFO** | Device firmware version, serial, MAC address |
| **C_STATE** | Real-time sensor data (temperature, humidity, VOC, direction) |
| **C_SETTING_OPER** | Operating mode, speed, boost/auto/night flags |
| **C_CONFIGURATION** | Sensitivity thresholds, season, free-cooling level |
| **C_ADVANCED** | Sensor calibration offsets |

All data is properly byte-encoded with correct endianness and scaling factors. The integration uses **0x7F preservation masks** for selective configuration writes, allowing individual settings to be changed without affecting others.

### Device Tree

The integration creates a single device with multiple entities:

```
Device: Ecocomfort 2 [MAC Address]
├── fan.ecocomfort (main control)
├── sensor.ecocomfort_*
├── binary_sensor.ecocomfort_*
├── switch.ecocomfort_*
├── number.ecocomfort_*
├── select.ecocomfort_*
└── button.ecocomfort_pair
```

## Performance

- **State refresh**: 30 seconds (configurable)
- **BLE read latency**: ~100–500ms
- **Memory footprint**: ~5 MB
- **CPU impact**: <1% (idle), <5% (during refresh)

## Development

See [CLAUDE.md](CLAUDE.md) for architecture, protocol details, and contribution guidelines.

### Running Tests

```bash
pip install pytest pytest-asyncio bleak voluptuous
pytest tests/  # 154 tests
```

## License

MIT — See [LICENSE](LICENSE)

## Credits

- Based on the [ESPHome Ecocomfort 2 component](https://github.com/gledian/esphome-ecocomfort2) by gledian
- Fantini Cosmi — https://www.fantini-cosmi.com/
- Home Assistant Developers Docs

## Support

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. Enable debug logging and check `home-assistant.log`
3. Open an issue on GitHub with logs and device information

---

**Note**: This component requires direct Bluetooth access. It will not work with remote Home Assistant instances or setups without local BLE hardware.
