# Ecocomfort 2 - Home Assistant Custom Component

A direct Bluetooth integration for the Fantini Cosmi Ecocomfort 2 ventilation unit with Home Assistant, without requiring ESPHome middleware.

## Features

- **Direct Bluetooth Connection**: Communicates directly with your Ecocomfort 2 device via BLE
- **Climate Control**: Adjust operating modes (Off, Fan-only, Heat, Cool, Auto)
- **Real-time Monitoring**: Track temperature, humidity, and VOC levels
- **Device Information**: Display firmware version and serial number
- **Automatic Discovery**: Detects Ecocomfort 2 devices automatically via BLE

## Installation

### Method 1: Manual Installation

1. Copy the `custom_components/ecocomfort2` directory to your Home Assistant `custom_components` folder:
   ```bash
   cp -r custom_components/ecocomfort2 ~/.homeassistant/custom_components/
   ```

2. Restart Home Assistant

### Method 2: Using HACS (future)

This integration will be available through HACS once published.

## Configuration

1. Go to **Settings > Devices & Services > Create Integration**
2. Search for **Ecocomfort 2**
3. Either:
   - Let the integration auto-discover your device, or
   - Manually enter your Ecocomfort 2 device's MAC address

The integration will automatically:
- Create a climate entity for HVAC control
- Create sensor entities for temperature, humidity, VOC, and direction
- Sync the device clock automatically

## Supported Entities

### Climate Entity
- **Operating Modes**: Off, Fan Only, Heat, Cool, Auto
- **Current Temperature**: Real-time temperature reading
- **Current Humidity**: Real-time humidity percentage

### Sensor Entities
- **Temperature**: Current room temperature in °C
- **Humidity**: Current humidity percentage
- **VOC**: Volatile organic compounds level in ppb
- **Direction**: Air flow direction

## Bluetooth Protocol

The integration uses the following BLE GATT service and characteristics:

**Service UUID**: `f4b827c3-e660-4bc8-bdf6-3c8e9b845e0d`

| Characteristic | UUID | Purpose |
|---|---|---|
| C_INFO | f5f56229-dd4f-480f-a829-9189269d8b37 | Device firmware & serial |
| C_STATE | 438d3433-7e5a-459a-a8e4-66343fad2bb0 | Temperature, humidity, VOC, direction |
| C_SETTING_OPER | b9d6f678-bc0d-4a73-90c8-60b0f07301f1 | Operating mode control |
| C_CONFIGURATION | d3dac48e-b4e1-4f3a-8715-326ddf1da89a | Device configuration (12 bytes) |
| C_SETTING_CLOCK | 82788997-49e4-4533-b949-7ed433678044 | Clock synchronization |
| C_ADVANCED | f8b2284e-61dd-44e3-a782-a93c9503ab2d | Sensor calibration (4 bytes) |

## Requirements

- Python 3.11+
- Home Assistant 2023.12 or newer
- Bluetooth-capable system
- Fantini Cosmi Ecocomfort 2 device

## Data Collection

This integration reads the following data from your device:
- Temperature
- Humidity
- VOC (Volatile Organic Compounds)
- Air flow direction
- Operating mode
- Firmware version
- Serial number

The integration automatically syncs the device clock on startup to ensure accurate scheduling.

## Troubleshooting

### Device Not Found

1. Ensure your Ecocomfort 2 is powered on
2. Check that it's in Bluetooth pairing mode (consult your device manual)
3. Verify Bluetooth is enabled on your Home Assistant system
4. Try manually entering the MAC address (find it on your device or in its manual)

### Connection Issues

1. Make sure your Home Assistant system is within Bluetooth range (typically 10+ meters)
2. Try restarting the Ecocomfort 2 device
3. Check your Home Assistant logs for specific errors

## Development

This integration is based on the ESPHome Ecocomfort 2 component by gledian and provides direct Bluetooth connectivity without requiring ESPHome middleware.

### Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - See LICENSE file for details

## References

- [Original ESPHome Component](https://github.com/gledian/esphome-ecocomfort2)
- [Fantini Cosmi](https://www.fantini-cosmi.com/)
