# Ecocomfort 2 Home Assistant Component — Project Documentation

## Overview

A direct Bluetooth custom component for Home Assistant that controls Fantini Cosmi Ecocomfort 2 ventilation units (VMC — ventilazione meccanica controllata) without requiring ESPHome middleware. The component communicates directly via BLE GATT with the device's 5 characteristics.

**Status**: Feature-complete, production-ready. 154 passing tests.

## Architecture

### Core Device Layer (`ecocomfort.py`)
- **`EcocomfortDevice`**: Low-level BLE interface
  - Connects/disconnects via Bleak library
  - Reads 5 GATT characteristics and updates `EcocomfortState`
  - Writes commands with proper byte encoding and 0x7F preservation masks
  - Auto-connects on read failure; syncs clock hourly

- **`EcocomfortState`**: Data class mirroring all device state
  - Environmental: temperature, humidity, VOC, direction
  - Control: operating_mode, speed, boost_active, auto_mode, night_mode
  - Config: thresholds (3), offsets (2), season, free_cooling, role
  - Device info: firmware, serial
  - Connectivity: connected flag

### Integration Layer (`__init__.py`)
- Sets up coordinator pattern with 30-second refresh interval
- Forwards to 7 entity platforms
- Handles setup and teardown

### Entity Platforms

| Platform | File | Entities | Controls |
|---|---|---|---|
| **fan** | `fan.py` | 1 | Speed (25/50/75/100%), Preset (In/Out/In-Out/Sensor) |
| **sensor** | `sensor.py` | 7 | Temperature, Humidity, VOC, Direction, Actual Mode, Actual Speed, Firmware |
| **binary_sensor** | `binary_sensor.py` | 2 | Connected, Boost Active |
| **switch** | `switch.py` | 2 | Humidity Advanced, VOC Advanced |
| **number** | `number.py` | 5 | Humidity Threshold, Luminosity Threshold, VOC Threshold, Temp Offset, Hum Offset |
| **select** | `select.py` | 2 | Season, Free Cooling |
| **button** | `button.py` | 1 | Pair (manual reconnect) |

### Configuration (`config_flow.py`)
- BLE device discovery by service UUID or device name
- Manual MAC address entry
- Prevents duplicate device configuration

## Protocol

### BLE Service
**UUID**: `f4b827c3-e660-4bc8-bdf6-3c8e9b845e0d`

### Characteristics

| Name | UUID | Size | Dir | Purpose |
|---|---|---|---|---|
| C_INFO | f5f56229-... | 8+ | R | Nibble-encoded firmware, serial |
| C_STATE | 438d3433-... | 9 | R | Temperature, humidity, VOC, direction |
| C_SETTING_OPER | b9d6f678-... | 2 | R/W | Operating mode, speed, boost/auto/night flags |
| C_CONFIGURATION | d3dac48e-... | 12 | R/W | Thresholds, season, free cooling (with 0x7F masks) |
| C_SETTING_CLOCK | 82788997-... | 8 | W | Date/time sync |
| C_ADVANCED | f8b2284e-... | 4 | R/W | Calibration offsets (big-endian, ×100) |

### Key Data Formats

**C_STATE** (9 bytes, little-endian):
```
Bytes 0-1: reserved
Byte 2:    direction (0-3)
Bytes 3-4: temperature (int16 / 100 = °C)
Bytes 5-6: humidity (uint16 / 100 = %)
Bytes 7-8: VOC (uint16 ppb)
```

**C_SETTING_OPER** (2 bytes):
```
Byte 0: mode (0=Off, 1=In, 2=Out, 3=In-Out, 4=Sensor)
Byte 1: speed (bits 0-3) + flags
  - Bits 0-3: speed (1=Sleep/25%, 2=Vel1/50%, 3=Vel2/75%, 4=Vel3/100%)
  - Bit 4: auto flag (0x10)
  - Bit 5: advanced control (0x20)
  - Bit 6: boost active (0x40, read-only)
  - Bit 7: night/sleep mode (0x80)
```

**C_CONFIGURATION** (12 bytes):
```
Byte 0:   role (0=unconfigured, 1=master, 2=slave)
Byte 1:   humidity threshold (0-3, bit 7 = advanced flag)
Byte 2:   luminosity threshold (0-3)
Byte 3:   VOC threshold (0-3, bit 7 = advanced flag)
Byte 4:   free cooling (bits 0-1: 0-3) + season (bit 3: 0=Winter, 1=Summer)
Byte 5:   rotation
Bytes 6-11: master BLE address
```

**C_ADVANCED** (4 bytes, big-endian):
```
Bytes 0-1: temperature offset (int16 / 100 = °C, range ±5.0)
Bytes 2-3: humidity offset (int16 / 100 = %, range ±5.0)
```

## Development

### Setup
```bash
pip install -r requirements-dev.txt
pytest tests/  # 154 tests, full coverage
ruff check custom_components/ecocomfort2/
mypy custom_components/ecocomfort2/
```

### Adding Features
- Protocol parsing: extend `_parse_*()` methods in `ecocomfort.py`
- Write commands: add `async_set_*()` methods maintaining 0x7F masks
- New entities: create platform file following existing patterns
- Tests: add to `tests/test_*.py` with stubs for HA imports

### Testing Approach
- Mock `BleakClient` for all BLE operations
- Use `conftest.py` helper builders (`make_*_bytes()`) for protocol testing
- Lightweight HA stubs in `tests/stubs/` allow testing without full HA installation
- 154 tests cover parsing edge cases, byte orders, preservation masks

## Known Limitations

1. **C_PROGRAMS** (weekly schedule, 168 bytes) — not implemented
2. **C_STATS** (usage statistics) — not implemented
3. **100ms command debounce** — not implemented (nice-to-have, not critical)
4. **Initial state on first startup** — device state only populated after first async_update()

## References

- Original ESPHome component: https://github.com/gledian/esphome-ecocomfort2
- Fantini Cosmi: https://www.fantini-cosmi.com/
- Home Assistant integration docs: https://developers.home-assistant.io/docs/creating_integration_index/
- Bleak library: https://github.com/hynek/bleak

## File Structure

```
custom_components/ecocomfort2/
├── __init__.py           # Integration setup, platforms, coordinator
├── ecocomfort.py         # Core BLE device class & data model
├── config_flow.py        # Config UI, BLE discovery
├── fan.py                # Ventilation speed/preset control
├── sensor.py             # Environmental & state readback sensors
├── binary_sensor.py      # Connected, boost active
├── switch.py             # Advanced sensor mode toggles
├── number.py             # Thresholds, calibration offsets
├── select.py             # Season, free cooling intensity
├── button.py             # Manual pairing trigger
├── manifest.json         # Integration metadata
├── strings.json          # UI translations
└── py.typed              # Type hints marker

tests/
├── conftest.py           # Shared fixtures, byte builders
├── test_ecocomfort.py    # Protocol parsing & write commands (48 tests)
├── test_fan.py           # Fan entity behavior (26 tests)
├── test_sensor.py        # Sensor value mapping (11 tests)
├── test_binary_sensor.py # Binary sensor states (4 tests)
├── test_switch.py        # Switch toggle behavior (6 tests)
├── test_number.py        # Number entity writes (11 tests)
├── test_select.py        # Select option handling (16 tests)
├── test_config_flow.py   # Discovery & setup (15 tests)
└── stubs/                # Lightweight HA mocks for testing
```

## Version History

- **0.2.0** — Full feature parity with ESPHome component; corrected all protocol parsing; added 6 new platforms
- **0.1.0** — Initial structure with climate entity (deprecated)
