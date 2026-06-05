# ECOCOMFORT 2 Server Hostname Analysis

## Finding: Server Address is NOT Hardcoded

**Status:** The server hostname/IP is **completely configurable** and **NOT stored in the firmware binary**.

### Evidence

1. **Firmware Analysis**
   - Only NTP server found: `time.google.com`
   - NO API/cloud server domains hardcoded
   - NO IP addresses for data transmission found

2. **Configuration Storage**
   - Server stored in NVS at key: `wifi_conf/server`
   - Port stored in NVS at key: `wifi_conf/port`
   - Both are loaded at runtime (not compiled in)
   - Configurable via command: `Set wifi conf (param: SSID PSK SERVER PORT[1..65535] PERIOD[10..300])`

3. **Inference from Code**
   - Uses `AT+CIPSTART=0,"TCP","%s",%d,7200` format
   - The `%s` for SERVER is filled from configuration variable
   - Not a hardcoded constant

### How Device Gets Its Server Address

1. **During Setup (IntelliClima+ App)**
   - User scans device QR code or MAC address
   - IntelliClima+ app registers device with cloud
   - Cloud returns server address/endpoint
   - App sends server info to device via Bluetooth LE
   - Device stores in NVS storage

2. **Default Factory Configuration**
   - Unknown (firmware doesn't contain default)
   - Likely set during manufacturing
   - Could contact manufacturer for default values

3. **Runtime Configuration**
   - Can be changed via shell command: `Set wifi conf ...`
   - Can be changed via Bluetooth LE (from app)
   - Changes persist in NVS

### How to Discover the Server Address

**Option 1: Monitor Device on Your Network** ⭐ RECOMMENDED
```bash
# Capture DNS queries and traffic
tcpdump -i wlan0 -n 'udp port 53 or tcp port 80 or tcp port 443 or tcp port 8080' | grep <device-ip>

# Or use nmap
nmap -sV <device-ip>

# Or monitor network traffic
wireshark # Filter by device IP
```

**Option 2: Read Device Configuration**
```bash
# If you have UART/serial access (GPIO 1/3 @ 115200)
# Connect and monitor boot sequence
# Look for AT+CIPSTART command output showing the server

# Or if you can access NVS storage
# Extract NVS partition from device
# Parse key: wifi_conf/server
```

**Option 3: Analyze IntelliClima+ App**
```bash
# Decompile APK to find server endpoints
# Search for API URLs in decompiled code
# Check network requests in app traffic

# Or reverse-engineer API from app usage
# Monitor what server URLs app connects to
```

**Option 4: Contact Manufacturer**
- Email: supportotecnico@aspira.it
- Phone: +39 02 95682278
- Ask for: "Default server hostname for ECOCOMFORT 2.0 firmware 0.6.8"
- Or: "IntelliClima API documentation"

### Known Information About Fantini Cosmi Infrastructure

From earlier research:
- **Firmware hosting:** Azure Blob Storage
  - `fantinicosmistorage.blob.core.windows.net`
  - `blob.ams25prdstr04a.store.core.windows.net`
  
- **Cloud infrastructure:** Likely Azure-based
- **API integration:** IntelliClima+ cloud service
- **Status:** Proprietary, no public API documentation

### Inference: Likely Server Details

Based on device design patterns:

```
Protocol: TCP
Port: 8000-8080 or 443 (HTTPS likely)
Server: Could be:
  - intelliclima.fantinicosmispa.it
  - api.intelliclima.com
  - cloud.ecocomfort.io
  - mqtt.intelliclima.com (for MQTT)
  - Or Azure hosted: *.blob.core.windows.net
```

### What This Means for ESPHome

1. **Cloud Server Address Cannot be Determined From Firmware Alone**
   - Requires network traffic capture OR
   - App decompilation OR
   - Device configuration access

2. **Alternative Approach**
   - Use official IntelliClima integration (Home Assistant)
   - Device works with cloud regardless of our knowledge
   - Don't need to replicate the server address

3. **If You Want Local-Only Control**
   - You MUST capture network traffic first
   - Identify the actual server address
   - Understand the proprietary protocol
   - Then replicate or replace with ESPHome

### Next Action Items

1. **Network Traffic Capture (Easiest)**
   ```bash
   # Monitor device during normal operation
   tcpdump -i wlan0 -w ecocomfort_traffic.pcap host <device-ip>
   # Analyze with Wireshark to find actual server IP/hostname
   ```

2. **Check Your IntelliClima App Activity**
   - Look at app settings for any server information
   - Check "About" or "Status" screens
   - May show server address or connection status

3. **Device Terminal Access**
   - If you can connect via UART
   - Run: `Get wifi conf`
   - Should display current SERVER and PORT values

---

**Conclusion:** The server hostname is configuration-driven and must be discovered through network traffic analysis or device configuration access.

Generated: 2026-06-01
