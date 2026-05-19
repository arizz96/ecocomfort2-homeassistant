# Development Guide

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/arizz96/ecocomfort2-homeassistant.git
   cd ecocomfort2-homeassistant
   ```

2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

## Testing

Run tests with:
```bash
pytest
```

With coverage:
```bash
pytest --cov=custom_components/ecocomfort2
```

## Code Quality

### Linting
```bash
ruff check custom_components/ecocomfort2/
```

### Type Checking
```bash
mypy custom_components/ecocomfort2/
```

## Project Structure

```
custom_components/ecocomfort2/
├── __init__.py              # Integration setup and initialization
├── config_flow.py           # Configuration UI and discovery
├── ecocomfort.py            # Core BLE device communication
├── climate.py               # Climate entity (HVAC control)
├── sensor.py                # Sensor entities (temperature, humidity, etc)
├── manifest.json            # Integration metadata
├── strings.json             # UI translations
└── py.typed                 # Type hints marker
```

## Key Components

### EcocomfortDevice (ecocomfort.py)
Core class that handles all BLE communication with the device:
- `async_connect()` - Connect to the device
- `async_disconnect()` - Disconnect from the device
- `async_update()` - Read current device state
- `async_set_operating_mode()` - Change HVAC mode
- `async_set_configuration()` - Write device configuration
- `async_set_advanced()` - Write calibration data

### Climate Entity (climate.py)
Exposes the device as a climate entity with:
- Operating mode selection (Off, Fan, Heat, Cool, Auto)
- Current temperature reading
- Current humidity reading
- Extra attributes (VOC, direction, firmware, serial)

### Sensor Entities (sensor.py)
Individual sensors for:
- Temperature
- Humidity
- VOC (Volatile Organic Compounds)
- Direction

## BLE Protocol Details

The integration communicates with the device using BLE GATT characteristics:

**Service**: `f4b827c3-e660-4bc8-bdf6-3c8e9b845e0d`

| Characteristic | UUID | Type | Bytes | Purpose |
|---|---|---|---|---|
| C_INFO | f5f56229-dd4f-480f-a829-9189269d8b37 | R | 8+ | Firmware (4) + Serial (4+) |
| C_STATE | 438d3433-7e5a-459a-a8e4-66343fad2bb0 | R | 8+ | Temp(2), Humidity(1), VOC(2), Direction(1), Pad(2) |
| C_SETTING_OPER | b9d6f678-bc0d-4a73-90c8-60b0f07301f1 | R/W | 2 | Operating Mode (little-endian u16) |
| C_CONFIGURATION | d3dac48e-b4e1-4f3a-8715-326ddf1da89a | R/W | 12 | Device configuration |
| C_SETTING_CLOCK | 82788997-49e4-4533-b949-7ed433678044 | W | 8 | YY, MM, DD, HH, MM, SS, DOW, PAD |
| C_ADVANCED | f8b2284e-61dd-44e3-a782-a93c9503ab2d | R/W | 4 | Sensor calibration offsets |

### Data Formats

#### C_STATE (Device State)
```
Offset  Size  Type    Description
0       2     i16     Temperature (°C × 10, little-endian)
2       1     u8      Humidity (0-100%)
3       2     u16     VOC (ppb, little-endian)
5       1     u8      Direction
6       2     u16     Padding
```

#### C_SETTING_OPER (Operating Mode)
```
Value   Mode
0       Off
1       Fan Only
2       Heat
3       Cool
4       Auto
```

#### C_SETTING_CLOCK (Clock Sync)
```
Offset  Size  Type    Description
0       1     u8      Year (0-99, e.g., 24 = 2024)
1       1     u8      Month (1-12)
2       1     u8      Day (1-31)
3       1     u8      Hour (0-23)
4       1     u8      Minute (0-59)
5       1     u8      Second (0-59)
6       1     u8      Day of Week (0=Monday, 6=Sunday)
7       1     u8      Padding
```

## Debugging

Enable debug logging in Home Assistant configuration.yaml:
```yaml
logger:
  logs:
    custom_components.ecocomfort2: debug
```

Check the Home Assistant logs at `~/.homeassistant/home-assistant.log`

## Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes and test thoroughly
3. Run linting and type checks
4. Commit with clear messages
5. Push to your fork and create a Pull Request

## References

- [Home Assistant Integration Development](https://developers.home-assistant.io/docs/creating_integration_index/)
- [BLE Platform Documentation](https://developers.home-assistant.io/docs/device_tracker/bluetooth)
- [Bleak Library](https://github.com/hynek/bleak) - BLE communication
