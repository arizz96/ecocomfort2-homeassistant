# ECOCOMFORT 2 Firmware v0.6.8 - Decompilation & Analysis Report

## Executive Summary

Successfully decompiled and analyzed the ECOCOMFORT 2 firmware binary using Ghidra disassembler. The firmware is an ARM Thumb instruction set compiled with the Zephyr RTOS framework.

**Key Statistics:**
- **Total Functions:** 2,749
- **Firmware Size:** 410 KB (compressed to 401 KB)
- **Architecture:** ARM/little-endian/32-bit v8 (ARMv8-A Cortex)
- **OS:** Zephyr Real-Time Operating System (not standard ESP-IDF)

## Decompilation Method

1. **Binary Format Conversion**: Raw firmware → ARM ELF header wrapper
2. **Disassembler**: Ghidra v11.0.3 (NSA reverse engineering tool)
3. **Processor**: ARM Cortex (Thumb instruction set)
4. **Analysis**: Automatic function discovery and control flow analysis

## Firmware Structure

### Largest Functions (Top 50)

The largest functions indicate core functionality:

| Address | Function | Size | Purpose (Inferred) |
|---------|----------|------|-------------------|
| 0x0003b5a0 | FUN_0003b5a0 | 2,552 bytes | Likely main processing loop |
| 0x00007fbc | FUN_00007fbc | 1,630 bytes | Major subsystem handler |
| 0x00034380 | FUN_00034380 | 1,278 bytes | Configuration/settings handler |
| 0x000115a0 | FUN_000115a0 | 1,224 bytes | Communication/protocol handler |
| 0x00008bd8 | FUN_00008bd8 | 1,198 bytes | Device control logic |

**Total of 2,749 functions identified** across the entire firmware, ranging from small utility functions to large processing routines.

## Known Strings & Configuration

From binary string extraction (see FIRMWARE_STRINGS.txt):

### Configuration Keys
- **WiFi:** `wifi_conf/{ssid,psk,server,port,period,active}`
- **Time:** `sntp/{name,port,timezone}`
- **Bluetooth:** `bt/{keys,id,name,cf,ccc,sc}`
- **Device:** `dev/{addr_0..addr_9}` (up to 10 devices)
- **Operations:** `oper/{mode,speed}`
- **Status:** `stat/{idx,flt_wrn_count}`

### Communication
- Time servers: `time.google.com`, 8.8.8.8, 4.4.4.4
- No hardcoded cloud URLs (configured at runtime)

### Device Features
- FIRMWARE_UPGRADE command with block transfers
- Multi-device support (master + up to 10 slaves)
- Weekly schedule profiles (prof/day_0 - prof/day_6)
- Environmental sensors: temperature, humidity, luminosity, VOC

## Limitations

1. **No Symbol Information** - Functions are auto-discovered, not explicitly named
2. **Optimized Code** - Compiler optimizations make some flow analysis difficult
3. **Runtime Configuration** - Server addresses loaded from NVS, not in binary
4. **No Debugging Symbols** - Standard production firmware without debug info

## Next Steps

To gain more insight:

1. **Correlate with APK** - Map app commands to firmware functions
2. **Monitor Network Traffic** - Capture device-to-server communication
3. **Dynamic Analysis** - Use device debugger or JTAG for runtime inspection
4. **Pattern Matching** - Compare against Zephyr OS source code patterns
5. **Function Signature Recognition** - Use Ghidra's function ID database

## Files Generated

- `GHIDRA_DISASSEMBLY.txt` - Complete function listing (97 KB)
- `FIRMWARE_STRINGS.txt` - All extracted strings (47 KB)
- `ecocomfort_firmware.elf` - Repackaged firmware as ARM ELF
- `FIRMWARE_ANALYSIS.md` - Static string analysis results

## Tools Used

- **Ghidra 11.0.3** - Disassembler and decompiler
- **Python 3** - Binary analysis and ELF header creation
- **Strings utility** - Static string extraction

---

Generated: 2026-06-01
Firmware Version: 0.6.8
Device: Fantini Cosmi ECOCOMFORT 2 SMART MVHR
