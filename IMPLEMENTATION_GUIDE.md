# ECOCOMFORT 2 Complete Implementation Guide

This guide provides step-by-step instructions for implementing local-only cloud-free operation of the ECOCOMFORT 2 device using the reverse-engineered protocol.

---

## Project Overview

**Goal:** Operate the ECOCOMFORT 2 ventilation device without cloud dependency, enabling local control and Home Assistant integration.

**Approach:** 
1. Reverse-engineer the proprietary device-to-server protocol
2. Build a mock server that understands this protocol
3. Redirect device to local server instead of cloud
4. Analyze actual traffic to verify protocol accuracy
5. Build integrations (Home Assistant, automations, etc.)

**Status:** Protocol partially reverse-engineered from firmware analysis. Ready for real-world testing.

---

## Available Documentation

| File | Purpose |
|------|---------|
| `DETAILED_FIRMWARE_DECOMPILATION.md` | Complete firmware architecture & threading |
| `FIRMWARE_COMMUNICATION_PROTOCOL.md` | AT command interface & WiFi module control |
| `HARDWARE_PINOUT_ANALYSIS.md` | GPIO mapping & sensor connections |
| `BLE_COMMAND_ANALYSIS.md` | UART shell commands & BLE protocol |
| `SERVER_HOSTNAME_ANALYSIS.md` | Server address storage & discovery |
| `NETWORK_TRAFFIC_CAPTURE_GUIDE.md` | Methodology for protocol analysis |
| `LOCAL_SERVER_TESTING_GUIDE.md` | Mock server usage & testing |
| `ecocomfort2_mock_server.py` | Working mock server implementation |
| `ecocomfort2_packet_analyzer.py` | Protocol packet analysis tool |

---

## Quick Start (5 minutes)

### Step 1: Prepare Your Environment

You need:
- Device with WiFi connectivity (Linux, macOS, Windows)
- ECOCOMFORT 2 device on same network
- USB-to-Serial adapter (optional, for UART access)
- Python 3.7+

### Step 2: Start the Mock Server

```bash
# Terminal 1: Run mock server
python3 ecocomfort2_mock_server.py --verbose
```

### Step 3: Redirect Device to Local Server

Connect to device via UART shell at **GPIO 1/3 @ 115200 baud**:

```bash
# Via USB-to-Serial adapter (e.g., /dev/ttyUSB0)
picocom -b 115200 /dev/ttyUSB0

# Or with screen
screen /dev/ttyUSB0 115200

# Or with minicom
minicom -D /dev/ttyUSB0 -b 115200
```

Once connected (you should see a shell prompt), send:

```
Set wifi conf MyNetwork MyPassword 192.168.1.100 8080 60
```

Where:
- `MyNetwork` = your WiFi SSID
- `MyPassword` = your WiFi password  
- `192.168.1.100` = your server's local IP address
- `8080` = server port
- `60` = data transmission period in seconds

The device should respond with `OK` and then restart WiFi connection.

### Step 4: Verify Connection

Check mock server output (Terminal 1):

```
2026-06-10 12:34:56 [INFO] New connection from 192.168.1.50:54321
2026-06-10 12:34:57 [INFO] Device registered: ecocomfort_device
2026-06-10 12:34:58 [INFO] [192.168.1.50:54321] Status: fan=2/5 (MANUAL), uptime=3600s, signal=-45dBm
```

✅ If you see these messages, the basic connection is working!

---

## Detailed Workflow

### Phase 1: Establish & Verify Connection (15-30 min)

#### 1.1 Prepare Mock Server
```bash
# Create a working directory
mkdir -p ~/ecocomfort-local
cd ~/ecocomfort-local

# Copy scripts
cp /path/to/ecocomfort2_mock_server.py .
cp /path/to/ecocomfort2_packet_analyzer.py .
```

#### 1.2 Configure Network Access
```bash
# Option A: Direct IP access
# Find your server IP
ip addr show  # Linux
ifconfig      # macOS

# Option B: Make server accessible from device network
# If on different subnet, enable port forwarding:
sudo iptables -t nat -A PREROUTING -p tcp --dport 8080 -j DNAT --to 192.168.1.100:8080
```

#### 1.3 Start Server with Logging
```bash
python3 ecocomfort2_mock_server.py --verbose 2>&1 | tee server.log
```

#### 1.4 Redirect Device
Connect via UART and send the WiFi configuration command (see Step 3 above).

#### 1.5 Validate Connection
```bash
# Server output should show:
# - "New connection from [DEVICE_IP]"
# - "Device registered"
# - Periodic sensor data and status reports

# You should see these within 30 seconds of sending the command
```

### Phase 2: Capture Real Traffic (1-2 hours)

#### 2.1 Start Network Capture
```bash
# Terminal 2: Capture all traffic to mock server
sudo tcpdump -i any -w ecocomfort_capture.pcap host 192.168.1.50
# (replace 192.168.1.50 with device IP from server logs)

# Alternative: Capture to file and analyze later
sudo tcpdump -i any -nn host 192.168.1.50 > ecocomfort_traffic.txt
```

#### 2.2 Let Device Run Normally
- Keep mock server running for 1-2 hours
- Let device send periodic data
- Trigger any manual controls if possible (change fan speed, etc.)

#### 2.3 Analyze Captured Traffic
```bash
# Stop tcpdump (Ctrl+C)

# Extract hex packets from server log
grep "Payload" server.log | sed 's/.*Payload: //' > packets.hex

# Analyze with packet analyzer
python3 ecocomfort2_packet_analyzer.py --hex "$(head -1 packets.hex)" --verbose

# Or batch analyze
python3 ecocomfort2_packet_analyzer.py --logs server.log --summary --detailed
```

### Phase 3: Verify Protocol Understanding (1-2 hours)

#### 3.1 Identify Patterns
```bash
# Look at packet frequencies
grep "Received:" server.log | grep "cmd=" | sed 's/.*cmd=//' | cut -d',' -f1 | sort | uniq -c

# Expected output:
#  42 0x02 (sensor data - frequent)
#  41 0x03 (status report - frequent)  
#   2 0x04 (ping - keepalive)
#   1 0x01 (device info - at startup)
```

#### 3.2 Check Payload Consistency
```bash
# Look for repeating payload patterns
grep "cmd=0x02" server.log | grep "Payload:" | sed 's/.*Payload: //' | sort | uniq -c | head -5

# If payloads are similar, protocol is stable
# If random, may need more data or different packet structure
```

#### 3.3 Update Mock Server
Based on findings, update `ecocomfort2_mock_server.py`:
- Adjust payload parsing structures
- Add any missing command types
- Improve error handling

### Phase 4: Implement Integration (Varies)

#### 4.1 Option A: Home Assistant MQTT Bridge
```python
# Create MQTT publisher from device data
import paho.mqtt.client as mqtt

class ECOCOMFORTToMQTT:
    def __init__(self, broker="localhost", device_id="ecocomfort"):
        self.mqtt = mqtt.Client(client_id=device_id)
        self.mqtt.connect(broker, 1883, 60)
        
    def publish_sensor_data(self, device_data):
        """Publish sensor readings to MQTT"""
        self.mqtt.publish(f"home/ecocomfort/temperature", device_data['temperature'])
        self.mqtt.publish(f"home/ecocomfort/humidity", device_data['humidity'])
        self.mqtt.publish(f"home/ecocomfort/voc", device_data['voc'])
```

#### 4.2 Option B: Home Assistant Integration
```yaml
# configuration.yaml
rest_command:
  ecocomfort_set_fan_speed:
    url: "http://localhost:8080/api/device/control"
    method: POST
    payload: '{"action": "set_fan_speed", "speed": {{ fan_speed }}}'

sensor:
  - platform: mqtt
    name: "ECOCOMFORT Temperature"
    state_topic: "home/ecocomfort/temperature"
    unit_of_measurement: "°C"
```

#### 4.3 Option C: Custom Home Assistant Component
See `GITHUB_ESPHOME_INTEGRATION.md` for working BLE-based solution.

---

## Tools Reference

### ecocomfort2_mock_server.py

**Purpose:** Accepts device connections and emulates cloud server

**Usage:**
```bash
# Basic
python3 ecocomfort2_mock_server.py

# With options
python3 ecocomfort2_mock_server.py --host 0.0.0.0 --port 8888 --verbose

# Keep running in background
nohup python3 ecocomfort2_mock_server.py > server.log 2>&1 &
```

**Features:**
- Accepts TCP connections from device
- Parses proprietary packet format
- Extracts sensor data (temperature, humidity, VOC, light)
- Tracks device status (fan speed, uptime, signal)
- Sends keepalive responses
- Extensible command system

**Output:**
```
2026-06-10 12:34:56 [INFO] New connection from 192.168.1.50:54321
2026-06-10 12:34:57 [INFO] Device registered: ecocomfort_device
2026-06-10 12:34:58 [DEBUG] [192.168.1.50:54321] Status: fan=2/5 (MANUAL), uptime=3600s, signal=-45dBm
```

### ecocomfort2_packet_analyzer.py

**Purpose:** Analyze and reverse-engineer captured network packets

**Usage:**
```bash
# Analyze single hex packet
python3 ecocomfort2_packet_analyzer.py --hex "FEED0102001C00000001AA..."

# Analyze server logs
python3 ecocomfort2_packet_analyzer.py --logs server.log --summary

# Interactive mode
python3 ecocomfort2_packet_analyzer.py --interactive

# Export to JSON
python3 ecocomfort2_packet_analyzer.py --logs server.log --export analysis.json
```

**Features:**
- Decodes proprietary packet format
- Extracts sensor readings
- Parses device status
- Identifies packet types
- Statistical analysis
- JSON export

---

## Expected Device Behavior

### Normal Operation Timeline

```
T=0s    Device connects to server
        Sends CMD_DEVICE_INFO (0x01) with MAC address
        Receives time sync response

T=10-60s Device sends periodic data:
        - CMD_SENSOR_DATA (0x02) with temperature, humidity, VOC, light
        - CMD_STATUS_REPORT (0x03) with fan status, uptime, signal

T=30s   Device sends PING (0x04) for keepalive

T=60s   Device repeats data transmission cycle

Ongoing Server may send:
        - CMD_CONTROL (0x81) to change fan speed
        - CONFIG_UPDATE (0x82) for parameter changes
        - TIME_SYNC (0x83) periodic time updates
```

### Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Device not connecting | Wrong IP/port | Verify UART command syntax |
| Connection drops after 30s | Timeout/keepalive failure | Check server is responding to PING |
| Invalid packet format | Protocol mismatch | Verify firmware version is 0.6.8 |
| No sensor data | Device not sending (0x02) | Wait 60+ seconds, check PERIOD setting |
| Server not accessible | Firewall blocking | `sudo ufw allow 8080` (Linux) |
| Can't connect via UART | Baud rate wrong | Verify 115200 baud, try different adapter |

---

## Advanced Usage

### Custom Server with Command Support

Extend the mock server to send commands back to device:

```python
# In ecocomfort2_mock_server.py, modify handle_sensor_data():

def handle_sensor_data(self, client_id: str, payload: bytes) -> Optional[bytes]:
    # ... existing parsing code ...
    
    # Check if fan should be adjusted
    if device.voc > 1000:  # VOC threshold
        # Send command to increase fan speed
        command_data = struct.pack('B', 3)  # Set fan to speed 3
        return self.build_packet(self.RSP_COMMAND, command_data, seq=0)
    
    return self.build_packet(self.RSP_OK, b'', seq=0)
```

### Persistent Data Logging

```bash
# Log all sensor data to CSV
python3 << 'EOF'
import json
import csv
import time

log_file = open('ecocomfort_data.csv', 'w', newline='')
writer = csv.DictWriter(log_file, fieldnames=['timestamp', 'temperature', 'humidity', 'voc', 'light', 'fan_speed'])
writer.writeheader()

# Parse server.log and write to CSV
with open('server.log', 'r') as f:
    for line in f:
        if "Status:" in line:
            # Parse and write to CSV
            pass
EOF
```

### Network Isolation & Testing

```bash
# Create isolated network for testing
sudo ip netns add ecocomfort-test
sudo ip link add veth-test type veth peer name veth-ns
sudo ip link set veth-ns netns ecocomfort-test
sudo ip addr add 192.168.99.1/24 dev veth-test
sudo ip netns exec ecocomfort-test ip addr add 192.168.99.2/24 dev veth-ns

# Start mock server in isolated namespace
sudo ip netns exec ecocomfort-test python3 ecocomfort2_mock_server.py
```

---

## Testing Checklist

- [ ] Mock server starts without errors
- [ ] Device successfully connects via UART
- [ ] Device receives UART command and reboots WiFi
- [ ] Server logs show "Device registered"
- [ ] Server logs show periodic sensor data
- [ ] Packet analyzer successfully parses packets
- [ ] Sensor readings make logical sense
- [ ] Fan status updates appear periodically
- [ ] Device remains connected for 1+ hours
- [ ] Traffic capture contains repeating patterns

---

## Next Steps

1. **Implement:** Start at Phase 1, verify connection works
2. **Analyze:** Run Phase 2 to capture real traffic
3. **Validate:** Complete Phase 3 to verify protocol
4. **Integrate:** Build Home Assistant integration (Phase 4)
5. **Automate:** Create rules for fan control
6. **Document:** Update protocol docs with findings

---

## References

- Complete reverse engineering analysis: `DETAILED_FIRMWARE_DECOMPILATION.md`
- Network analysis methodology: `NETWORK_TRAFFIC_CAPTURE_GUIDE.md`
- Existing working solution: `GITHUB_ESPHOME_INTEGRATION.md`
- UART shell commands: `BLE_COMMAND_ANALYSIS.md`

---

## Support

For issues, check the troubleshooting section above or review:
- `LOCAL_SERVER_TESTING_GUIDE.md` - Detailed server setup
- `FIRMWARE_COMMUNICATION_PROTOCOL.md` - Protocol documentation
- Server logs with `--verbose` flag for detailed debugging

