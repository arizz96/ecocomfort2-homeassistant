# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

A Home Assistant custom integration (`custom_components/ecocomfort2`, domain
`ecocomfort2`) for Intelliclima / Fantini Cosmi **Ecocomfort 2.0 Smart**
heat-recovery ventilation units, talking BLE through Home Assistant's Bluetooth
stack: a local adapter or a connectable proxy. It's a port of the
[esphome-ecocomfort2](https://github.com/gledian/esphome-ecocomfort2) ESPHome
package. User-facing documentation, including the full byte-level protocol, is
in `README.md`; keep it in sync with behaviour changes.

- Version `0.1.0` (`manifest.json`).
- Minimum Home Assistant **2026.8**: `hacs.json` and the README's Requirements
  section must match.
- Real-unit testing has used a main unit and its satellite behind an ESPHome
  Bluetooth proxy.

## Layout

| File | Role |
|---|---|
| `device.py` | Everything BLE: connection lifecycle, pairing, polling, parsing, command encoding. `EcoComfort2Device` + `EcoComfort2State` |
| `coordinator.py` | `DataUpdateCoordinator`: 30 s poll, staggered first poll, hourly clock sync, device-registry firmware/serial |
| `__init__.py` | Setup without blocking startup; registry cleanup of replaced entities |
| `entity.py` | Base entity: device info, availability, `_async_command` (UI error messages + refresh) |
| `fan.py`, `sensor.py`, `select.py`, `switch.py`, `number.py`, `button.py`, `binary_sensor.py` | Platforms, description-driven |
| `config_flow.py` | Bluetooth discovery (service UUID, or `Comfort_*` name) and manual pick |
| `const.py` | UUIDs, protocol constants, enum option lists |
| `strings.json`, `translations/en.json`, `translations/it.json` | Config flow + enum state labels (en/it); entity *names* come from code |
| `brand/` | Icon/logo (used from HA 2026.3); Intelliclima has no separate logo, so `logo*.png` = `icon*.png` |
| `blueprints/` | Season and free-cooling automations (select by entity input; option strings `Summer`/`Winter`/`Off`/`Low`/… are relied on) |

There is no test suite in the repo; see **Testing** below.

## Protocol knowledge and its sources

See the README's "BLE protocol reference" for byte layouts. How sure we are of
each part:

- **Confirmed against real units** (GATT dumps from a main unit and its
  satellite):
  - **Sensor readings bytes 0–1** are the *running* mode/speed (cloud API
    `mode_state`/`speed_state`), unlike the operation characteristic, which is
    the commanded setpoint.
  - **Configuration byte 4** is season in the high nibble and free cooling in
    the low nibble. The original package read season from bit 3, which was
    wrong.
  - **Role** 1 = main, 2 = satellite; a satellite's configuration contains its
    main unit's address (bytes 6–11). Configuration writes send those bytes
    back as last read, never zeros (the package's choice) or 0x7F (whether
    "keep" applies there is undocumented), so they need a prior read.
  - **Device info bytes 2–5** are the serial number, the suffix of the GAP name
    `ECMF2-xxxxxxxx`.
- **From pyintelliclima** (Intelliclima cloud API, same device family): the
  speed-flag decoding (`0x10` profiled/auto, `0x20` advanced step, `0x40`
  boost, `0x80` Sleep), its override order, and the "no reading" placeholders.
- **From the manual** (EN/IT):
  - Sleep mode (section 3.7.3) is a minimum-speed mode. Call it **"Sleep" in
    every language**, never "Night"/"Notte".
  - The VOC thresholds are labelled 250/300/350 "ppm".
  - The brightness thresholds read 0.1/0.125/0.150 "lux"; that's a vendor scale
    name, not a physical unit.
- **Unverified:**
  - Direction byte 1 = intake, 2 = exhaust is an assumption. A satellite set
    to "opposite" rotation read the other value at the same moment, which
    supports it being a direction byte.
  - The meaning of the high nibble of sensor-readings byte 0 is unknown.
- **VOC** is the device's own scale, not a concentration: about 220 is
  normal. Unit `UnitOfRatio.PARTS_PER_MILLION` (the manufacturer's label) with
  **no device class**, so HA doesn't convert it. ppb would be physically
  plausible but contradicts the manual; ppm with the VOC device class made HA
  show "224,000 ppb".
- **Undocumented enum values** go through `_decode()`, which logs once and
  returns `None` (unknown) instead of guessing.

## Design decisions (and why)

Most of these were learned from real-world failures; don't undo them without a
reason.

- **Connect → read → disconnect on every poll.** No persistent link: the units
  or proxies drop idle connections within a minute, and a held link wastes an
  ESP32 proxy's ~3 slots. Each poll opens a *fresh* connection, closing any
  left over from a command first.
- **Hard timeouts.** `POLL_TIMEOUT` 120 s, `COMMAND_TIMEOUT` 60 s,
  `PAIR_BUTTON_TIMEOUT` 120 s, `DISCONNECT_TIMEOUT` 10 s. The coordinator schedules the next poll only after
  the current one returns, and all BLE work shares one `asyncio.Lock`, so
  without them a single hung operation stopped polling until a reload.
  `_disconnect_locked` never raises, and polls catch *any* exception as a
  failed poll.
- **Reachability.** `state.connected` turns False only after 3 consecutive
  failed polls, then logs a warning with the reason (and info on recovery).
  Entities go unavailable when not connected, except the Connected sensor and
  the Pair button.
- **Commands pass their change into the device method** (e.g.
  `async_send_operation(speed=…)`, `async_send_thresholds(voc=…)`), which
  merges it with the `desired_*` readback *under the lock* and updates
  `desired_*` only after a successful write. Setting `desired_*` from an entity
  before waiting for the lock let a running poll overwrite the change with the
  old value (reproduced in a simulation). Grouped writes (thresholds, offsets)
  refuse with a `HomeAssistantError` while a value they would resend is still
  unknown (`None`), instead of writing a default over it.
- **Log labels use the unit's Bluetooth name** (`device.label`: name, else
  address). The name comes from the advertisement if it's a real name (HA
  reports a missing one as the address), else from the GAP Device Name
  (0x2A00) read once after the other reads. That read is optional: it never
  pairs and a failure is only logged at debug. bleak-esphome passes every
  service through, so it works via proxies; BlueZ hides the GAP service. The
  coordinator stores the name in `entry.data["name"]` so labels are right from
  the first poll. `describe_command_error` still uses the entry title.
- **A poll that reads nothing counts as failed,** to catch links that only
  look alive.
- **Independent reads.** Each characteristic is read on its own (parity with
  the package's separate sensors). A failed one clears only its fields
  (unknown) and is logged once.
- **Lazy pairing.** Pair only when a GATT op fails with insufficient
  encryption/authentication: at most once per connection, and after a failure
  not again for `PAIR_RETRY_INTERVAL` (10 min, `_pair_retry_at`) or until the
  Pair button. The wait used to be permanent: a pair attempt that failed when
  the satellite's link dropped (log: "is not connected") left it refusing
  every read with "Insufficient encryption" — unreachable until someone
  pressed Pair (seen on real units, 2026-10-06). A poll whose every read fails
  for encryption raises an error saying so. Never request pairing from
  optional operations. A failed pair through a proxy drops the link, which
  caused a reconnect loop once with notifications.
- **The Pair button** pairs without unpairing first (the maintainer's change,
  matching the package) and surfaces failure as a `HomeAssistantError`.
- **No notifications.** The sensor-readings characteristic supports notify,
  but the unit floods notifications and the CCCD write can require pairing.
  The maintainer explicitly chose 30 s polling only; it was added and removed
  twice.
- **GATT service cache is reused** (`use_services_cache=True`, maintainer's
  change). A stale cache is handled:
  - a "not found" read clears the cache;
  - a "write not permitted" logs the characteristic's handle/properties,
    clears the cache, reconnects and retries once.
- **Staggered first poll** (`_stagger_offset`, maintainer's change). Note the
  current two units get offsets 3 s and 29 s, only about 4 s apart in the 30 s
  cycle; improving the spread was offered but not requested.
- **Non-blocking setup.** `coordinator.data` is pre-set to the empty state,
  platforms are forwarded, then the first refresh runs as
  `entry.async_create_background_task`. Firmware and serial are written later
  via `async_get_device_by_identifier` + `async_update_device`
  (`async_get_device` is deprecated; the new API needs HA 2026.8). Entity
  `DeviceInfo` must not set them, because passing unknown values clears them.
- **Coordinator updates must not reset the timer.** Never use
  `async_set_updated_data` for out-of-band updates; it resets the poll timer.
  Use `async_update_listeners`.
- **Entities are deliberately minimal.**
  - Boost Active and Sleep/Night Mode binary sensors were removed because they
    restated Actual Speed (or contradicted it).
  - Temp/Humidity Offset sensors (restated the offset numbers) and Firmware
    Version (on the device page) were removed.
  - Thresholds are selects, not numbers.
  - Coded values are `SensorDeviceClass.ENUM` with `translation_key` state
    labels.
  - Season/free-cooling/preset option strings stay human strings because
    blueprints and automations depend on them.
- **Registry cleanup.** `__init__.py` removes registry entries of replaced
  entities (old threshold numbers, `night_active`, `sleep_active`,
  `boost_active`, `temp_offset`, `humidity_offset`, `firmware`). Add to that list when an entity is removed or changes
  platform.
- **Use Home Assistant's current APIs** (`UnitOfRatio`,
  `AddConfigEntryEntitiesCallback`, `entry.runtime_data`). Before using a
  newer HA API, check which release introduced it and bump the minimum version
  if needed.

## Testing

No hardware is reachable from the development environment, and there's no
committed test suite. Verify changes with ad-hoc scripts:

- **Environment.** The container's newest Python is 3.13, and HA ≥ 2026.3
  needs Python ≥ 3.14, so the local venv (e.g. `/tmp/ha313`) runs HA 2026.2.3
  plus `bleak-retry-connector`, `habluetooth`, `bluetooth-adapters`,
  `bluetooth-data-tools`, `dbus-fast`, `aiousbwatcher` and `pyserial` (needed
  to import `homeassistant.components.bluetooth`). Recreate it if it's gone.
  Don't install `bleak-esphome` into it: its dependencies conflict with HA's
  pins. Download its wheel and read the source instead.
- **Newer HA APIs.** Code uses APIs newer than 2026.2 (`UnitOfRatio`,
  `DeviceRegistry.async_get_device_by_identifier`). Tests inject a test-only
  shim (a stand-in `UnitOfRatio` and an `async_get_device_by_identifier`
  wrapper) via a module imported before the integration. Never commit shims
  or compatibility fallbacks into the integration.
- **Checking against a real release.** Download its wheel from PyPI
  (`https://pypi.org/pypi/homeassistant/<version>/json`) and inspect the
  source, e.g. to see which release introduced an API.
- **Mocking BLE.** Patch `device.establish_connection` and
  `device.bluetooth.async_ble_device_from_address`. Fake clients need
  `is_connected`, `read_gatt_char`, `write_gatt_char`, `disconnect` (calling
  the disconnected callback), and `pair`, `unpair`, `clear_cache` where
  exercised.
- **Real-data fixtures** captured from real units (addresses replaced with
  `aa…`, serial with `ab cd`):
  - running main unit in Auto, Sleep active: sensor readings
    `04 91 02 08 6e 15 be 00 e0`, operation `04 10`;
  - satellite in Sensor with boost and Sleep flags: sensor readings
    `44 c1 01 08 47 15 93 01 09`, operation `04 01`;
  - satellite configuration `02 01 02 01 10 02 aa aa aa aa aa aa` (role 2,
    summer, opposite rotation);
  - device info `01 88 00 00 ab cd aa aa aa aa aa aa 01 00 aa aa aa aa aa aa 01`
    → firmware 0.6.8, serial `0000abcd`;
  - calibration `ff 38 fe 0c` → −2.00 °C / −5.00 %.
- **What to always check:** `python3 -m py_compile`, importing every module
  against HA, the translations covering every enum `options` entry, and
  behaviour scenarios such as failed/hung polls, pairing gating and registry
  cleanup.
- **Be explicit about what was simulated** versus run on real units.

### Network

The session egress policy has blocked `brands.home-assistant.io`, the
manufacturer's site (`fantinicosmi.it`), ManualsLib and the HA community forum
at times. GitHub and PyPI work. On a 403 from the proxy, don't route around it
with other tools; report it. Manual PDFs were fetched once the policy allowed
it.

## Git workflow

- **Branch:** `claude/ecocomfort2-ha-ble-component-gru8qo`; push with
  `git push -u origin <branch>`.
- **Fetch first.** The maintainer also pushes their own commits to this
  branch, so always fetch before pushing and **rebase onto their work**.
  Never overwrite it.
- **Commit messages:** `type: summary` (`feat`, `fix`, `perf`, `refactor`,
  `chore`, `docs`), with a body explaining *why*. End with the attribution
  trailer the session instructions specify.
- **Clean history.** The maintainer asks for squashes and drops (fixups folded
  into the commit that introduced the bug, reverted experiments removed).
  Rewrite history only when asked:
  1. back up with `git branch -f backup/<name> HEAD`;
  2. verify the final tree with `git diff`;
  3. check every rewritten commit still imports;
  4. push with `--force-with-lease=<branch>:<expected-sha>`.
- **Commit-message honesty.** A commit's title must match its content, e.g.
  the version it sets.

## Working with the maintainer

- **Keep reports short and direct.** Say what was verified and how, and what
  wasn't (no hardware access).
- **Ground claims in sources** (the original package, pyintelliclima, the
  manual, captured data). Say when something is an assumption, and fix wrong
  earlier claims openly.
- **Diagnose before changing.** When the maintainer reports a symptom
  (activity CSVs, log lines), analyse it before changing code, and prefer the
  smallest fix that addresses the evidence.
- **Ask when ambiguous.** For questions phrased as "maybe we can…", answer
  with the trade-off first; implement directly only when the instruction is
  clear.
