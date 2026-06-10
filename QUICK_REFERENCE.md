# ECOCOMFORT 2 Quick Reference Card

## 📋 Project Status

✅ **Firmware fully reverse-engineered** (410 KB binary analyzed)
✅ **Protocol partially understood** (packet structure identified)
✅ **Mock server implemented** (ready for testing)
❓ **Real-world validation needed** (capture actual traffic)

---

## 🚀 Start Here (5 Minutes)

### 1. Run Mock Server
```bash
python3 ecocomfort2_mock_server.py --verbose
```

### 2. Connect Device via UART (GPIO 1/3 @ 115200)
```bash
picocom -b 115200 /dev/ttyUSB0
```

### 3. Send Configuration Command
```
Set wifi conf <SSID> <PASSWORD> <SERVER_IP> 8080 60
```

### 4. Verify Connection
Check server logs for:
```
[INFO] New connection from 192.168.1.50:54321
[INFO] Device registered: ecocomfort_device
```

---

## 📚 Documentation Map

| Task | File |
|------|------|
| **Understanding firmware** | `DETAILED_FIRMWARE_DECOMPILATION.md` |
| **Setting up server** | `LOCAL_SERVER_TESTING_GUIDE.md` |
| **Step-by-step guide** | `IMPLEMENTATION_GUIDE.md` |
| **Network capture** | `NETWORK_TRAFFIC_CAPTURE_GUIDE.md` |
| **Hardware pinouts** | `HARDWARE_PINOUT_ANALYSIS.md` |
| **UART commands** | `BLE_COMMAND_ANALYSIS.md` |
| **Existing solution** | `GITHUB_ESPHOME_INTEGRATION.md` |

---

## 🔧 Tools Available

| Tool | Purpose | Usage |
|------|---------|-------|
| **mock_server.py** | Device replacement | `python3 ecocomfort2_mock_server.py` |
| **packet_analyzer.py** | Protocol analysis | `python3 ecocomfort2_packet_analyzer.py --hex "<packet>"` |

---

## 🎯 Key Discoveries

### Device Hardware
- **Microcontroller:** ARM Cortex-M (Zephyr RTOS, not ESP-IDF)
- **Sensors:** SHTC3 (T/H), NTC thermistor, ALS (light), VOC sensor
- **Communication:** WiFi (AT commands), Bluetooth LE
- **Control:** PWM fan (GPIO 12), Relay logic (GPIO 15/16)

### Protocol Structure
```
Header (8 bytes)        Payload (0-1024 bytes)
FEED 01 001C 00000001   AA BB CC ... (sensor data)
│    │  │    │
│    │  │    └─ Sequence
│    │  └────── Payload length
│    └───────── Command type
└───────────── Magic (0xFEED)
```

### Command Types
| Hex | Direction | Name | Purpose |
|-----|-----------|------|---------|
| 0x01 | C→S | Device Info | Registration |
| 0x02 | C→S | Sensor Data | Temp, humidity, VOC, light |
| 0x03 | C→S | Status Report | Fan speed, uptime, signal |
| 0x04 | C→S | Ping | Keepalive |
| 0x80 | S→C | OK | Acknowledge |
| 0x81 | S→C | Command | Control instruction |
| 0x83 | S→C | Time Sync | Server timestamp |

---

## 📊 Expected Data

### Sensor Data (CMD_02)
```
Offset  Size  Field              Range
------  ----  -----              -----
0       2     Temperature        -50 to +50°C (1/100 resolution)
2       1     Humidity           0-100%
3       2     VOC                0-1000+ ppb
5       2     Ambient Light      0-4000 lux
```

### Status Report (CMD_03)
```
Offset  Size  Field              Range
------  ----  -----              -----
0       1     Fan Control        [0:3]=speed(0-5), [4:7]=mode(0=OFF,1=MANUAL,2=AUTO)
1       4     Uptime             seconds since boot
5       1     Signal Strength    -100 to 0 dBm
```

---

## 🔌 UART Connection

### Wiring
```
Device UART    USB-Adapter
GPIO 1 (TX)    RX (often white)
GPIO 3 (RX)    TX (often green)  
GND            GND (black)
```

### Connection Tools
```bash
# Option 1: picocom (simple)
picocom -b 115200 /dev/ttyUSB0

# Option 2: minicom (advanced)
minicom -D /dev/ttyUSB0 -b 115200

# Option 3: screen (minimal)
screen /dev/ttyUSB0 115200

# Option 4: cu (Unix)
cu -l /dev/ttyUSB0 -s 115200
```

### Shell Commands
```
Set wifi conf <SSID> <PSK> <IP> <PORT> <PERIOD>
  - Reconfigures WiFi and server settings
  - Device restarts after command
  
help
  - Lists available commands

version
  - Shows firmware version (should be 0.6.8)

status
  - Device status information
```

---

## 🌐 Network Redirection Methods

### Method 1: UART (Recommended)
- Pros: Direct, reliable, immediate
- Cons: Requires physical USB connection
- Time: 1-2 minutes

### Method 2: DNS Spoofing
- Pros: No hardware needed
- Cons: Requires router access or local DNS control
- Time: 5-10 minutes

### Method 3: Network Interception (iptables)
- Pros: Works transparently
- Cons: Complex setup, requires root
- Time: 10-15 minutes

---

## 📈 Packet Analysis

### Extract Packets from Log
```bash
grep "Received:" server.log | sed 's/.*Payload: //' > packets.hex
```

### Analyze Single Packet
```bash
python3 ecocomfort2_packet_analyzer.py --hex "FEED0102001C00000001..."
```

### Statistical Summary
```bash
python3 ecocomfort2_packet_analyzer.py --logs server.log --summary
```

---

## 🐛 Troubleshooting

| Issue | Check | Fix |
|-------|-------|-----|
| No connection | UART command sent correctly | Retry with explicit OK response |
| Connection drops | Server running | Restart server, check logs |
| Invalid packets | Baud rate 115200 | Try different USB adapter |
| No sensor data | PERIOD setting | Wait 60+ seconds |
| Can't access server | Firewall | Allow port 8080 |
| Device reboots loop | Invalid command | Check WiFi credentials |

---

## 📱 Device Status Fields

```json
{
  "device_id": "ecocomfort_device",
  "firmware_version": "0.6.8",
  "mac_address": "AA:BB:CC:DD:EE:FF",
  "online": true,
  "temperature": 22.5,
  "humidity": 55,
  "voc": 450,
  "ambient_light": 150,
  "fan_speed": 2,
  "fan_mode": "MANUAL",
  "uptime_seconds": 3600,
  "signal_strength": -45
}
```

---

## 🎓 Learning Path

**Beginner:** Read `IMPLEMENTATION_GUIDE.md` Phase 1
↓
**Intermediate:** Complete Phase 2-3 with traffic capture
↓
**Advanced:** Implement custom server features, MQTT bridge
↓
**Expert:** Build Home Assistant integration

---

## 🔗 Related Files

- **Firmware Analysis:** `FIRMWARE_STRINGS.txt` (47 KB), `GHIDRA_DISASSEMBLY.txt` (97 KB)
- **Hardware Specs:** `esphome_ecocomfort2_template.yaml`
- **References:** All markdown docs in repository root

---

## ⏱️ Expected Timeline

| Phase | Duration | Task |
|-------|----------|------|
| Setup | 5 min | Start server, redirect device |
| Verification | 10 min | Confirm connection works |
| Capture | 1-2 hours | Record real traffic |
| Analysis | 30 min | Verify protocol accuracy |
| Integration | 1-2 hours | Build automations/HA integration |

---

## 💡 Tips

- Start with verbose logging: `--verbose` flag
- Keep mock server running in `tmux` or `screen` for persistent access
- Use `tcpdump` to capture actual WiFi traffic: `sudo tcpdump -i wlan0 -w capture.pcap`
- Packet analyzer can be used interactively: `python3 ecocomfort2_packet_analyzer.py --interactive`
- Monitor server status: grep logs for `Status:` lines
- Device will retry connection if server unavailable (watch for backoff pattern)

---

## ❓ FAQ

**Q: What if I lose the UART connection?**
A: Device stores settings. Use DNS spoofing or iptables as fallback.

**Q: Can I run mock server on different machine?**
A: Yes, just ensure it's accessible (firewall, same subnet).

**Q: How often does device send data?**
A: Every PERIOD seconds (configurable 10-300s, default 60s).

**Q: What if I get "Permission denied" on /dev/ttyUSB0?**
A: Add user to dialout group: `sudo usermod -a -G dialout $USER`

**Q: Can I modify firmware instead?**
A: See `GITHUB_ESPHOME_INTEGRATION.md` for working ESPHome solution.

---

**Last Updated:** June 10, 2026
**Status:** Ready for field testing
**Next:** Run Phase 1, verify connection works

