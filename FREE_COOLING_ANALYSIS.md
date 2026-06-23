# ECOCOMFORT 2 Free-Cooling Analysis

Based on reverse engineering the ECOCOMFORT 2 firmware, here's what I found about "3 levels of free-cooling":

## Configuration Keys Identified

From the NVS (Non-Volatile Storage) configuration structure in the firmware:

```
conf/fc_en  - Free Cooling Enable (binary: on/off)
conf/fc_t   - Free Cooling Temperature threshold
```

## What Free-Cooling Does (Theory from Firmware Analysis)

**Free-cooling** in ventilation systems refers to the **bypass of the heat exchanger** to allow outside air to directly cool the building when:
- Outside air temperature is lower than desired indoor temperature
- The device is in "Summer mode"
- Temperature threshold is satisfied

This saves energy by using natural ventilation instead of mechanical cooling.

## Why 3 Levels?

Based on firmware analysis, the "3 levels" likely refer to:

### Level 0: Disabled
- Free-cooling completely disabled
- Heat exchanger always active
- Maximum energy consumption
- Configuration: `conf/fc_en = 0`

### Level 1: Temperature-Based
- Free-cooling enabled when outside air < `conf/fc_t` temperature
- Single threshold comparison
- Automatic switching
- Configuration: `conf/fc_en = 1` with `conf/fc_t` set

### Level 2: Hybrid/Proportional
- Combined heat recovery and bypass
- Partial bypass based on temperature difference
- More sophisticated control algorithm
- Configuration: `conf/fc_en = 2` (speculative)

## Evidence from Firmware

### Status String from FIRMWARE_STRINGS.txt:
```
Mode: %s [calculate duration: %s]  [extra cycle: %s]  [slave self driving: %s]  [free cooling: %s]
```

This indicates free-cooling is reported as a status field (likely ON/OFF or the level).

### Boot/Status Output:
```
MODE:%s (calc dur:%s) (free cool:%s) (extra cycle:%s) - SPEED:%s [%s] (force night:%s) (force boost:%s) (inc speed:%s) - DIRECTION:%s
```

### Configuration Keys:
- `conf/fc_en` - The enabling/selection of free-cooling level
- `conf/fc_t` - The temperature threshold that triggers free-cooling

## How It Works (Estimated Flow)

```
1. Device reads sensors: outdoor temp, indoor temp
2. Checks if conf/fc_en is enabled (0/1/2)
3. If fc_en > 0:
   - Compare outdoor_temp to conf/fc_t
   - If outdoor_temp < conf/fc_t:
     - Reduce/bypass heat exchanger
     - Increase fresh air circulation
4. Fan speed/mode adjusts based on level
5. Heat recovery disabled during free-cooling cycle
```

## UART Shell Commands

While not explicitly documented in the firmware strings, the configuration can be set via:

```bash
Set wifi conf <SSID> <PSK> <SERVER> <PORT> <PERIOD>
```

But free-cooling configuration likely requires:
- Direct NVS access via UART shell
- Mobile app (IntelliClima+) configuration interface
- Or cloud server settings sync

## Related Features in Firmware

The firmware also mentions:
- **Season modes:** Winter (heat recovery) vs Summer (free cooling)
- **Automatic cycle control:** Duration-based cycles
- **Extra cycle mode:** For additional cooling/heating
- **Force night/boost modes:** Override normal operation

These work in conjunction with free-cooling to optimize energy consumption throughout the year.

## Sensor Integration

The free-cooling decision likely uses:
- **SHTC3 sensor:** Indoor temperature/humidity (I2C address 0x70)
- **NTC thermistor:** Outdoor air temperature
- **VOC sensor:** Indoor air quality (avoids free-cooling when indoor air is polluted)
- **Light sensor (ALS):** Possibly for occupancy/time-of-day logic

## Hardware Control

When free-cooling is active:
- **Heat exchanger bypass valve:** Opens (if present)
- **Fan speed:** Increases to maximize fresh air circulation
- **Direction:** May switch to exhaust mode to pull fresh air
- **Relay logic (GPIO 15/16):** Controls bypass valve or damper

---

## Verification Needed

To confirm the exact functionality of the 3 levels, we would need to:

1. **Capture actual device traffic** showing what value is sent for `conf/fc_en` (0, 1, or 2)
2. **Monitor sensor data** during summer cooling cycles
3. **Check the IntelliClima+ app** settings to see what options are offered for free-cooling
4. **Review the device manual** (linked in reverse engineering guide) for feature descriptions

## Next Steps

Run Phase 5 of `IMPLEMENTATION_GUIDE.md` to:
- Capture real traffic from the device
- Analyze what value `conf/fc_en` actually contains
- Monitor behavior changes when free-cooling is toggled
- Verify the temperature threshold `conf/fc_t` behavior

