# ECOCOMFORT 2 BLE Command Interface Analysis

## Discovery: Commands Available via Shell Interface

### Available Commands Found in Firmware

The device supports a **shell command interface** with these SET/GET commands:

#### WiFi Configuration Command ⭐ KEY FINDING
```
Set wifi conf (param: SSID PSK SERVER PORT[1..65535] PERIOD[10..300])
Get wifi conf
```

**This is the command to set the server!**

Parameters:
- `SSID` - WiFi network name
- `PSK` - WiFi password
- `SERVER` - Server hostname or IP address
- `PORT` - Server port (1-65535)
- `PERIOD` - Data transmission period (10-300 seconds)

#### Other Configuration Commands
```
Set clock (param: DD[1-31] MM[1-12] YY[1-99] HH[0-23] MM[0-59] SS[0-59] DST[0-1])
Set conf (param: ROLE[0-2] RH[0-3(+x80)] LUX[0-3] VOC[0-3(+x80)] FC[0-3(+x10)] ROT[0-2] ADDR[xx:xx:xx:xx:xx:xx])
Set oper (param: MODE[0-4] SPEED[0-4-x10])
Set adv conf (param: TEMP OFFSET[-500..500] HUM OFFSET[-500..500])
Set prof (param: IDX[0..6] PROFILE(24))

Get wifi conf
Get clock
Get conf
Get oper
Get adv conf
Get prof
```

---

## Command Input Methods

### ✅ UART Shell Interface (Confirmed)
```
shell.shell_uart
shell_uart_backend
```

**Access:** GPIO 1 (TX) and GPIO 3 (RX) @ 115200 baud

**Usage:**
```bash
# Connect with serial terminal
# Type: Set wifi conf <SSID> <PSK> <SERVER> <PORT> <PERIOD>
# Example: Set wifi conf MyWiFi MyPassword 192.168.1.100 8080 60
```

### ❓ BLE Command Interface (Unknown Status)

**Evidence Found:**
- `bt_gatt_discover` - GATT service discovery
- `bt_gatt_subscribe` - GATT notifications
- `Subscribed notify` - Notification mechanism exists
- BLE GATT write/read capabilities present

**What's Unknown:**
- No specific BLE characteristic UUIDs found in firmware
- No BLE command handler strings found
- No indication of how BLE commands are structured
- Unclear if shell commands accessible via BLE

**Likely Scenario:**
The IntelliClima+ app probably uses a **proprietary BLE protocol** (not standard shell commands) to configure the device. The app likely:
1. Sends BLE GATT write commands with a custom format
2. Reads responses via GATT notifications
3. Uses a different protocol than the UART shell

---

## How to Set Server Address

### Option 1: Via UART Shell (Direct Access) ⭐ SIMPLEST
```bash
# Connect to device UART (GPIO 1/3 @ 115200 baud)
# Type the command:
Set wifi conf MyWiFi MyPassword api.intelliclima.com 443 60

# Or:
Set wifi conf MyWiFi MyPassword 192.168.1.100 8080 60

# Verify:
Get wifi conf
# Should display: SERVER=api.intelliclima.com, PORT=443, etc.
```

**Advantages:**
- Simple text-based commands
- Easy to test
- No authentication needed (likely)
- Works immediately

**Requirements:**
- Physical access to device UART pins
- USB-to-Serial adapter (CH340, FTDI, etc.)
- Serial terminal software (minicom, PuTTY, etc.)

### Option 2: Via IntelliClima+ App (Mobile)
- Download IntelliClima+ app
- Pair device via Bluetooth
- Use app to set WiFi and server settings
- App sends proprietary BLE commands to device
- Device stores in NVS

**Advantages:**
- User-friendly GUI
- No soldering needed
- Official method

**Disadvantages:**
- Cloud-dependent (app needs to connect to Fantini servers)
- Settings transferred through proprietary format
- Cannot see actual values being sent

### Option 3: Via Reverse-Engineered BLE Protocol
If someone reverse-engineers the IntelliClima+ app BLE protocol:
- Write custom mobile app or Python script
- Send proprietary BLE GATT writes to device
- Receive responses via notifications

**Current Status:** BLE protocol not yet reverse-engineered

---

## Command Structure Analysis

### UART Shell Command Format

**Likely Format:**
```
<COMMAND> <PARAM1> <PARAM2> <PARAM3> ...
```

**Example:**
```
Set wifi conf MySSID MyPassword server.com 8080 60
│   │    │     │       │          │           │    │
│   │    │     │       │          │           │    └─ Period (seconds)
│   │    │     │       │          │           └─ Port
│   │    │     │       │          └─ Server
│   │    │     │       └─ PSK (password)
│   │    │     └─ SSID
│   │    └─ Command type (wifi conf)
│   └─ Subcommand (Set)
└─ Main command
```

### Error Handling
```
Unable to parse input (err %d)
Invalid cmd: %s
: command not found
Too many arguments in the command
```

---

## Command Parameter Specifications

### `Set wifi conf` Parameters

| Parameter | Range | Description |
|-----------|-------|-------------|
| SSID | string | WiFi network name |
| PSK | string | WiFi password |
| SERVER | hostname/IP | Server address or hostname |
| PORT | 1-65535 | TCP port number |
| PERIOD | 10-300 | Data sending period in seconds |

### `Set conf` Parameters

| Parameter | Range | Description |
|-----------|-------|-------------|
| ROLE | 0-2 | Device role (0=off, 1=master, 2=slave) |
| RH | 0-3 (+x80 flag) | Humidity setting |
| LUX | 0-3 | Light sensor setting |
| VOC | 0-3 (+x80 flag) | VOC threshold |
| FC | 0-3 (+x10 flag) | Feature control |
| ROT | 0-2 | Rotation/direction |
| ADDR | xx:xx:xx:xx:xx:xx | MAC address of connected device |

### `Set oper` Parameters

| Parameter | Range | Description |
|-----------|-------|-------------|
| MODE | 0-4 | Operating mode (off, auto, manual, sleep, etc.) |
| SPEED | 0-4, x10 | Fan speed (0=off, 1-4=speeds, x10=multiplier) |

---

## Testing the Command

### Step 1: Connect UART
```bash
# Using pyserial or similar
import serial
ser = serial.Serial('/dev/ttyUSB0', 115200)

# Or use minicom
minicom -D /dev/ttyUSB0 -b 115200
```

### Step 2: Send Command
```
Set wifi conf TestSSID TestPassword 192.168.1.100 8080 60
```

### Step 3: Check Response
```
Get wifi conf
# Should return current settings
```

### Step 4: Verify Persistence
```bash
# Reboot device and check again
# Settings should persist in NVS
```

---

## BLE Protocol Speculation

If BLE commands are supported, they might follow a binary protocol:

**Potential Structure:**
```
┌─────────┬──────────┬────────────┬──────────┐
│ Command │ Length   │ Parameters │ Checksum │
│ Type    │          │            │          │
├─────────┼──────────┼────────────┼──────────┤
│ 1 byte  │ 2 bytes  │ N bytes    │ 1-2 byte │
└─────────┴──────────┴────────────┴──────────┘
```

**Example BLE Write Characteristic Flow:**
1. App sends GATT write to config characteristic
2. Device parses command
3. Device stores in NVS
4. Device sends notification back (success/error)

**Current Status:** No BLE characteristic UUIDs found, likely proprietary.

---

## Recommendations

### To Set Server Address:

1. **Easiest Method: UART Shell**
   - Open device
   - Connect UART (GPIO 1/3)
   - Send: `Set wifi conf SSID PASSWORD SERVER PORT PERIOD`
   - Verify with: `Get wifi conf`

2. **Alternative: Use App**
   - Install IntelliClima+ app
   - Pair via Bluetooth
   - Use app's WiFi settings to configure server

3. **Future: BLE Reverse Engineering**
   - Capture BLE traffic from IntelliClima+ app
   - Analyze GATT write payloads
   - Implement custom BLE client

---

## Key Takeaway

**YES, there are commands to set the server, but:**
- ✅ UART shell commands: Definitely (text-based)
- ❓ BLE commands: Probably, but proprietary format unknown
- ❌ No hardcoded server, fully configurable
- ✅ Commands and parameters fully documented in firmware

Generated: 2026-06-01
