# ECOCOMFORT 2 Network Traffic Capture & Analysis Guide

## Objective
Capture and analyze the communication between ECOCOMFORT 2 and its cloud server to understand the protocol and build a local server mock.

---

## Phase 1: Network Traffic Capture

### Setup Requirements
- Device with network access (Linux/Mac/Windows)
- tcpdump or Wireshark installed
- ECOCOMFORT 2 on same network
- Device IP address known

### Method 1: tcpdump (Headless/SSH)

**Capture all traffic from device:**
```bash
# Find device IP first (optional):
nmap -sn 192.168.1.0/24  # or arp-scan

# Capture traffic to/from device
sudo tcpdump -i eth0 -w ecocomfort.pcap host 192.168.1.100
# Ctrl+C to stop

# Or capture specific protocol:
sudo tcpdump -i eth0 -w ecocomfort_tcp.pcap -n "host 192.168.1.100 and tcp port 8080"
```

**Monitor DNS queries (to find server):**
```bash
sudo tcpdump -i eth0 -w ecocomfort_dns.pcap -n "host 192.168.1.100 and udp port 53"
# Device will try to resolve server hostname
```

**Real-time monitoring:**
```bash
sudo tcpdump -i eth0 -n "host 192.168.1.100 and tcp" | tee ecocomfort.log
```

### Method 2: Wireshark (GUI)

**Steps:**
1. Open Wireshark
2. Select network interface
3. Click "Start" to begin capture
4. Let device operate for 5-10 minutes
5. Stop capture
6. Apply filter: `ip.addr == 192.168.1.100`
7. Save as ecocomfort.pcap

### Method 3: Router-Level Capture

If device is accessible via SSH/telnet to router:
```bash
# On router with tcpdump
tcpdump -i br0 -w ecocomfort.pcap host 192.168.1.100
```

### What to Capture
**1. On Device Startup:**
- WiFi connection
- DNS queries (reveals server hostname)
- Initial TCP connection
- First data transmission

**2. During Normal Operation:**
- Periodic data sends (every 10-300 seconds)
- Any app interactions
- Server responses

**3. On Configuration Change:**
- If you change WiFi/server settings
- What data is transmitted differently

**Duration:** Capture for at least 5-10 minutes to see multiple data cycles

---

## Phase 2: Traffic Analysis

### Step 1: Open in Wireshark

```bash
wireshark ecocomfort.pcap
```

### Step 2: Extract DNS Information

**Find Server Hostname:**
1. Filter: `dns.flags.response == 1` (DNS responses)
2. Look for queries from device IP
3. Note the server IP and hostname

**Example Output:**
```
192.168.1.100 -> 8.8.8.8
Query: api.intelliclima.com
Response: 185.199.100.50
```

### Step 3: Identify Server IP and Port

**TCP Connections:**
1. Filter: `tcp.flags.syn == 1` (TCP SYN packets)
2. Look for connections FROM device IP
3. Note destination IP and port
4. Usually: `185.199.100.50:443` or `123.45.67.89:8080`

**Example Filter:**
```
tcp.stream == 0 and ip.src == 192.168.1.100
```

### Step 4: Extract Raw Data

**Export TCP Stream:**
1. Right-click on TCP packet
2. Select "Follow -> TCP Stream"
3. View as "Raw" mode
4. Copy hex data

**Save Specific Stream:**
```bash
# Use tshark (Wireshark CLI)
tshark -r ecocomfort.pcap -Y "tcp.stream==0" -T fields -e tcp.payload > stream_0.hex
```

### Step 5: Analyze Packet Structure

**Examine First Data Packet:**

```
00000000: 01 02 03 04 05 06 07 08 | 09 0a 0b 0c 0d 0e 0f 10
00000010: 11 12 13 14 15 16 17 18 | 19 1a 1b 1c 1d 1e 1f 20
00000020: ... (rest of payload)
```

**Look for patterns:**
- **Magic bytes:** First few bytes (e.g., 0x01 0x02 = header)
- **Device ID:** Likely 4-8 bytes (ECMF2-%08lx)
- **Length field:** 2-4 bytes indicating payload size
- **Data section:** Sensor values, fan state
- **Checksum/CRC:** Last 1-4 bytes

### Step 6: Identify Multiple Packet Types

**Capture several cycles and compare:**

**Packet 1 (Startup/Handshake):**
```
May be different format (auth/registration)
Likely shorter than data packets
```

**Packet 2-N (Periodic Data):**
```
Should be similar structure
Same length
Different data values (sensor readings change)
```

**Packet N (Server Response):**
```
Incoming data from server
May contain commands
Likely shorter than device-to-server packets
```

---

## Phase 3: Protocol Reverse Engineering

### Template Analysis

Based on firmware findings, likely structure:

```
┌─────────────────────────────────────────────────────────┐
│                  ECOCOMFORT 2 PACKET                    │
├─────────────────────────────────────────────────────────┤
│ Offset │ Size │ Field           │ Example               │
├─────────┼──────┼─────────────────┼───────────────────────┤
│ 0x00   │ 2    │ Magic/Header    │ 0x45 0x43 (EC)       │
│ 0x02   │ 2    │ Message Type    │ 0x00 0x01 (data)     │
│ 0x04   │ 2    │ Payload Length  │ 0x00 0x20 (32 bytes) │
│ 0x06   │ 4    │ Device ID       │ ECMF2-12345678      │
│ 0x0A   │ 4    │ Timestamp       │ Unix time            │
│ 0x0E   │ 1    │ Temperature     │ 0x18 (24°C)          │
│ 0x0F   │ 1    │ Humidity        │ 0x45 (69%)           │
│ 0x10   │ 1    │ Fan Speed       │ 0x02 (medium)        │
│ 0x11   │ 1    │ Fan Direction   │ 0x01 (in)            │
│ 0x12   │ 1    │ VOC Index       │ 0x50 (80)            │
│ 0x13   │ 1    │ Status Flags    │ 0xA5                 │
│ 0x14   │ 4    │ Reserved        │ 0x00 0x00 0x00 0x00  │
│ 0x18   │ 2    │ CRC16           │ 0xAB 0xCD            │
└─────────┴──────┴─────────────────┴───────────────────────┘
```

**To Verify Structure:**
1. Extract multiple packets
2. Look for constant bytes (header)
3. Identify length fields
4. Map changing values (temperatures, etc.)
5. Verify CRC matches data

### Identifying Sensor Values

**Temperature (from firmware):**
```
"Immission Temperature: %hd.%02hd"
"Emission Temperature: %hd.%02hd"
"Ambient Temperature: %hd.%02hd"
```
Likely: 2 bytes each, fixed-point (16.34 = 0x10 0x22)

**Humidity:**
```
"Relative Humidity: %hd.%02hd%%"
```
Likely: 1-2 bytes (0-100%)

**VOC:**
```
"VOC: %hu index"
```
Likely: 2 bytes unsigned

**Fan State:**
```
Speed: 0-4 (1 byte)
Direction: IN/OUT/NONE (1 byte)
```

### Server Response Analysis

**Commands likely include:**
- Fan speed change
- Operating mode change
- Settings update
- Firmware update trigger
- Keep-alive/heartbeat

**Response packet might be:**
```
┌──────┬──────┬────────────┐
│Type  │Length│ Data       │
├──────┼──────┼────────────┤
│ 0x80 │ 0x04 │ 0x01 0x02  │ <- Acknowledge
│ 0x81 │ 0x10 │ Fan cmd... │ <- Fan control
│ 0x82 │ 0x20 │ Settings..│ <- Configuration
│ 0xFE │ 0x02 │ 0x00 0x00  │ <- Heartbeat ACK
└──────┴──────┴────────────┘
```

---

## Phase 4: Building Local Server Mock

### Simple Python Mock Server

```python
#!/usr/bin/env python3
import socket
import struct
import time
from datetime import datetime

class EcocomfortServer:
    def __init__(self, host='0.0.0.0', port=443):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.host, self.port))
        self.server.listen(1)
        self.devices = {}
        
    def parse_packet(self, data):
        """Parse ECOCOMFORT 2 packet"""
        if len(data) < 6:
            return None
            
        # Adjust based on actual structure discovered
        magic = data[0:2]
        msg_type = struct.unpack('>H', data[2:4])[0]
        length = struct.unpack('>H', data[4:6])[0]
        
        return {
            'magic': magic,
            'type': msg_type,
            'length': length,
            'payload': data[6:6+length],
            'raw': data
        }
    
    def build_response(self, device_id, command_type=0xFE):
        """Build response packet"""
        # Simple heartbeat ACK
        response = struct.pack('>HHH', 
            0x4543,  # Magic "EC"
            command_type,  # Response type
            2  # Length
        )
        response += struct.pack('>H', 0x0000)  # Data
        return response
    
    def handle_client(self, client, addr):
        """Handle device connection"""
        print(f"[*] Connected: {addr}")
        device_id = None
        
        try:
            while True:
                data = client.recv(1024)
                if not data:
                    break
                
                # Log raw data
                print(f"[RX] {data.hex()}")
                print(f"[RX ASCII] {data}")
                
                # Parse packet
                pkt = self.parse_packet(data)
                if pkt:
                    print(f"  Magic: {pkt['magic'].hex()}")
                    print(f"  Type: 0x{pkt['type']:04x}")
                    print(f"  Length: {pkt['length']}")
                    print(f"  Payload: {pkt['payload'].hex()}")
                    
                    # Extract device ID if present
                    if pkt['type'] == 0x0001 and len(pkt['payload']) >= 4:
                        device_id = struct.unpack('>I', pkt['payload'][0:4])[0]
                        print(f"  Device ID: 0x{device_id:08x}")
                    
                    # Send response
                    response = self.build_response(device_id or 0)
                    client.send(response)
                    print(f"[TX] {response.hex()}")
                
        except Exception as e:
            print(f"[!] Error: {e}")
        finally:
            client.close()
            print(f"[-] Disconnected: {addr}")
    
    def run(self):
        """Start server"""
        print(f"[+] Starting mock server on {self.host}:{self.port}")
        try:
            while True:
                client, addr = self.server.accept()
                self.handle_client(client, addr)
        except KeyboardInterrupt:
            print("\n[*] Shutting down...")
        finally:
            self.server.close()

if __name__ == '__main__':
    server = EcocomfortServer(port=8080)
    server.run()
```

**Run it:**
```bash
python3 mock_server.py
```

### Redirect Device to Local Server

**Option 1: UART Command**
```bash
# Connect via UART (GPIO 1/3 @ 115200)
Set wifi conf MySSID MyPassword 192.168.1.100 8080 60
Get wifi conf
# Should show: SERVER=192.168.1.100, PORT=8080
```

**Option 2: DNS Spoofing**
```bash
# Edit /etc/hosts on your router:
185.199.100.50  api.intelliclima.com  # Redirect to your mock server IP
192.168.1.100   api.intelliclima.com  # Your local server
```

**Option 3: Network Redirection**
```bash
# iptables rule to redirect connections
sudo iptables -t nat -A PREROUTING -p tcp -d 185.199.100.50 --dport 443 -j DNAT --to-destination 192.168.1.100:8080
```

---

## Phase 5: Analyzing Captured Data

### Using Wireshark Features

**Export all packets:**
```bash
tshark -r ecocomfort.pcap -T fields -e tcp.stream -e tcp.payload > packets.txt
```

**Filter and extract specific streams:**
```bash
# Get all TCP streams from device
tshark -r ecocomfort.pcap -Y "ip.src == 192.168.1.100 and tcp" -T fields -e tcp.stream | sort -u

# Extract stream 0
tshark -r ecocomfort.pcap -Y "tcp.stream == 0" -T ek > stream_0.json
```

**Hexdump analysis:**
```bash
# Convert pcap to hex for offline analysis
tshark -r ecocomfort.pcap -T fields -e tcp.payload > payloads.hex
hexdump -C payloads.hex | less
```

---

## Phase 6: Testing Local Mock

### Startup Sequence

**Expected packets (in order):**
1. DNS query: `api.intelliclima.com` → 192.168.1.100
2. TCP SYN: Device → Server (port 8080)
3. Data packet 1: Device → Server (initialization/auth)
4. Response 1: Server → Device
5. Data packet 2: Device → Server (sensor data)
6. Response 2: Server → Device
7. Repeat every 60 seconds (or configured PERIOD)

**Verify with mock server logs:**
```
[+] Starting mock server on 0.0.0.0:8080
[*] Connected: 192.168.1.100:12345
[RX] 45 43 00 01 00 20 ...
  Magic: 4543
  Type: 0x0001
  Length: 32
  Device ID: 0x12345678
[TX] 45 43 00 FE 00 02 ...
[RX] 45 43 00 01 00 20 ...  # Next cycle
```

---

## Tools Reference

### Required Tools
```bash
# macOS
brew install wireshark tcpdump

# Ubuntu/Debian
sudo apt-get install wireshark tcpdump tshark

# Fedora/RHEL
sudo dnf install wireshark tcpdump

# Windows
# Download Wireshark + Npcap from wireshark.org
```

### Optional Tools
```bash
# Protocol analysis
pip install scapy  # For packet crafting

# Network monitoring
nmap, arp-scan  # Find device IP

# Hex editing
hexedit, xxd  # Analyze binary data
```

---

## Troubleshooting

### Device Not Sending Data
- Check WiFi connection: `Get wifi conf`
- Verify server settings: `Set wifi conf ...`
- Check firewall (allow inbound on 8080, 443)
- Check device period setting (PERIOD parameter)

### Cannot Capture Traffic
- Verify device IP: `arp -a | grep ecocomfort`
- Check interface: `ifconfig` or `ip addr`
- May need sudo/admin
- Try Wireshark if tcpdump fails

### Mock Server Not Receiving Data
- Check device redirection worked
- Verify device sent packets to correct IP
- Monitor with: `sudo tcpdump -i eth0 -n "port 8080"`
- Check firewall blocking port

---

## Summary

1. **Capture:** tcpdump/Wireshark (5-10 min)
2. **Analyze:** Extract streams, identify format
3. **Document:** Packet structure, types, values
4. **Mock:** Build local server that responds
5. **Test:** Redirect device to local server
6. **Replicate:** Implement full protocol

Generated: 2026-06-01
