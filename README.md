# 🌬️ Ecocomfort 2.0 VMC — Home Assistant Integration

A native Home Assistant custom integration for **Intelliclima / Fantini Cosmi
Ecocomfort 2.0 Smart** decentralized heat-recovery ventilation units (VMC),
talking to them **directly over Bluetooth Low Energy** through Home Assistant's
own Bluetooth stack.

Each unit is a wall-mounted ventilator with a ceramic heat exchanger that
alternates between bringing fresh air in and extracting stale air, recovering
up to 90% of the heat.

> **A big thank you to [gledian/esphome-ecocomfort2](https://github.com/gledian/esphome-ecocomfort2).**
> This integration started as a port of that ESPHome package, and it wouldn't
> exist without its work: the BLE protocol it worked out is the foundation of
> everything here.

## Why this integration

- **Local control.** Home Assistant talks to the units directly, on your own
  network and radios.
- **No cloud dependency.** Nothing goes through the Intelliclima cloud, so the
  units keep working if the cloud or your internet connection is down.
- **Bluetooth is the only way to do it locally.** The units can't be
  controlled locally over Wi-Fi.
- **The logic lives in Home Assistant, not on a dedicated ESP32.** The ESPHome
  package runs the protocol on an ESP32 flashed for the job. This integration
  runs it inside Home Assistant and uses whatever Bluetooth adapters it already
  has: the host's own radio or any **connectable** Bluetooth proxy. A standard
  ESPHome `bluetooth_proxy` can serve these units and every other Bluetooth
  device in the house at the same time, with no unit-specific firmware.

**Tested** on real units (a main unit and its satellite) through an ESPHome
Bluetooth proxy.

**Version:** 0.1.0 · **Requires:** Home Assistant 2026.8 or newer

---

## Contents

- [Why this integration](#why-this-integration)
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Adding a unit](#adding-a-unit)
- [Pairing](#pairing)
- [Entities](#entities)
- [Controlling the unit](#controlling-the-unit)
- [How it works](#how-it-works)
- [Main and satellite units](#main-and-satellite-units)
- [Blueprints](#blueprints)
- [Migrating from the ESPHome package](#migrating-from-the-esphome-package)
- [Troubleshooting](#troubleshooting)
- [BLE protocol reference](#ble-protocol-reference)
- [Known limitations](#known-limitations)
- [Credits](#credits)

---

## Features

- 📡 **Direct BLE** through Home Assistant's Bluetooth stack: local adapter or
  connectable proxy, no custom firmware.
- 🔌 **UI setup** with automatic Bluetooth discovery.
- 🏠 **Fan entity**: on/off, 4 speeds (Sleep, Vel 1–3) and the In / Out /
  In/Out / Sensor / Auto modes.
- 🌡️ **Readings**: temperature, humidity and air quality (VOC).
- 🔍 **What the unit is actually doing**: running mode, running speed
  (including automatic changes in Sensor/Auto mode, Boost and Sleep) and
  current airflow direction.
- ❄️🔥 **Season** (Winter heat recovery / Summer) and **free cooling**.
- 📊 **Sensor-mode thresholds** for humidity, VOC and brightness, with the
  "advanced" one-step-up option.
- 🔧 **Calibration offsets** for temperature and humidity.
- 🕐 **Clock sync** from Home Assistant (hourly).
- 🧩 **One device per unit**, including main/satellite pairs.
- 🌍 **English and Italian** translations.
- 🛡️ **Robust polling**: short connections, tolerant of occasional failed
  polls, self-recovering, and never blocks Home Assistant startup.

## Requirements

- **Home Assistant 2026.8 or newer.**
  - The integration's brand images (icon/logo) are shown from 2026.3 onwards.
- **A Bluetooth adapter Home Assistant can connect with**, either:
  - the local Bluetooth radio of the Home Assistant host, or
  - a **connectable** Bluetooth proxy already set up in Home Assistant,
    e.g. ESPHome's `bluetooth_proxy` with `active: true`.
- **One or more Ecocomfort 2.0 Smart units** within Bluetooth range
  (roughly 10 m, fewer walls is better).

### Notes for ESPHome Bluetooth proxies

- **`active: true` is required.** A passive proxy only listens to
  advertisements and can't connect.
- **Pairing through a proxy needs ESPHome 2024.3.0 or newer** on the proxy.
  Older firmware can still connect and read, but can't pair if a unit
  requires it.
- **ESP32 proxies have few connection slots** (commonly 3). This integration
  only holds a connection for a few seconds per poll, but other Bluetooth
  integrations on the same proxy compete for the same slots.
- **A bond belongs to the adapter or proxy that made it.** If several proxies
  can reach a unit, Home Assistant may connect through any of them; see
  [Pairing](#pairing).

## Installation

### HACS (custom repository)

1. In HACS, open **⋮ → Custom repositories**.
2. Add `https://github.com/arizz96/ecocomfort2-homeassistant` with type
   **Integration**.
3. Install **Ecocomfort 2.0 VMC (BLE)** and restart Home Assistant.

### Manual

1. Copy `custom_components/ecocomfort2` into your Home Assistant
   `config/custom_components/` folder.
2. Restart Home Assistant.

## Adding a unit

1. Make sure the unit is powered and within range of a Bluetooth adapter or
   proxy.
2. Home Assistant **discovers** it and offers it under
   **Settings → Devices & Services**. Confirm to add it.
   - Discovery matches the unit's Bluetooth **service**, not its name. Many
     units don't advertise a name and show up only by their MAC address; both
     cases are found.
   - If it isn't offered automatically: **Add Integration → Ecocomfort 2.0 VMC**
     and pick it from the list of nearby units.
3. Repeat for each unit.

The entities appear right away and stay **unavailable until the first
successful poll**. That's usually within a minute: the first poll is spread out
over up to 30 seconds per unit so several units don't hit the same proxy at
once.

## Pairing

The units support Bluetooth pairing (bonding), but **Home Assistant doesn't
always need it**. The integration only asks to pair when the unit refuses a
read or a command because the link isn't encrypted. If everything reads and
works, no pairing happens.

When pairing is needed:

1. **Put the unit in pairing mode**: hold its button for about 5 seconds until
   the LED blinks. The window is short (roughly 30–60 seconds).
2. **Press `button.<device>_pair`** in Home Assistant while the LED blinks.
3. **Check the result:** the button reports an error in the UI if pairing
   failed. On success, the unit is read again over the paired link, so values
   that needed encryption show up right away.

How pairing behaves:

- **At most once per connection, never in a loop.** If an automatic attempt
  fails (usually because the unit wasn't in pairing mode), it's retried only
  after 10 minutes, not on every poll; meanwhile values that need encryption
  show as unknown. Pressing **Pair** tries again right away. If a unit refuses
  every read until it's paired, the log says so.
- **No unpairing first.** The Pair button doesn't clear an existing bond, like
  the original ESPHome package.
- **The phone app can coexist.** The Intelliclima app and Home Assistant can
  both be bonded, but a unit accepts a *new* bond only while in pairing mode.

## Entities

Entity IDs below use `<device>` for your device's name (for example
`ecmf2_0000abcd`).

### Controls

| Entity | What it does |
|---|---|
| `fan.<device>` | On/off, speed (25 / 50 / 75 / 100 %) and mode (In, Out, In/Out, Sensor, Auto) |
| `select.<device>_season` | Winter (heat recovery) or Summer |
| `select.<device>_free_cooling` | Off / Low / Medium / High (only effective in Summer) |
| `select.<device>_humidity_threshold` | Sensor-mode humidity threshold: Off / Low (55%) / Medium (60%) / High (65%) |
| `select.<device>_voc_threshold` | Sensor-mode air-quality threshold: Off / Low (250) / Medium (300) / High (350) |
| `select.<device>_luminosity_threshold` | Sensor-mode brightness threshold: Off / Low / Medium / High |
| `switch.<device>_humidity_advanced` | When the humidity threshold is exceeded: step up one speed (on) instead of boosting to maximum (off) |
| `switch.<device>_voc_advanced` | Same, for the air-quality threshold |
| `number.<device>_set_temp_offset` | Temperature calibration, −5 to +5 °C |
| `number.<device>_set_humidity_offset` | Humidity calibration, −5 to +5 % |
| `button.<device>_pair` | Pair with the unit (see [Pairing](#pairing)) |

### Readings

| Entity | What it shows |
|---|---|
| `sensor.<device>_temperature` | Indoor temperature (°C) |
| `sensor.<device>_humidity` | Indoor relative humidity (%) |
| `sensor.<device>_voc` | Air quality (VOC), see [below](#about-the-voc-reading) |

### Diagnostics

| Entity | What it shows |
|---|---|
| `sensor.<device>_actual_mode` | Mode the unit is running in right now: Off, In, Out, In/Out (heat recovery), Sensor, Auto |
| `sensor.<device>_actual_speed` | Speed the unit is running at right now, including automatic changes: Off, Sleep, Speed 1, Speed 2, Speed 3, Boost |
| `sensor.<device>_direction` | Current airflow: Intake or Exhaust (alternates in In/Out mode), Off while the unit is off |
| `sensor.<device>_role` | Standalone, Main unit or Satellite unit |
| `binary_sensor.<device>_connected` | Whether Home Assistant can reach the unit (see [How it works](#how-it-works)) |

Firmware version and serial number also appear on the device page.

#### About the VOC reading

The unit reports air quality on **its own scale**, which the manufacturer
labels "ppm": the manual's VOC thresholds are 250 / 300 / 350 ppm, and the
Intelliclima app graphs the value as "quality". It isn't a physical
concentration (a typical reading of ~220 would be an implausible 220 ppm of
VOCs indoors). So the sensor shows the number with the manufacturer's "ppm"
label and no VOC device class, and Home Assistant doesn't convert it.
**Compare it with the thresholds:** below 250 means the unit considers the air
fine.

## Controlling the unit

### Speeds

| Fan % | Unit speed | Airflow | Power |
|---|---|---|---|
| 25 % | Sleep | 8.0 m³/h | 2.0 W |
| 50 % | Vel 1 | 20.5 m³/h | 2.5 W |
| 75 % | Vel 2 | 35.0 m³/h | 4.0 W |
| 100 % | Vel 3 | 48.5 m³/h | 6.3 W |

The fan shows the speed you set. In **Auto**, where there is no set speed, it
shows the speed the unit is actually running at. Setting a speed while in
**Auto** switches the fan to **Sensor** at that speed (Auto has no manual
speed; Sensor still reacts to the unit's sensors). `sensor.<device>_actual_speed`
always shows the real running speed, including Boost and the unit's Sleep
mode.

### Modes (fan presets)

| Preset | Behaviour |
|---|---|
| **In** | Fresh air intake only. The unit returns to automatic after 60 minutes. |
| **Out** | Extraction only. The unit returns to automatic after 60 minutes. |
| **In/Out** | Alternating intake and extraction with heat recovery: normal operation. |
| **Sensor** | The unit adjusts its speed from its humidity, air-quality and brightness sensors, using the thresholds below. |
| **Auto** | The unit follows its weekly program (set in the Intelliclima app). |

### Season and free cooling

- **Winter**: heat recovery is active; the ceramic core captures heat from
  outgoing air and warms incoming air.
- **Summer**: heat recovery is minimised, and **free cooling** becomes
  available. When it's cooler outside than inside, the unit takes in more
  outdoor air to cool the room.

| Free cooling | Indoor/outdoor difference to act on |
|---|---|
| Low | 2 °C |
| Medium | 4 °C |
| High | 6 °C |

Switching to Winter also turns free cooling off.

### Sensor-mode thresholds

In **Sensor** mode the unit reacts when a reading crosses its threshold:

| Level | Humidity | Air quality (VOC) | Brightness |
|---|---|---|---|
| Off | — | — | — |
| Low | 55 % | 250 | 0.100 |
| Medium | 60 % | 300 | 0.125 |
| High | 65 % | 350 | 0.150 |

By default an exceeded humidity or VOC threshold **boosts** the unit to maximum
speed. With the matching **advanced** switch on, it steps up **one speed**
instead, which suits bathrooms and kitchens with short spikes.

## How it works

- **Polling, every 30 seconds.** Each poll opens a Bluetooth connection, reads
  everything, and disconnects. The units (or proxies) drop idle connections
  within seconds to a minute, and keeping them open would also tie up a proxy's
  few connection slots.
- **Staggered start.** A unit's first poll is delayed by an offset derived
  from its address (0–30 s), so several units don't connect at once.
- **Commands connect on demand.** Each command connects, writes, reads the
  unit's whole state back on the same connection, and disconnects, so the
  entities show the result as soon as the command returns, without waiting
  for the next poll. A failed command reports its error right away.
- **Reachability.** An occasional failed poll is normal through a proxy, so a
  unit is reported unreachable only after **3 failed polls in a row** (about
  90 seconds). Until then its last values are kept. `binary_sensor.<device>_connected`
  shows whether the unit is reachable; it stays available while the other
  entities go unavailable.
- **Self-recovering.** Every poll uses a fresh connection, and polls, commands
  and pairing have hard time limits (2 minutes for polls and pairing, 1 minute
  for commands). A stuck Bluetooth
  operation therefore can't stop polling; the integration keeps retrying until
  the unit answers.
- **Independent reads.** If one value can't be read (for example, it needs
  pairing), only that value shows as unknown; the rest keep updating.
- **Grouped settings.** The three thresholds with their advanced switches are
  written to the unit in one command, and so are the two calibration offsets,
  so changing one resends the others as last read. Until those have been read
  from the unit, a change is refused with an error rather than overwriting them
  with defaults.
- **Clock.** The unit's clock is set from Home Assistant on the first poll and
  then once an hour.
- **Log names.** Log lines name each unit by its own Bluetooth name (e.g.
  `ECMF2-0000abcd`), taken from its advertisement or read once from the
  standard Device Name characteristic and then remembered. A local Bluetooth
  adapter on Linux hides that characteristic, so a unit that doesn't advertise
  its name is logged by its address there.
- **Startup.** Setup doesn't wait for the units, so the integration never slows
  down Home Assistant's startup.

## Main and satellite units

Units can be linked in the Intelliclima app as a **main unit** with one or
more **satellites** that follow it, running in the same or opposite direction.
`sensor.<device>_role` shows each unit's role.

A satellite follows its main unit, and may refuse operating-mode commands sent
to it directly (the error mentions "Write not permitted" and says the unit is
a satellite). Control the **main** unit instead.

## Blueprints

| Blueprint | Description | Import |
|---|---|---|
| [Season Auto-Switch](blueprints/vmc_season_auto_switch.yaml) | Switches Winter/Summer from an outdoor temperature sensor, with hysteresis | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Farizz96%2Fecocomfort2-homeassistant%2Fblob%2Fmain%2Fblueprints%2Fvmc_season_auto_switch.yaml) |
| [Free Cooling Auto](blueprints/vmc_free_cooling_auto.yaml) | Sets free cooling by season and time of day | [![Import](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Farizz96%2Fecocomfort2-homeassistant%2Fblob%2Fmain%2Fblueprints%2Fvmc_free_cooling_auto.yaml) |

Both pick your units' entities through their inputs, so they work with any
device names.

## Migrating from the ESPHome package

The integration exposes the same functionality with Home Assistant-native
entity types. Entity IDs differ: they're derived from the device's name.

| ESPHome package | This integration |
|---|---|
| `fan.<unit>` | `fan.<device>` (same speeds and presets) |
| `select.<unit>_season`, `select.<unit>_free_cooling` | Same, as selects |
| `number.<unit>_humidity/luminosity/voc_threshold` (0–3) | `select.<device>_…_threshold` (Off / Low / Medium / High) |
| `switch.<unit>_humidity_advanced`, `_voc_advanced` | Same, as switches |
| `number.<unit>_set_temp_offset`, `_set_humidity_offset` | Same, as numbers |
| `button.<unit>_pair` | `button.<device>_pair` |
| `binary_sensor.<unit>_connected` | `binary_sensor.<device>_connected` (reachability, see [How it works](#how-it-works)) |
| `binary_sensor.<unit>_boost_active` | Removed: use `sensor.<device>_actual_speed` = **Boost** |
| `sensor.<unit>_temperature`, `_humidity`, `_voc` | Same; VOC on the device's scale, see [About the VOC reading](#about-the-voc-reading) |
| `sensor.<unit>_direction`, `_actual_mode`, `_actual_speed`, `_role` (numbers) | Same names, now with readable states |
| Firmware Version text sensor | Removed: on the device page, with the serial number |
| `sensor.<unit>_temp_offset`, `_humidity_offset` | Removed: the offset numbers show the values stored on the unit |

Differences in behaviour:

- **Actual Mode and Actual Speed show what the unit is really doing**, decoded
  from its running state. The package showed the last command, so they now
  follow automatic changes in Sensor/Auto mode.
- **Season is decoded correctly.** The package read the wrong bit and could
  show Winter after Summer was set.
- **Configuration writes keep a satellite's main-unit address.** The package
  overwrote it with zeros on every season, free cooling or threshold change.
- **No dedicated ESP32 needed.** Your existing adapter or proxies are used.

## Troubleshooting

| Problem | What to do |
|---|---|
| Unit not discovered | Check it's powered and within range of an adapter/proxy. Proxies need `active: true`. Try **Add Integration → Ecocomfort 2.0 VMC**. |
| Entities unavailable right after a restart or reload | Normal for up to about a minute: entities wait for the first poll, which is staggered per unit. |
| Unit stays unreachable | The log has a warning `… unreachable after 3 failed polls; last error: …` saying why. Common causes: range, a busy proxy (too many Bluetooth devices on it), or the Intelliclima app holding the unit's connection. The integration keeps retrying on its own. |
| Some values show "unknown", log says `Can't read … Insufficient encryption` | That value needs a paired link. Put the unit in pairing mode and press **Pair**. |
| Pairing fails (e.g. `Pairing failed due to error: 102`) | The unit wasn't in pairing mode, or the window closed. Hold the button until the LED blinks and press **Pair** immediately. |
| Pairing works but values go unknown again later | Another proxy, not bonded with the unit, may have made the connection. Keep the unit in range of one proxy, or pair through the one in use. |
| Pair button or log says the adapter/proxy can't pair ("doesn't support pairing") | Update the ESPHome proxy to 2024.3.0 or newer. |
| Command fails with "Write not permitted" | The unit is probably a **satellite**; control its main unit. Otherwise press **Pair** with the unit in pairing mode. |
| Command fails with "isn't paired" | Put the unit in pairing mode and press **Pair**. |
| Log warns about an "undocumented … value" | The unit reported a value this integration doesn't know; it shows as unknown. Please open an issue with the log line. |

### Debug logging

**Settings → Devices & Services → Ecocomfort 2.0 VMC → ⋮ → Enable debug
logging**, or in `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.ecocomfort2: debug
```

Each failed poll is then logged with its reason
(`Could not poll … (n in a row): …`).

## BLE protocol reference

Everything goes through one GATT service, `f4b827c3-e660-4bc8-bdf6-3c8e9b845e0d`.
Values are big-endian. Sources are the original ESPHome package, the
Intelliclima cloud API as decoded by
[pyintelliclima](https://github.com/dvdinth/pyintelliclima), the Ecocomfort 2.0
manual, and GATT dumps of real units.

| Characteristic | UUID | Access | Used for |
|---|---|---|---|
| Device info | `f5f56229-dd4f-480f-a829-9189269d8b37` | read | Firmware, serial |
| Sensor readings (state) | `438d3433-7e5a-459a-a8e4-66343fad2bb0` | read, notify | Running mode/speed, direction, temperature, humidity, VOC |
| Operation | `b9d6f678-bc0d-4a73-90c8-60b0f07301f1` | read, write | Commanded mode and speed |
| Configuration | `d3dac48e-b4e1-4f3a-8715-326ddf1da89a` | read, write | Role, thresholds, season, free cooling, satellite settings |
| Calibration | `f8b2284e-61dd-44e3-a782-a93c9503ab2d` | read, write | Temperature/humidity offsets |
| Clock | `82788997-49e4-4533-b949-7ed433678044` | read, write | Date and time |

**Device info** (21 bytes)
- Bytes 0–1: firmware version (major = high nibble of byte 0; the remaining 12
  bits split into 6-bit minor and patch).
- Bytes 2–5: serial number, which is also the suffix of the unit's Bluetooth
  name `ECMF2-xxxxxxxx`.
- Bytes 6–11: the unit's Bluetooth address.
- Bytes 14–19: its Wi-Fi MAC address.

**Sensor readings** (9 bytes)
- Byte 0: running mode in the low nibble: 0 off, 1 in, 2 out, 3 in/out,
  4 sensor/auto.
- Byte 1: running speed in the low 3 bits (1 Sleep, 2–4 Vel 1–3, 5 Boost),
  plus flags:
  - `0x10`: speed comes from the sensors/program (Auto);
  - `0x20`: advanced threshold, one speed step up;
  - `0x40`: boost;
  - `0x80`: Sleep mode.
  - Overrides apply in that order: step up, then boost, then Sleep.
- Byte 2: airflow direction, 1 or 2.
- Bytes 3–4: temperature × 100, signed.
- Bytes 5–6: humidity × 100.
- Bytes 7–8: VOC.
- "No reading" placeholders: 0x7FFF temperature, humidity over 100 %, 0xFFFF
  VOC.

**Operation** (2 bytes, the commanded setpoint)
- Byte 0: mode (0 off, 1 in, 2 out, 3 in/out, 4 sensor/auto).
- Byte 1: speed 1–4; `0x10` instead means Auto.
- Off is written as `00 00`.

**Configuration** (12 bytes; writing `0x7F` in a byte keeps its current value)
- Byte 0: role (0 standalone, 1 main, 2 satellite).
- Bytes 1–3: humidity, brightness and VOC thresholds (0–3; +128 for advanced,
  humidity and VOC only).
- Byte 4: **season in the high nibble** (0 winter, 1 summer) and **free cooling
  in the low nibble** (0–3). Written as `0x1F` (summer, keep free cooling),
  `0x00` (winter, free cooling off) and `0x70 + level` (keep season).
- Byte 5: satellite rotation (1 same direction, 2 opposite).
- Bytes 6–11: the main unit's address, on a satellite. The integration writes
  them back as last read (the ESPHome package wrote zeros).

**Calibration** (4 bytes)
- Temperature offset and humidity offset, each a signed 16-bit value × 100.

**Clock** (8 bytes)
- Year (2 digits), month, day, weekday (0 = Monday), hour, minute, second, 0.

The units also expose characteristics this integration doesn't use:
- a weekly program (`4a3561b0-5e1c-42e5-995e-e3a3310e38a3`, 168 bytes = 7 days
  × 24 hours of speed levels);
- Wi-Fi/cloud settings (`6e6bad93-5db2-4864-86e3-3707b12907b2`);
- statistics and other request/response channels that can't simply be read
  (`ab53b5e0-3a3f-4548-8972-95dec0ed0b2d` and others).

## Known limitations

- **Direction labels are an assumption.** Intake = 1 and Exhaust = 2 isn't
  documented anywhere. It's consistent with a main/satellite pair running
  opposite directions, but not confirmed against a unit.
- **The weekly program and Sleep mode** can't be edited or selected from Home
  Assistant; use the Intelliclima app. Setting the fan to 25 % runs at Sleep
  speed.
- **No brightness reading.** The brightness sensor only drives its threshold;
  the unit doesn't report a light level (the app doesn't show one either).
- **Polling only.** The unit can push sensor readings, but it does so very
  often, and subscribing can require pairing, so the integration polls every
  30 seconds instead.

## Credits

- **[gledian/esphome-ecocomfort2](https://github.com/gledian/esphome-ecocomfort2):
  big thanks.** The original ESPHome package and the protocol work this
  integration is built on; it wouldn't have been possible without it.
- [dvdinth/pyintelliclima](https://github.com/dvdinth/pyintelliclima): the
  Intelliclima cloud API decoding used to identify the running state, roles and
  the season/free-cooling byte.
- Fantini Cosmi's Ecocomfort 2.0 Smart user manual and technical data sheet.

## License

MIT
