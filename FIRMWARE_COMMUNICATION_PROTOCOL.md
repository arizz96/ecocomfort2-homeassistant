# ECOCOMFORT 2 Firmware Communication Protocol Analysis

## Summary

The device uses a **persistent TCP connection** to send periodic data updates to a remote server. Communication is controlled via AT commands to an embedded WiFi/TCP module.

---

## Connection Details

### Network Configuration (Configurable via `wifi_conf/`)
```
SSID: <WiFi SSID>
PSK: <WiFi Password>
SERVER: <Server Address/IP>
PORT: <1-65535> (default likely 8000-8080 or 443)
PERIOD: <10-300 seconds> (data transmission interval)
```

### Connection Establishment
**AT Commands Used:**
```
AT+CWMODE=1          # Station mode (connect to WiFi)
AT+CWJAP="SSID","PSK"  # Connect to WiFi AP
AT+CIPSTART=0,"TCP","SERVER",PORT,7200  # Open TCP connection
                     # Timeout: 7200 seconds (2 hours)
                     # Link ID: 0 (single connection)
```

### Data Transmission
**Sending Data:**
```
AT+CIPSEND=0,<LENGTH>   # Send LENGTH bytes on link 0
<BINARY_DATA>           # Raw data payload
```

**Receiving Data:**
```
AT+CIPRECVDATA=0,<LENGTH>  # Receive up to LENGTH bytes
+CIPRECVDATA:0,<DATA>      # Response with received data
```

### Connection Management
```
AT+CIPCLOSE=0              # Close TCP connection
AT+CIPSTA?                 # Check IP status
AT+CIPSTAMAC?              # Check MAC address
```

---

## Data Transmission Architecture

### Threading Model
```
┌─────────────────────────────────────────────┐
│  Zephyr RTOS Kernel                         │
├─────────────────────────────────────────────┤
│  Thread: send_data_thread                   │
│  ├─ Reads sensor data (temp, humidity, etc) │
│  ├─ Packages into payload                   │
│  ├─ Queues data via k_msgq (message queue)  │
│  └─ Sends via AT+CIPSEND                    │
├─────────────────────────────────────────────┤
│  Thread: receive_data_thread                │
│  ├─ Listens for server responses            │
│  ├─ Processes commands from server          │
│  └─ Updates local device state              │
├─────────────────────────────────────────────┤
│  Thread: open_sock_work_handler             │
│  ├─ Opens TCP connections                   │
│  ├─ Handles DNS resolution                  │
│  └─ Manages connection errors               │
├─────────────────────────────────────────────┤
│  Thread: close_sock_work_handler            │
│  ├─ Closes connections on timeout           │
│  └─ Cycles connections periodically         │
└─────────────────────────────────────────────┘
```

### Timing Architecture
```
PERIOD (10-300s)              F_CLOSE_SOCK_PERIOD (likely hours)
│                             │
├─ Send sensor data ─────────┼──────────────┐
│  ├─ Temperature             │              │
│  ├─ Humidity                │              │
│  ├─ Fan speed/direction     │              │
│  ├─ VOC index               │              │
│  └─ Device status           │              │
│                             │              │
├─ Receive server commands ──┤              │
│  ├─ Fan control            │              │
│  ├─ Settings changes       │              │
│  └─ Firmware updates       │              │
│                             │              │
└─────────────────────────────┴──────────────┘
                              │
                    Close & Reopen Connection
                    (Keep-alive cycle)
```

---

## Data Payload Format

### Unknown (Proprietary Binary Format)

**What we know:**
- Uses `AT+CIPSEND` with binary data
- Periodic transmission every 10-300 seconds
- Server likely responds with commands
- Supports device control, settings, and firmware updates

**Data likely includes:**
```
- Device ID: ECMF2-%08lx (serial number)
- Temperature readings (multiple sensors)
- Humidity readings
- VOC (air quality) index
- Fan state (speed, direction)
- Device status flags
- Uptime/statistics
```

**Possible formats:**
1. **Custom Binary Protocol** (most likely)
   - Fixed header with message type
   - Device ID and timestamp
   - Binary-encoded sensor values
   - CRC/checksum for validation

2. **JSON** (possible but strings not in firmware)
   - Would need JSON encoder library
   - Not detected in binary

3. **Protocol Buffers** (possible)
   - Compact binary serialization
   - No protobuf markers found in strings

**Packet Structure (Estimated):**
```
┌────────────┬────────────┬─────────────┬──────────┬────────────┐
│   Header   │ Device ID  │ Timestamp   │ Sensors  │ Checksum   │
├────────────┼────────────┼─────────────┼──────────┼────────────┤
│ 1-4 bytes  │ 4 bytes    │ 4 bytes     │ N bytes  │ 1-4 bytes  │
└────────────┴────────────┴─────────────┴──────────┴────────────┘
```

---

## Server Response Handling

### Possible Commands from Server
Based on firmware features found:
```
- FAN_CONTROL: Set speed (0-4) and direction (IN/OUT)
- MODE_CHANGE: Switch operating modes
- SETTINGS_UPDATE: Change thresholds/parameters
- FIRMWARE_UPGRADE: Push new firmware
- HEARTBEAT_ACK: Connection keep-alive
```

### Error Handling
```
send_data_thread_handler - send error %d
open_sock_work_handler - unable to resolve address, error: %d
open_sock_work_handler - socket result error %d
open_sock_work_handler - connect result error %d
Failed to send data: link %d, ret %d
```

---

## Connection Lifecycle

```
1. WiFi STARTUP
   ├─ Read wifi_conf/ssid, psk, server, port, period from NVS
   ├─ Execute AT+CWMODE=1
   └─ Execute AT+CWJAP="SSID","PSK"

2. DNS RESOLUTION
   ├─ Resolve SERVER hostname to IP
   └─ Error: "unable to resolve address"

3. TCP CONNECTION
   ├─ Execute AT+CIPSTART=0,"TCP","SERVER",PORT,7200
   ├─ Wait for connection result
   └─ Error: "socket result error", "connect result error"

4. DATA TRANSMISSION (Every PERIOD seconds)
   ├─ Read sensor data (temperature, humidity, VOC, fan state)
   ├─ Package into payload (format: UNKNOWN)
   ├─ Execute AT+CIPSEND=0,<LENGTH>
   ├─ Send <BINARY_PAYLOAD>
   ├─ Listen for response on receive_data_thread
   └─ Error: "send error"

5. CONNECTION CYCLING (Every F_CLOSE_SOCK_PERIOD)
   ├─ Execute AT+CIPCLOSE=0
   ├─ Wait for close confirmation
   └─ Return to step 3

6. ERROR RECOVERY
   ├─ If connect fails: Retry or wait
   ├─ If send fails: Queue retry
   ├─ If network down: Restart WiFi
   └─ Reboot if persistent failure
```

---

## Key Findings

### ✅ Confirmed
- **Protocol:** TCP/IP over WiFi (using AT command interface)
- **Connection Type:** Persistent (timeout 7200s)
- **Data Period:** Configurable 10-300 seconds
- **Server Address:** Configurable (stored in NVS at `wifi_conf/server`)
- **Server Port:** Configurable 1-65535 (stored in NVS)
- **Threading:** Multi-threaded with dedicated send/receive threads
- **Error Handling:** Robust with retries and recovery

### ❓ Unknown (Proprietary)
- **Payload Format:** Binary, not documented
- **Message Structure:** Likely has header + data + checksum
- **Encryption:** Possibly encrypted (not confirmed)
- **Authentication:** Possibly device ID based
- **Server Response Format:** Unknown

### ⚠️ Implications for Home Assistant/ESPHome

The communication protocol is **proprietary and undocumented**. To replicate device behavior:

1. **Network Traffic Capture Required**
   - Use Wireshark/tcpdump to capture device-to-server traffic
   - Analyze packet payloads to reverse-engineer format
   
2. **Alternative: Use Official IntelliClima API**
   - Device registers with IntelliClima cloud backend
   - Communicate through official cloud API instead
   - Home Assistant IntelliClima integration already does this

3. **ESPHome Approach**
   - ESPHome cannot easily replicate the proprietary protocol
   - Best to keep device on WiFi for cloud sync
   - Use Home Assistant as bridge/interface

---

## Next Steps

1. **Capture Network Traffic**
   ```bash
   tcpdump -i wlan0 -w ecocomfort.pcap host <device-ip>
   # Monitor during device startup and periodic data sends
   # Analyze .pcap file with Wireshark
   ```

2. **Monitor Serial Debug Output**
   - Connect UART to GPIO 1/3 (115200 baud)
   - Capture boot messages and AT command flow

3. **Contact Manufacturer**
   - Request API documentation
   - Ask for protocol specification

4. **Community Reverse Engineering**
   - Check Home Assistant community
   - Look for existing protocol analysis

---

Generated: 2026-06-01
Device: Fantini Cosmi ECOCOMFORT 2 SMART v0.6.8
Framework: Zephyr RTOS
Communication: TCP/WiFi (AT Commands)
