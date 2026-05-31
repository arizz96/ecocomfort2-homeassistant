# ECOCOMFORT 2 Firmware Analysis & Reverse Engineering Guide

## Project Overview
Reverse engineering the Fantini Cosmi ECOCOMFORT 2 SMART ventilation unit to enable custom firmware development and local-only control without cloud dependency.

**Repository Branch:** `claude/ecocomfort-firmware-flashing-U9LOD`

---

## Device Information

### Device Details
- **Product:** Fantini Cosmi ASPIRVELO AIR ECOCOMFORT 2.0 SMART
- **Type:** Mechanical Ventilation Unit with Heat Recovery (MVHR)
- **Manufacturer:** Fantini Cosmi (Italian)
- **Firmware Version:** 0.6.8 (current)

### Hardware Architecture
- **Microcontroller:** Espressif ESP32 or ESP8266
  - **Evidence:** Device broadcasts WiFi SSID as "espressif" 
  - This is the standard SSID for Espressif chips during setup
- **RAM:** 512 kB (ESP32) or 160 kB (ESP8266)
- **Flash Storage:** Typically 4MB minimum
- **WiFi:** 802.11 b/g/n 2.4 GHz
- **Additional Protocols:** Bluetooth Low Energy (BLE), LoRa optional

### Device Connectivity
- **WiFi:** Primary communication with cloud
- **Bluetooth LE:** Local device-to-device communication (10m range)
- **Cloud API:** Requires internet connection
- **App Control:** IntelliClima+ application (iOS/Android/Huawei)

---

## Firmware Storage Locations

### Azure Blob Storage Domains
The firmware is hosted on Azure Blob Storage:
- `fantinicosmistorage.blob.core.windows.net`
- `blob.ams25prdstr04a.store.core.windows.net`

**Status:** These domains are access-restricted and blocked from standard environments.

### Likely Firmware URL Patterns
```
https://fantinicosmistorage.blob.core.windows.net/firmware/ecocomfort-0.6.8.bin
https://fantinicosmistorage.blob.core.windows.net/ecocomfort/0.6.8/firmware.bin
https://fantinicosmistorage.blob.core.windows.net/updates/ecocomfort-0.6.8.bin
```

---

## Reverse Engineering Plan

### Phase 1: APK Decompilation & Analysis ⭐ START HERE

#### Step 1: Download IntelliClima+ APK
```bash
# Option A: From APKPure (recommended)
wget "https://m.apkpure.com/download?id=com.fantinicosmispa.intelliclimasmart" \
  -O intelliclima.apk

# Option B: From APKCombo
wget "https://apkcombo.com/intelliclima/com.fantinicosmispa.intelliclimasmart/" \
  -O intelliclima.apk

# Option C: From Google Play (requires adb/Android device)
```

**APK Details:**
- Package Name: `com.fantinicosmispa.intelliclimasmart`
- Latest Versions: 3.9.25 - 3.10.39
- Requirements: Android 5.1+

#### Step 2: Install JADX Decompiler
```bash
# Download JADX
wget https://github.com/skylot/jadx/releases/download/v1.4.7/jadx-1.4.7.zip
unzip jadx-1.4.7.zip
export PATH=$PATH:$(pwd)/jadx/bin

# Or use apt (if available)
sudo apt-get install jadx

# Or use Docker
docker run -it -v $(pwd):/work skylot/jadx:latest jadx /work/intelliclima.apk
```

#### Step 3: Decompile the APK
```bash
jadx -d intelliclima-src intelliclima.apk
# This creates intelliclima-src/ directory with decompiled Java code
```

#### Step 4: Search for Critical Information
```bash
cd intelliclima-src

# Search for firmware URLs
echo "=== Firmware URLs ==="
grep -r "firmware" . | grep -i "url\|download\|blob\|storage"
grep -r "fantinicosmistorage" .
grep -r "blob.core.windows" .
grep -r "\.bin" . | grep -i url

# Search for API endpoints
echo "=== API Endpoints ==="
grep -r "api\." . | grep -i "fantini\|intelliclima"
grep -r "http" . | grep -E "(fantini|intelliclima|ecocomfort)" | head -20
grep -rE "https?://[a-zA-Z0-9\.\-]+" . | head -30

# Search for device communication protocol
echo "=== Communication Protocol ==="
grep -r "MQTT" .
grep -r "CoAP" .
grep -r "REST" .
grep -r "WebSocket" .

# Search for hardcoded credentials/keys
echo "=== Credentials & Keys ==="
grep -r "password\|token\|secret\|key\|auth" . | grep -v "keystore\|keytool" | head -20

# Search for device info/version endpoints
echo "=== Device Endpoints ==="
grep -r "version\|firmware\|device" . | grep -i "url\|endpoint\|path"

# Search for base URLs
echo "=== Base URLs ==="
grep -rE "https?://.*\.(com|io|net)" . | cut -d: -f2 | sort -u | head -20
```

#### Step 5: Key Files to Examine
Look for these important files in the decompiled source:
```
# API/Network communication
-r . -name "*Api*"
-r . -name "*Service*"
-r . -name "*Client*"
-r . -name "*Network*"
-r . -name "*Request*"
-r . -name "*Response*"

# Configuration
-r . -name "*Config*"
-r . -name "*Constants*"
-r . -name "*BuildConfig*"

# Device control
-r . -name "*Device*"
-r . -name "*Control*"
-r . -name "*Command*"

# OTA/Firmware update
-r . -name "*OTA*"
-r . -name "*Update*"
-r . -name "*Firmware*"
```

Example:
```bash
find intelliclima-src -name "*Api*" -o -name "*Config*" | head -20
```

---

### Phase 2: Firmware Extraction

#### Option A: Extract from Device via UART/Serial
```bash
# Install esptool.py
pip install esptool

# Connect device via USB/Serial (CH340 or similar)
# Put device in flash mode (GPIO0 to GND, then power on)

# Read flash contents
esptool.py -p /dev/ttyUSB0 read_flash 0x0 0x400000 ecocomfort_full_flash.bin

# Read only firmware partition (typical offsets)
esptool.py -p /dev/ttyUSB0 read_flash 0x10000 0x200000 ecocomfort_firmware.bin
```

#### Option B: Monitor WiFi Traffic
```bash
# Use Wireshark or tcpdump to capture firmware update traffic
# Run app update check and capture HTTPS traffic

# Monitor device WiFi connection
sudo tcpdump -i wlan0 -w ecocomfort_traffic.pcap host <device-ip>

# Decrypt HTTPS traffic using MITM proxy (Burp Suite, mitmproxy)
# This may reveal firmware download URLs
```

#### Option C: Extract from App Download Cache
```bash
# If the app downloads firmware locally
adb shell find /data/data/com.fantinicosmispa.intelliclimasmart -name "*.bin"
adb pull /data/... ecocomfort_firmware.bin
```

---

### Phase 3: Firmware Analysis

#### Step 1: Analyze Binary Structure
```bash
# Get file info
file ecocomfort_firmware.bin
hexdump -C ecocomfort_firmware.bin | head -50

# Search for ESP firmware magic numbers
hexdump -C ecocomfort_firmware.bin | grep "e9 05"  # ESP image magic

# Look for strings
strings ecocomfort_firmware.bin | head -50
strings ecocomfort_firmware.bin | grep -i "wifi\|mqtt\|http\|api"
```

#### Step 2: Disassembly
```bash
# Install Ghidra or IDA Free
# Use Espressif IDF tools
# Or use online tools like Godbolt

# Install capstone for disassembly
pip install capstone

# Basic disassembly
python3 << 'EOF'
from capstone import *
import struct

with open('ecocomfort_firmware.bin', 'rb') as f:
    code = f.read()

md = Cs(CS_ARCH_XTENSA, CS_MODE_XTENSA_ESP32)
for i, (addr, size, mnem, op_str) in enumerate(md.disasm_lite(code[:0x1000], 0)):
    print(f"0x{addr:x}: {mnem} {op_str}")
    if i > 100:
        break
EOF
```

#### Step 3: Extract Strings and Look for Protocols
```bash
strings ecocomfort_firmware.bin | grep -i "mqtt\|http\|coap\|websocket\|fantini\|intelliclima"

# Look for certificate/SSL data
strings ecocomfort_firmware.bin | grep -i "cert\|ca\.pem\|server\|port"

# Look for WiFi SSID prefixes
strings ecocomfort_firmware.bin | grep -i "ssid\|espressif"
```

---

## Expected Discoveries

### Firmware Update Mechanism
1. Device checks for updates on startup
2. Connects to Azure Blob Storage
3. Downloads firmware binary
4. Validates signature/checksum
5. Writes to flash and reboots

### Communication Protocol
Likely uses one of:
- **MQTT** (most common for IoT)
- **CoAP** (lightweight)
- **REST/HTTPS** (common with cloud)
- **Custom Binary Protocol**

### Cloud Services
- Fantini Cosmi cloud for device registration
- Likely hosted on Azure (based on storage domains)
- API probably requires authentication token

---

## Tools Needed

### APK Analysis
- **JADX** - Java decompiler (primary)
- **apktool** - Resource extraction
- **MobSF** - Automated security analysis
- **Frida** - Runtime instrumentation

### Firmware Analysis
- **esptool.py** - ESP firmware utility
- **Binwalk** - Binary analysis
- **Ghidra** - Disassembler/decompiler
- **IDA Free** - Interactive disassembly
- **Wireshark** - Network traffic analysis

### Installation
```bash
# Essential tools
pip install esptool jadx binwalk capstone

# Optional but recommended
sudo apt-get install ghidra wireshark tcpdump strings hexdump

# Docker alternative (recommended)
docker pull skylot/jadx:latest
docker pull espressif/idf:latest
```

---

## Security Considerations

⚠️ **This is for devices you own. Ensure:**
1. You have legal right to analyze the device
2. No unauthorized modification for distribution
3. Respect manufacturer's intellectual property
4. Use findings responsibly

✅ **Legitimate use cases:**
- Custom firmware for your own device
- Local-only control (privacy)
- Home Assistant integration
- Understanding device behavior
- Educational/research purposes

---

## Next Steps

1. **Download APK locally** in an unrestricted environment
2. **Run JADX decompilation** 
3. **Search for firmware URLs** using grep commands above
4. **Document all findings** in a new analysis file
5. **Extract firmware** using discovered URLs or esptool
6. **Analyze binary structure** to understand firmware format
7. **Create extraction script** for automated firmware updates
8. **Develop custom firmware** based on discovered protocol

---

## Files to Generate

After running analysis, create these files in the repository:

1. `FIRMWARE_URLS.txt` - Discovered firmware download URLs
2. `API_ENDPOINTS.txt` - Cloud API endpoints found
3. `PROTOCOL_ANALYSIS.md` - Communication protocol details
4. `APK_STRINGS.txt` - Interesting strings from APK
5. `FIRMWARE_ANALYSIS.md` - Binary firmware structure
6. `ecocomfort_firmware_0.6.8.bin` - Extracted firmware binary

---

## References

### Tools & Documentation
- [JADX GitHub](https://github.com/skylot/jadx)
- [esptool.py Documentation](https://docs.espressif.com/projects/esptool/en/latest/)
- [Espressif ESP32 Technical Reference](https://www.espressif.com/en/products/socs/esp32)
- [Android Reverse Engineering Guide](https://httptoolkit.com/blog/android-reverse-engineering/)

### Resources
- [Home Assistant IntelliClima Integration](https://www.home-assistant.io/integrations/intelliclima/)
- [MQTT Protocol](https://mqtt.org/)
- [ECOCOMFORT 2 Manual](https://www.fantinicosmi.it/wp-content/uploads/2023/07/ECOCOMFORT-2-SMART-istruzioni-uso-5680008C_NoVocal_EN.pdf)

---

## Status

- **Phase 1 - APK Analysis:** Pending (requires local execution)
- **Phase 2 - Firmware Extraction:** Pending
- **Phase 3 - Protocol Analysis:** Pending
- **Phase 4 - Custom Firmware:** Not started

Last Updated: 2026-05-31
