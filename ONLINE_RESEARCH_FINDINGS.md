# ECOCOMFORT 2 Online Research Findings

## Search Results Summary

### ✅ Found Resources

#### 1. **Official Documentation**
- **Manufacturer:** Fantini Cosmi (Italian HVAC company)
- **Product Line:** ASPIRVELO AIR ECOCOMFORT 2.0 SMART
- **Firmware Version Tested:** 0.6.8 (confirmed in code)
- **Manual Available:** Multiple sources (ManualsLib, manuals.plus, manufacturer PDF)

**Manual Access Points:**
- [ManualsLib - Full Manual](https://www.manualslib.com/manual/2525890/Aspira-Aspirvelo-Air-Ecocomfort-2-0-Smart-Series.html)
- [Manuals.plus](https://manuals.plus/aspira/smart-air-ecocomfort-2-0-manual)
- [Fantini Cosmi Official PDF](https://www.fantinicosmi.it/wp-content/uploads/2023/07/ECOCOMFORT-2-SMART-istruzioni-uso-5680008C_NoVocal_EN.pdf)

#### 2. **Home Assistant Integration**
- **IntelliClima Integration:** Official Home Assistant support for ECOCOMFORT 2.0
- **Status:** Cloud-based API (no local-only option in official integration)
- **API:** Reverse-engineered from IntelliClima+ app
- **Location:** https://www.home-assistant.io/integrations/intelliclima/

#### 3. **Third-Party Projects**
- **Homebridge Plugin:** [ruizmarc/homebridge-intelliclima](https://github.com/ruizmarc/homebridge-intelliclima)
  - Supports WiFi thermostats from Fantini Cosmi
  - Uses reverse-engineered IntelliClima API calls
  - Note: No official API provided by manufacturer

#### 4. **Community Discussions**
- Home Assistant Community Forum threads exist for ECOCOMFORT 2.0 configuration
- Limited discussion of hardware-level modifications

### ❌ NOT Found Online

Unfortunately, the following information is **not publicly available**:

1. **GPIO Pinout** - Not documented in any manual or online source
2. **Schematic Diagrams** - Not published by manufacturer
3. **PCB Layout** - Not available publicly
4. **Hardware Teardown Guides** - No iFixit or similar teardown
5. **WiFi Module Specifications** - Not detailed in documentation
6. **Detailed Hardware Architecture** - Only high-level description available

### 📋 Manual Contents (What IS Available)

The official ECOCOMFORT 2.0 SMART manual includes:
- Installation instructions
- IntelliClima+ app pairing procedures
- Operating modes: Automatic, Manual, Sleep, Off
- Advanced settings: Temperature offset, humidity threshold, free cooling, geolocation
- Filter maintenance procedures
- Electrical safety specifications
- Dimensions and mounting information

But **NO internal hardware or electronic schematic information**.

---

## Technical Details Confirmed from Manual

### Device Capabilities
- **Fan Speeds:** NIGHT, LOW, MEDIUM, HIGH, BOOST (matches our firmware analysis)
- **Operating Modes:** Automatic, Manual, Sleep, Off (matches firmware strings)
- **Sensors:** Temperature, Humidity, Air Quality monitoring (consistent with firmware)
- **Control Methods:** WiFi + Bluetooth LE (from firmware)
- **Heat Recovery:** Yes (MVHR - Mechanical Ventilation Heat Recovery)

### Network Features
- **WiFi:** 802.11 b/g/n 2.4 GHz
- **App:** IntelliClima+ (available on iOS, Android, Huawei AppGallery)
- **API:** Cloud-based (Azure hosted, as found in firmware)
- **Local Control:** Bluetooth LE support

---

## Recommendations for GPIO Pinout Discovery

Since the GPIO pinout is **not publicly available**, you have these options:

### Option 1: Contact Manufacturer ⭐ RECOMMENDED
**Contact Information:**
- Technical Support Email: supportotecnico@aspira.it
- Phone: +39 02 95682278
- Ask for: "Technical Documentation for WiFi Module" or "Hardware Specification Sheet"

### Option 2: Community Reverse Engineering
- Search niche forums (elektroda.com, smarthome.cz, etc.)
- Check Italian-language forums (device is from Italian manufacturer)
- Post in Home Assistant community asking for hardware info

### Option 3: Physical Inspection (DIY)
1. **Carefully open the device** - Document assembly process with photos
2. **Identify main PCB** - Take high-resolution photos (both sides)
3. **Trace connections:**
   - Fan PWM control lines (likely 1-3 GPIO)
   - Fan direction relay (likely 2 GPIO for coil control)
   - I2C bus (SDA/SCL to SHTC3 sensor)
   - Power/Ground reference points
4. **Use a multimeter** - Test GPIO voltage levels during fan operation
5. **Document findings** - Create detailed pinout map

### Option 4: Dynamic Analysis
With device access:
- Use oscilloscope to monitor GPIO signals during fan operation
- Use JTAG/SWD debugger (if accessible) to read firmware at runtime
- Monitor serial debug output via UART

---

## ESPHome Path Forward

Once GPIO pinout is confirmed, you can:

1. **Customize the ESPHome template** (already created in this repo)
2. **Flash ESPHome firmware** to the device
3. **Integrate with Home Assistant** locally (no cloud required)
4. **Full automation support** with Home Assistant automations
5. **Preserve original firmware** (optional, depends on bootloader)

---

## Risk Assessment

### ESPHome Conversion Risks
- **Irreversible** (original Fantini firmware cannot be recovered unless backed up)
- **No Official Support** - Flashing ESPHome voids any manufacturer warranty
- **Cloud Features Lost** - IntelliClima+ app will no longer work
- **Feature Loss** - Some advanced Fantini features may not be replicated
- **Testing Required** - All GPIO assignments must be verified before flashing

### Hardware Damage Risks
- **Opening Device** - Risk of damaging seals (may affect heat recovery efficiency)
- **Soldering Risk** - If GPIO lines need to be tapped directly
- **ESD Damage** - Risk to electronic components during handling

---

## Summary

The ECOCOMFORT 2 is well-documented for **installation and operation**, but there's **no public hardware documentation** available. The ESP32 WiFi module inside is custom-integrated and not separately documented.

**Best Path:** Contact Fantini Cosmi support for technical specifications, or plan for careful physical inspection of the device to map GPIO assignments.

---

Generated: 2026-06-01
Research Completed: Online sources thoroughly searched
