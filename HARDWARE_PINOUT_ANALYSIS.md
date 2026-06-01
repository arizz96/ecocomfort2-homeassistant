# ECOCOMFORT 2 Hardware & Pinout Analysis

## Identified Hardware Components

### Microcontroller
- **Chip:** ESP32 (confirmed in firmware strings)
- **Firmware Framework:** Zephyr RTOS
- **Flash Size:** 4MB+ (typical for ESP32)
- **RAM:** 512 KB available for RTOS

### Sensors

#### 1. **SHTC3 Temperature & Humidity Sensor**
- **Type:** Digital I2C sensor
- **I2C Address:** 0x70 (7-bit)
- **Functions:** 
  - Temperature measurement (immission/emission)
  - Relative humidity measurement
  - High accuracy (±0.2°C, ±1.5% RH)
- **Connection:** I2C bus (I2C@40003000)

#### 2. **NTC Thermistor (Temperature)**
- **Connection:** ADC input (Analog-to-Digital Converter)
- **Purpose:** Secondary/backup temperature measurement
- **Resolution:** ADC configuration mentions specific gain/reference settings

#### 3. **ALS (Ambient Light Sensor)**
- **Purpose:** Light/daylight detection
- **Function:** Likely helps with automatic day/night cycle detection

#### 4. **VOC (Volatile Organic Compounds) Sensor**
- **Output:** VOC index value
- **Purpose:** Air quality monitoring for automatic ventilation adjustment

### Fan Control

**Fan Configuration:**
- **Bidirectional:** Can operate in BOTH directions
  - Direction: IN (supply air)
  - Direction: OUT (exhaust air)
  - Direction: NONE (off)

**Fan Speed Levels:**
- NIGHT (lowest, quietest)
- LOW
- MEDIUM
- HIGH
- BOOST (maximum)

**Control Method:** Likely PWM (Pulse Width Modulation) on GPIO pins

### Communication Interfaces

| Interface | Details | Usage |
|-----------|---------|-------|
| **WiFi** | 802.11 b/g/n 2.4 GHz | Cloud communication, app control |
| **Bluetooth LE** | 10m range | Local device pairing, multi-device control |
| **I2C** | I2C@40003000 | Sensor communication (SHTC3@0x70) |
| **UART** | uart@40028000, uart@40002000 | Serial communication, debugging |
| **ADC** | adc@40007000 | Analog sensor inputs (NTC, etc.) |
| **GPIO** | gpio@50000300, gpio@50000000 | Fan control, relay control, digital I/O |

### Operating Modes

- **Automatic Cycle:** Self-adjusting based on sensor readings
- **Free Cooling:** Uses outdoor temperature/humidity
- **Self-Driving Slave:** Controlled by master unit (multi-zone)
- **Manual:** Fixed speed/direction
- **Boost:** High-speed operation on demand
- **Extra Cycles:** Periodic operation for air circulation

---

## Missing Information: Physical Pinout

Unfortunately, **the exact GPIO pinout is not available** from firmware analysis because:

1. ✅ **Can be extracted:** By opening the device and tracing PCB
2. ✅ **Can be discovered:** Using JTAG/SWD debugger
3. ✅ **Can be inferred:** Through dynamic testing (toggling GPIO pins)
4. ❌ **NOT in firmware:** Zephyr device tree configuration (not included in binary)

**Likely GPIO Functions:**
- GPIO pins for PWM fan speed control (2-4 pins)
- GPIO pins for fan direction relay (1-2 pins)
- GPIO pins for status/indication LEDs (optional)
- I2C pins: SDA, SCL (hardware I2C)
- UART pins: TX, RX (debugging)

---

## ESPHome Conversion Feasibility

### ✅ Possible
- **Hardware Base:** ESP32 is fully ESPHome-compatible
- **Sensors:** SHTC3, ALS, VOC sensors have ESPHome components
- **WiFi/BLE:** ESPHome supports both protocols
- **Fan PWM:** ESPHome has fan component with speed control

### ⚠️ Challenges
1. **Missing Pinout:** Don't know which GPIO controls what
2. **Custom Sensor Configuration:** VOC sensor specifics unknown
3. **Bidirectional Fan Control:** Need relay control logic
4. **Data Loss:** Original firmware features not easily replicated
5. **Hardware Teardown:** May need to open device to get pinout

### ❌ Not Reversible
- Once ESPHome is flashed, original Fantini firmware cannot be recovered
- No cloud control (unless you set up your own MQTT server)
- No official app support (must use ESPHome/Home Assistant)

---

## Steps to Enable ESPHome Support

### Phase 1: Hardware Identification (Required)
1. **Open device carefully** - Locate main PCB
2. **Take high-resolution photos** of PCB (both sides)
3. **Trace GPIO assignments:**
   - Fan speed PWM pin(s)
   - Fan direction control pin(s)
   - Relay control pins (if any)
   - LED indicator pins
   - I2C SDA/SCL confirmation
4. **Document any markings** on chips/components

### Phase 2: ESPHome Configuration
1. Create `ecocomfort2.yaml` for ESPHome
2. Define I2C bus for SHTC3 sensor
3. Configure PWM outputs for fan control
4. Map GPIO pins for all functions
5. Create fan entity with speed/direction control
6. Add sensor components (temperature, humidity, etc.)

### Phase 3: Testing & Tuning
1. Flash ESPHome firmware to ESP32
2. Test each GPIO individually
3. Calibrate sensor readings
4. Tune fan control logic
5. Integrate with Home Assistant

### Phase 4: Recovery (Optional)
1. Keep backup of original firmware
2. Document recovery procedure
3. Ability to reflash Fantini firmware if needed (if bootloader allows)

---

## Estimated GPIO Pinout (Educated Guess)

Based on common ESP32 ventilation controller layouts:

```
Possible Configuration:
- GPIO 12, 13, 14: Fan PWM speed control (1-3 channels)
- GPIO 15, 16: Fan direction relay control (coil+ / coil-)
- GPIO 21, 22: I2C (SDA, SCL)
- GPIO 1, 3: UART (TX, RX) - typically used for debugging
- GPIO 32, 33: ADC inputs for sensors
- GPIO 25, 26: Optional LED indicators

⚠️ THIS IS A GUESS - REQUIRES PHYSICAL VERIFICATION
```

---

## Recommendation

To proceed with ESPHome conversion:

1. **Obtain Device Schematic** (if available from manufacturer)
2. **Open Device Physically** - Trace GPIO connections
3. **Use Logic Analyzer** - Capture GPIO toggle patterns during normal operation
4. **Document Everything** - Create detailed pinout map
5. **Create ESPHome Config** - Once pinout is known

---

## Resources

- **SHTC3 Datasheet:** Temperature/Humidity I2C sensor
- **ESP32 Pinout:** https://www.espressif.com/en/products/devkits
- **ESPHome Fan Component:** https://esphome.io/components/fan/
- **ESPHome I2C:** https://esphome.io/components/i2c/

---

Generated: 2026-06-01
Device: Fantini Cosmi ECOCOMFORT 2 SMART v0.6.8
