# ECOCOMFORT 2 Local Server Testing & Implementation

This guide explains how to use the mock server to test device communication and verify the proprietary protocol without cloud dependency.

---

## Quick Start

### 1. Start the Mock Server

```bash
# Basic usage (listens on 0.0.0.0:8080)
python3 ecocomfort2_mock_server.py

# Verbose mode (shows all packet details)
python3 ecocomfort2_mock_server.py --verbose

# Custom host/port
python3 ecocomfort2_mock_server.py --host 192.168.1.100 --port 8888
```

### 2. Redirect Device to Local Server

#### Method A: UART Shell Command (Recommended)
Connect via USB-to-Serial and send:
```
Set wifi conf <SSID> <PASSWORD> <SERVER_IP> 8080 60
```

Example:
```
Set wifi conf MyNetwork MyPassword 192.168.1.100 8080 60
```

The parameters mean:
- `MyNetwork` - WiFi SSID (your router)
- `MyPassword` - WiFi password
- `192.168.1.100` - Your local server IP
- `8080` - Server port
- `60` - Data transmission period (seconds)

#### Method B: DNS Spoofing
Modify your router's DNS or `/etc/hosts`:
```bash
# Linux/Mac: add to /etc/hosts
192.168.1.100 api.fantinicosmispa.com
192.168.1.100 fantinicosmistorage.blob.core.windows.net
```

Then restart the device to pick up DNS changes.

#### Method C: Network Interception
Use iptables on your gateway:
```bash
# Redirect all traffic meant for original server to local mock
sudo iptables -t nat -A PREROUTING -p tcp -d <ORIGINAL_IP> --dport 8080 -j DNAT --to 192.168.1.100:8080
```

---

## Testing the Connection

### 1. Monitor Server Logs

```bash
# Start server with verbose logging in one terminal
python3 ecocomfort2_mock_server.py --verbose

# Output will show:
# - Device connections
# - Received packets (hex)
# - Parsed sensor data
# - Fan status updates
# - Response acknowledgments
```

### 2. Check Device Status

```bash
# In another terminal, you can check status via Python
python3 << 'EOF'
import socket
import struct
import time

# Connect to mock server
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('localhost', 8080))

# Send a ping packet
magic = 0xFEED
cmd = 0x04  # PING
payload_len = 0
seq = 1

packet = struct.pack('>HHHI', magic, cmd, payload_len, seq)
s.sendall(packet)

# Receive response
response = s.recv(1024)
print(f"Received: {response.hex()}")
s.close()
EOF
```

---

## Protocol Packet Structure (Estimated)

Based on firmware analysis, packets follow this format:

### Header (8 bytes)
```
Offset  Size  Field           Value
------  ----  -----           -----
0       2     Magic           0xFEED
2       2     Command/Type    0x01-0xFF
4       2     Payload Length  0-1024
6       2     Sequence        0-65535
```

### Command Types (Client → Server)

| Code | Name | Description |
|------|------|-------------|
| 0x01 | Device Info | Device registration/identification |
| 0x02 | Sensor Data | Environmental sensor readings |
| 0x03 | Status Report | Fan status, uptime, signal |
| 0x04 | Ping | Keep-alive heartbeat |
| 0x05 | ACK | Packet acknowledgment |

### Response Types (Server → Client)

| Code | Name | Purpose |
|------|------|---------|
| 0x80 | OK | Command accepted |
| 0x81 | Command | Server command to device |
| 0x82 | Config | Configuration update |
| 0x83 | Time Sync | Server timestamp |
| 0x84 | Firmware Update | OTA update directive |
| 0xFF | Error | Error response |

---

## Payload Structures (Estimated)

### CMD_DEVICE_INFO (0x01) - Device Registration
**Request Payload:**
```
Offset  Size  Field           Example
------  ----  -----           -------
0       6     MAC Address     AA:BB:CC:DD:EE:FF
6       16    Device ID       "ECOCOMFORT2"
22      4     Firmware Ver    0.6.8
```

**Response Payload:**
```
0       4     Server Time     unix timestamp
```

### CMD_SENSOR_DATA (0x02) - Environmental Data
**Request Payload:**
```
Offset  Size  Field           Resolution
------  ----  -----           ----------
0       2     Temperature     1/100 °C (signed)
2       1     Humidity        0-100 %
3       2     VOC             ppb (parts per billion)
5       2     Ambient Light   lux
7       1     Flags           reserved
```

**Response Payload:**
```
0       1     Command Count   0=no commands, N=commands follow
1..     N     Command Data    if any
```

### CMD_STATUS_REPORT (0x03) - Device Status
**Request Payload:**
```
Offset  Size  Field           Bits
------  ----  -----           ----
0       1     Fan Control     [0:3]=speed(0-5), [4:7]=mode(0-2)
1       4     Uptime Seconds  unix seconds since boot
5       1     Signal Strength -100 to 0 dBm (signed)
6       1     Flags           reserved
```

**Response Payload:**
```
0       4     Server Time     unix timestamp
4       1     Command Count
5..     N     Command Data
```

---

## Capturing Real Traffic

### 1. Tcpdump Capture

```bash
# Capture all traffic to/from mock server
sudo tcpdump -i any -w ecocomfort_traffic.pcap host 192.168.1.100

# Display in real-time
sudo tcpdump -i any -A host 192.168.1.100 | grep -E "^[0-9a-f]|FEED"
```

### 2. Wireshark Analysis

```bash
# Open captured traffic
wireshark ecocomfort_traffic.pcap

# Filter for ECOCOMFORT traffic
tcp.port == 8080

# Export packet hex for analysis
# Right-click packet → Copy → Bytes (Hex)
```

### 3. Server Log Parsing

The mock server outputs all received packets in hex format:
```
2026-06-10 12:34:56 [DEBUG] [192.168.1.50:54321] Received: magic=0xFEED, cmd=0x01, len=28, seq=1
```

Extract hex packets:
```bash
python3 ecocomfort2_mock_server.py --verbose 2>&1 | grep "Received:" | \
  sed 's/.*Received: //' > packet_log.txt
```

---

## Protocol Reverse Engineering Process

### Phase 1: Establish Connection
1. Device connects to server on port 8080
2. Server logs connection with client IP:port
3. Device sends CMD_DEVICE_INFO (0x01)
4. Server responds with 0x80 OK + server timestamp

### Phase 2: Heartbeat & Keepalive
1. Device sends CMD_PING (0x04) every ~30 seconds
2. Server responds with 0x80 OK
3. Connection maintained as long as device is running

### Phase 3: Data Transmission
1. Every PERIOD seconds (configurable 10-300s):
   - Device sends CMD_SENSOR_DATA (0x02) with environmental readings
   - Device sends CMD_STATUS_REPORT (0x03) with fan status
2. Server acknowledges with 0x80 OK
3. Server may send 0x81 Command if action needed

### Phase 4: Command Processing
Server can send commands:
- 0x81 Command: Change fan speed/mode
- 0x82 Config: Update configuration parameters
- 0x83 Time Sync: Keep device time synchronized
- 0x84 Firmware Update: Initiate OTA update

---

## Improving Protocol Accuracy

### 1. Packet Collection
```bash
# Run for extended period and save all packets
timeout 3600 python3 ecocomfort2_mock_server.py --verbose 2>&1 | \
  tee extended_capture.log
```

### 2. Statistical Analysis
```python
import re
from collections import Counter

with open('extended_capture.log') as f:
    packets = re.findall(r'Received: magic=0x(.*?),', f.read())
    
# Analyze packet types
cmd_types = [int(p.split(',')[1].strip().split('=')[1], 16) for p in packets]
print("Command frequency:", Counter(cmd_types))

# Analyze payload sizes
payload_sizes = [int(p.split(',')[2].strip().split('=')[1]) for p in packets]
print("Payload size range:", min(payload_sizes), "-", max(payload_sizes))
```

### 3. Live Packet Inspection
Modify `ecocomfort2_mock_server.py` to dump raw payloads:
```python
# In process_command()
logger.info(f"Raw payload: {payload.hex()}")
```

Then analyze hexdumps to reverse-engineer exact packet format.

---

## Building a Complete Mock

Once protocol is verified, enhance the server with:

```python
# Add to ecocomfort2_mock_server.py

class EnhancedMockServer(ECOCOMFORTMockServer):
    """Extended server with command generation"""
    
    def should_send_command(self, device_id: str) -> bool:
        """Determine if server should send command to device"""
        # Example: adjust fan if CO2 high
        device = self.devices.get(device_id)
        if device and device.voc > 1000:
            return True
        return False
    
    def generate_command(self, device_id: str) -> bytes:
        """Generate server command based on device state"""
        device = self.devices[device_id]
        
        # Example: increase fan speed if VOC high
        if device.voc > 1000:
            fan_speed = min(5, device.fan_speed + 1)
            fan_mode = 1  # MANUAL
            return struct.pack('BB', (fan_mode << 4) | fan_speed, 0)
        
        return b'\x00'  # No command
```

---

## Home Assistant Integration

Once local mock is working:

1. Stop cloud communication by redirecting to local server
2. Build Home Assistant integration based on captured protocol
3. Create MQTT bridge or native integration
4. Reference: `GITHUB_ESPHOME_INTEGRATION.md` for existing BLE solution

---

## Troubleshooting

### Device Not Connecting
1. Verify IP address is correct: `ifconfig` or `ipconfig`
2. Check firewall isn't blocking port 8080
3. Verify UART command was accepted (should echo back)
4. Check device logs via UART: connect at 115200 baud

### Connection Drops
1. Increase PERIOD setting: higher values = less frequent connects
2. Check network stability: `ping` the server
3. Monitor logs for timeout errors
4. Verify port forwarding if server is on different machine

### Invalid Packet Errors
1. Ensure device received UART command (look for OK response)
2. Wait 10-30 seconds for device to reconnect to new server
3. Check server logs show connection attempt
4. Verify mock server is running on correct port

### Protocol Mismatch
1. Capture actual traffic with tcpdump
2. Compare against expected packet format
3. Update `DETAILED_FIRMWARE_DECOMPILATION.md` with findings
4. Modify payload parsing in mock server

---

## Next Steps

1. **Start Server**: Run mock server and verify it's accessible
2. **Configure Device**: Send UART command to redirect to local server
3. **Monitor Connection**: Watch logs for device packets
4. **Capture Traffic**: Record 1-2 hours of normal operation
5. **Analyze Patterns**: Identify repeating packet structures
6. **Build Documentation**: Update protocol analysis with findings
7. **Create Integration**: Build Home Assistant/automation control

---

## References

- `DETAILED_FIRMWARE_DECOMPILATION.md` - Firmware architecture
- `FIRMWARE_COMMUNICATION_PROTOCOL.md` - AT command interface
- `BLE_COMMAND_ANALYSIS.md` - UART shell commands
- `NETWORK_TRAFFIC_CAPTURE_GUIDE.md` - Traffic analysis methodology

