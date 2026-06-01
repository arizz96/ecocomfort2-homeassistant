# ECOCOMFORT 2 Firmware (v0.6.8) Analysis

## File Information
- **Filename:** ecocomfort_firmware_0.6.8.bin
- **Size:** 410,156 bytes (~401 KB)
- **Format:** Binary (Zephyr RTOS compiled firmware)
- **Device ID:** ECMF2-* (ECOCOMFORT 2)

## Runtime Environment
- **OS:** Zephyr RTOS (embedded real-time OS)
- **Not:** ESP-IDF (uses Zephyr instead of traditional Arduino/ESP framework)
- **Compiler:** ARM Zephyr EABi toolchain

## Device Configuration Structure

### WiFi Settings (`wifi_conf/`)
- `wifi_conf/ssid` - Network SSID
- `wifi_conf/psk` - WiFi password
- `wifi_conf/server` - Server address (configurable)
- `wifi_conf/port` - Server port (1-65535)
- `wifi_conf/period` - Communication period (10-300 seconds)
- `wifi_conf/active` - Enable/disable WiFi

### Time/NTP Settings (`sntp/`)
- `sntp/name` - NTP server name
- `sntp/port` - NTP port
- `sntp/timezone` - Timezone configuration

**Default NTP Servers Found:**
- `time.google.com`
- DNS: 8.8.8.8 (Google)
- DNS: 4.4.4.4 (Cloudflare)

### Bluetooth Settings (`bt/`)
- `bt/keys` - BLE pairing keys
- `bt/ccc` - CCCD (Client Characteristic Configuration)
- `bt/id` - BLE device ID
- `bt/name` - Bluetooth device name
- `bt/cf` - Connection flags
- `bt/sc` - Secure connection config

### Device Configuration (`conf/`)
- `conf/fc_en` - Feature control enable
- `conf/fc_t` - Feature control temperature
- `conf/role` - Device role
- `conf/slv_addr` - Slave addresses (up to 10 devices: `dev/addr_0` to `dev/addr_9`)
- `conf/slv_rot` - Slave rotation
- `conf/lum` - Luminosity/light settings
- `conf/rh_t` - Relative humidity temperature
- `conf/voc_t` - VOC (Volatile Organic Compounds) threshold

### Operating Settings (`oper/`)
- `oper/mode` - Operating mode
- `oper/speed` - Fan speed control

### Status/Statistics (`stat/`)
- `stat/idx` - Status index
- `stat/flt_wrn_count` - Filter warning count

### Profiles (`prof/`)
- `prof/day_0` through `prof/day_6` - Daily profiles (week schedule)

## Key Features Identified

### Firmware Update Mechanism
- **Command:** `FIRMWARE_UPGRADE`
- **Method:** Block-based transfer
- **Format:** "Starting update to v0x%04x (block size: %u, total size: %u)"
- **Storage:** NVS (non-volatile storage) with atomic commits

### Communication Protocols
- **Bluetooth LE (BLE)** - Local device control
- **WiFi** - Cloud connectivity
- **SNTP** - Time synchronization

### Device Pairing
- Multiple slave devices supported (up to 10: `dev/addr_0` through `dev/addr_9`)
- Bluetooth pairing with security levels
- Device MAC addresses stored: `ECMF2-%02X:%02X:%02X:%02X:%02X:%02X`

## Configuration Interface
The device supports:
```
Set wifi conf (param: SSID PSK SERVER PORT[1..65535] PERIOD[10..300])
```

## Storage & Settings
- NVS (Non-Volatile Storage) based configuration
- Settings keys organized hierarchically with `/` separators
- Support for atomic updates and rollback

## Observations
1. **Zephyr-based**, not standard ESP32 Arduino/IDF
2. **Server address is configurable** via WiFi settings
3. **No hardcoded cloud URL** found - likely configured at runtime
4. **Time-sync based updates** using SNTP before firmware upgrade
5. **BLE-first design** for local control without cloud
6. **Multi-device support** with up to 10 slave ECMF2 units

## Next Steps
To find the actual cloud server address:
1. Capture WiFi traffic during device initialization
2. Monitor the `wifi_conf/server` setting when app communicates
3. Check if server address is provided by the mobile app
4. Monitor HTTPS traffic to identify cloud endpoints
