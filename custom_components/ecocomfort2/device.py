"""BLE connection management and protocol for the Ecocomfort 2.0 VMC.

This module talks to the VMC directly over Bluetooth Low Energy using the
Home Assistant Bluetooth stack (no ESPHome proxy required). It mirrors the
protocol previously implemented in the ESPHome package: a single GATT service
with a handful of read/write characteristics.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
import logging
import time
from typing import Any

from bleak.backends.device import BLEDevice
from bleak.exc import BleakCharacteristicNotFoundError, BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from .const import (
    CHAR_ADVANCED,
    CHAR_CLOCK,
    CHAR_CONFIG,
    CHAR_DEVICE_NAME,
    CHAR_INFO,
    CHAR_OPER,
    CHAR_STATE,
    CONFIG_PRESERVE,
    DEFAULT_SPEED,
    DIRECTION_OFF,
    FREE_COOLING_TO_VALUE,
    FREE_COOLING_WRITE_PREFIX,
    MODE_IN,
    MODE_IN_OUT,
    MODE_OFF,
    MODE_OUT,
    MODE_SENSOR_AUTO,
    PRESET_AUTO,
    PRESET_IN,
    PRESET_IN_OUT,
    PRESET_OUT,
    PRESET_SENSOR,
    PRESET_TO_MODE,
    SEASON_SUMMER,
    SEASON_WINTER,
    SEASON_WRITE_SUMMER,
    SEASON_WRITE_WINTER,
    RUNNING_SPEED_MASK,
    SPEED_ADVANCED_FLAG,
    SPEED_AUTO_FLAG,
    SPEED_BOOST_FLAG,
    SPEED_SLEEP_FLAG,
    THRESHOLD_ADVANCED_FLAG,
    VALUE_TO_DIRECTION,
    VALUE_TO_FREE_COOLING,
    VALUE_TO_ROLE,
    VALUE_TO_SPEED_LEVEL,
)

_LOGGER = logging.getLogger(__name__)

# Settle time after pairing before the next GATT operation, mirroring the
# delay the original ESPHome package used after pairing.
PAIR_SETTLE_DELAY = 0.5
# Upper bound on a pairing attempt, so a proxy that never answers can't hold
# the connection lock (and every command behind it) indefinitely.
PAIR_TIMEOUT = 30
# Wait this long before asking again after the unit refused (or ignored) a
# pairing request, so a unit outside pairing mode isn't asked on every poll.
PAIR_RETRY_INTERVAL = 600
# The Pair button connects, pairs and syncs the clock, so give it as long as a
# poll rather than a single command.
PAIR_BUTTON_TIMEOUT = 120
# Consecutive failed polls before a unit is reported unreachable. Through a
# proxy an occasional poll fails (fresh connection + service discovery each
# time); one failure shouldn't make every entity flap.
FAILED_POLLS_BEFORE_UNREACHABLE = 3
# Hard limits so a hung BLE operation can't stall the integration: the
# coordinator only schedules the next poll after the current one returns, and
# every poll and command shares one lock.
POLL_TIMEOUT = 120
COMMAND_TIMEOUT = 60
DISCONNECT_TIMEOUT = 10

# Raw "no reading" values in C_STATE (0x7FFF = 327.67 °C, 0xFFFF VOC).
# Humidity's sentinel (143 %) is caught by rejecting anything above 100 %.
TEMPERATURE_NO_READING = 0x7FFF
VOC_NO_READING = 0xFFFF

CHAR_NAMES = {
    CHAR_INFO: "device info",
    CHAR_STATE: "sensor readings",
    CHAR_OPER: "operating mode",
    CHAR_CONFIG: "configuration",
    CHAR_ADVANCED: "calibration offsets",
    CHAR_CLOCK: "clock",
}


def _needs_encryption(err: Exception) -> bool:
    """Return True for ATT errors that pairing (encrypting the link) can fix."""
    text = str(err).lower()
    return "insufficient" in text or "encrypt" in text or "authent" in text


def describe_command_error(name: str, err: Exception) -> str:
    """Return a user-facing explanation for a failed command."""
    if _needs_encryption(err):
        return (
            f"{name} refused the command because the Bluetooth link isn't "
            "paired. Put the VMC in pairing mode (hold its button ~5s until "
            f"the LED blinks) and press the Pair button. ({err})"
        )
    if "not permitted" in str(err).lower():
        # Only reaches the user after a fresh service rediscovery, so the
        # handle is right and the device itself is refusing the write.
        return (
            f"{name} refused the write even after rediscovering its "
            "services. It most likely only accepts commands from a bonded "
            "link: put the VMC in pairing mode (hold its button ~5s until "
            f"the LED blinks) and press the Pair button. ({err})"
        )
    if isinstance(err, TimeoutError):
        # Raised by our own COMMAND_TIMEOUT, with no message of its own.
        return (
            f"{name} didn't respond in time; the command may not have been "
            "applied"
        )
    return f"Couldn't send the command to {name}: {err}"


@dataclass
class EcoComfort2State:
    """Snapshot of everything we read back from the device.

    A field is None when its characteristic couldn't be read in the last
    poll, so entities show "unknown" instead of a stale value.
    """

    connected: bool = False

    # C_INFO
    firmware: str | None = None
    serial: str | None = None

    # C_STATE: what the unit is actually doing right now
    operating_mode: str | None = None  # one of OPERATING_MODE_OPTIONS
    speed_level: str | None = None  # one of SPEED_LEVEL_OPTIONS
    running_speed: int | None = None  # 1-4 (boost as 4), for the fan
    direction: str | None = None  # key of VALUE_TO_DIRECTION
    temperature: float | None = None
    humidity: float | None = None
    voc: float | None = None

    # C_SETTING_OPERATION: the last command (setpoint)
    is_on: bool | None = None
    preset: str | None = None
    commanded_speed: int | None = None  # 1-4, None in Auto

    # C_CONFIGURATION
    role: str | None = None  # key of VALUE_TO_ROLE
    humidity_threshold: int | None = None
    humidity_advanced: bool | None = None
    luminosity_threshold: int | None = None
    voc_threshold: int | None = None
    voc_advanced: bool | None = None
    season: str | None = None
    free_cooling: str | None = None

    # C_ADVANCED
    temp_offset: float | None = None
    humidity_offset: float | None = None


_NOT_READ_YET = (
    "The unit's current {what} haven't been read yet, and they're all written "
    "together; try again after the next update"
)


def _pick[T](change: T | None, current: T | None) -> T | None:
    """Return the requested change, or the current value if none."""
    return current if change is None else change


def _is_real_name(name: str | None, address: str) -> bool:
    """Return False for a missing name, which HA reports as the address."""
    return bool(name) and name.replace("-", ":").upper() != address.upper()


def parse_firmware(data: bytes) -> str | None:
    """Decode the firmware version string from C_INFO."""
    if len(data) < 2:
        return None
    major = (data[0] >> 4) & 0x0F
    packed = ((data[0] & 0x0F) << 8) | data[1]
    minor = (packed >> 6) & 0x3F
    patch = packed & 0x3F
    return f"{major}.{minor}.{patch}"


def parse_serial(data: bytes) -> str | None:
    """Decode the serial number from C_INFO bytes 2-5.

    It's the suffix of the unit's GAP device name, e.g. "ECMF2-0000abcd".
    """
    if len(data) < 6:
        return None
    return f"{int.from_bytes(data[2:6], 'big'):08x}"


class EcoComfort2Device:
    """Owns the BLE connection to a single VMC unit and the protocol logic."""

    def __init__(
        self, hass: HomeAssistant, address: str, name: str | None = None
    ) -> None:
        """Initialise the device wrapper for a given BLE address."""
        self.hass = hass
        self.address = address
        # The unit's own Bluetooth name (e.g. "ECMF2-0000abcd"), to tell units
        # apart in logs. Passed in when stored from an earlier run, otherwise
        # learned from the advertisement or the GAP Device Name characteristic.
        self.name = name
        self.state = EcoComfort2State()

        self._lock = asyncio.Lock()
        self._client: BleakClientWithServiceCache | None = None
        self._firmware: str | None = None
        # Pairing is requested lazily, only when a characteristic answers
        # "insufficient encryption/authentication", and at most once per
        # connection. Re-requesting it on every reconnect or every poll makes
        # proxies time out when the VMC isn't in pairing mode.
        self._pair_attempted = False
        # time.monotonic() before which pairing isn't requested again, set
        # after the unit refused or ignored a request (each attempt can take
        # up to PAIR_TIMEOUT). Never permanent: a unit that needs pairing
        # would otherwise stay unreadable until someone pressed Pair. The Pair
        # button clears it.
        self._pair_retry_at = 0.0
        # Set when the backend can't pair at all (ESPHome Bluetooth proxy
        # older than 2024.3.0 raises NotImplementedError).
        self._pairing_unsupported = False
        # Characteristics whose last read failed, with the error, so a
        # persistent failure is logged once instead of on every poll.
        self._failing: dict[str, Exception] = {}
        self._failed_polls = 0
        # Undocumented raw values already logged, as (field, value).
        self._unknown_logged: set[tuple[str, int]] = set()

        # Desired state used to build the operation command. Kept in sync with
        # the device readback so a partial change (e.g. only speed) preserves
        # the rest of the command.
        self.desired_preset_name: str = PRESET_IN_OUT
        self.desired_speed: int = DEFAULT_SPEED

        # Sensor configuration and calibration offsets as last read. Each group
        # is written as a whole, so changing one value resends the others from
        # here; None until read, so a write never replaces a setting we haven't
        # seen with a made-up default.
        self.desired_humidity_threshold: int | None = None
        self.desired_humidity_advanced: bool | None = None
        self.desired_luminosity_threshold: int | None = None
        self.desired_voc_threshold: int | None = None
        self.desired_voc_advanced: bool | None = None
        self.desired_temp_offset: float | None = None
        self.desired_humidity_offset: float | None = None
        # C_CONFIGURATION bytes 6-11 as last read: a satellite's main-unit
        # address. Every configuration write sends them back unchanged.
        self._config_address: bytes | None = None

        # Last clock sync attempt that reached the unit; the coordinator
        # repeats it hourly.
        self.last_clock_sync: datetime | None = None

    @property
    def label(self) -> str:
        """Return how the unit is named in logs: its Bluetooth name or address."""
        return self.name or self.address

    @property
    def connected(self) -> bool:
        """Return whether the BLE link is currently up."""
        return self._client is not None and self._client.is_connected

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------
    def _on_disconnect(self, _client: BleakClientWithServiceCache) -> None:
        # Links are closed after every poll anyway; a drop mid-poll surfaces as
        # a failed read, so there's nothing else to do here.
        _LOGGER.debug("Disconnected from %s", self.label)

    async def _connect_locked(self) -> None:
        """Open a plain (unpaired) connection. Caller holds the lock."""
        ble_device: BLEDevice | None = bluetooth.async_ble_device_from_address(
            self.hass, self.address.upper(), connectable=True
        )
        if ble_device is None:
            raise BleakError(
                f"Ecocomfort2 device {self.label} not found; is it in range?"
            )
        if self.name is None and _is_real_name(ble_device.name, self.address):
            self.name = ble_device.name
        _LOGGER.debug("Connecting to %s", self.label)
        self._client = await establish_connection(
            BleakClientWithServiceCache,
            ble_device,
            self.label,
            disconnected_callback=self._on_disconnect,
            # Reuse the cached handle map: full discovery on every poll adds
            # GATT traffic and proxy load for little benefit once the layout
            # is known. A stale cache surfaces as BleakCharacteristicNotFound-
            # Error (read) or an ATT "not permitted" (write); both are already
            # handled by clearing the cache and rediscovering, in
            # _read_char_locked and _rediscover_locked respectively.
            use_services_cache=True,
        )
        self._pair_attempted = False

    async def _ensure_connected(self) -> None:
        """Connect if not already connected. Caller holds the lock."""
        if self.connected:
            return
        await self._connect_locked()

    async def async_disconnect(self) -> None:
        """Tear down the BLE connection."""
        async with self._lock:
            await self._disconnect_locked()

    async def _disconnect_locked(self) -> None:
        """Close the link, if any. Bounded in time and never raises."""
        client = self._client
        self._client = None
        if client is None:
            return
        try:
            async with asyncio.timeout(DISCONNECT_TIMEOUT):
                await client.disconnect()
        except Exception as err:  # noqa: BLE001 - nothing to do but move on
            _LOGGER.debug("Error disconnecting from %s: %s", self.label, err)

    async def _pair_locked(self) -> bool:
        """Pair/encrypt the current link, at most once per connection.

        Returns True if the link is now paired. A failure is never fatal to
        the connection: characteristics that don't need encryption keep
        working, matching the original package, which ignored a failed pair().
        """
        if (
            self._pair_attempted
            or self._pairing_unsupported
            or time.monotonic() < self._pair_retry_at
        ):
            return False
        self._pair_attempted = True
        client = self._client
        assert client is not None
        _LOGGER.debug("Pairing with %s", self.label)
        try:
            async with asyncio.timeout(PAIR_TIMEOUT):
                await client.pair()
        except NotImplementedError:
            self._pairing_unsupported = True
            _LOGGER.warning(
                "The Bluetooth adapter/proxy for %s doesn't support pairing. "
                "If you're using an ESPHome Bluetooth proxy, update it to "
                "ESPHome 2024.3.0 or newer",
                self.label,
            )
            return False
        except (BleakError, TimeoutError) as err:
            # Also when the link dropped: a failed pair through a proxy drops
            # it too, so the two can't be told apart, and retrying on the next
            # poll caused a reconnect loop once.
            self._pair_retry_at = time.monotonic() + PAIR_RETRY_INTERVAL
            _LOGGER.warning(
                "Pairing with %s failed: %s. Values that need an encrypted "
                "link will show as unknown; pairing is retried every %s "
                "minutes, or put the VMC in pairing mode (hold its button ~5s "
                "until the LED blinks) and press the Pair button",
                self.label,
                err,
                PAIR_RETRY_INTERVAL // 60,
            )
            return False
        await asyncio.sleep(PAIR_SETTLE_DELAY)
        return True

    async def _gatt_locked(
        self, op: Callable[[BleakClientWithServiceCache], Awaitable[Any]]
    ) -> Any:
        """Run a GATT operation, pairing and retrying once if it needs encryption."""
        client = self._client
        assert client is not None
        try:
            return await op(client)
        except (BleakError, TimeoutError) as err:
            if not _needs_encryption(err) or not await self._pair_locked():
                raise
        return await op(client)

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------
    async def async_poll(self, sync_clock: bool = False) -> EcoComfort2State:
        """Connect, read every characteristic, optionally sync the clock, disconnect.

        The link isn't kept open between polls: the units (or the proxy) drop
        idle connections within seconds to a minute, and an ESP32 proxy only
        has a few connection slots to share. `connected` in the returned state
        turns False only after FAILED_POLLS_BEFORE_UNREACHABLE failed polls in
        a row; until then the last values are kept.
        """
        async with self._lock:
            try:
                async with asyncio.timeout(POLL_TIMEOUT):
                    # Always a fresh connection: never reuse a link left over
                    # from a command, which may look alive but be dead.
                    await self._disconnect_locked()
                    await self._connect_locked()
                    await self._read_all_locked()
                    if sync_clock:
                        await self._write_clock_locked()
            except Exception as err:  # noqa: BLE001 - any failure is a failed poll
                self._failed_polls += 1
                reason = f"{type(err).__name__}: {err}" if str(err) else type(err).__name__
                _LOGGER.debug(
                    "Could not poll %s (%s in a row): %s",
                    self.label,
                    self._failed_polls,
                    reason,
                )
                if self._failed_polls == FAILED_POLLS_BEFORE_UNREACHABLE:
                    _LOGGER.warning(
                        "%s unreachable after %s failed polls; last error: %s",
                        self.label,
                        self._failed_polls,
                        reason,
                    )
                    self.state.connected = False
            else:
                if self._failed_polls >= FAILED_POLLS_BEFORE_UNREACHABLE:
                    _LOGGER.info("%s reachable again", self.label)
                self._failed_polls = 0
                self.state.connected = True
            finally:
                await self._disconnect_locked()
            return self.state

    async def _read_all_locked(self) -> None:
        # Each characteristic is read independently, like the separate
        # ble_client sensors in the original package: one that can't be read
        # (e.g. it needs stronger encryption than the link has) must not
        # stop the others from updating.
        if self._firmware is None:
            data = await self._read_char_locked(CHAR_INFO)
            if data is not None:
                self._firmware = parse_firmware(data)
                self.state.serial = parse_serial(data)
        self.state.firmware = self._firmware

        any_read = False
        for char, parse, clear in (
            (CHAR_STATE, self._parse_state, self._clear_state),
            (CHAR_OPER, self._parse_oper, self._clear_oper),
            (CHAR_CONFIG, self._parse_config, self._clear_config),
            (CHAR_ADVANCED, self._parse_advanced, self._clear_advanced),
        ):
            data = await self._read_char_locked(char)
            if data is None:
                clear()
            else:
                any_read = True
                parse(data)
        if not any_read:
            # A link that reads nothing at all is as good as no link.
            if all(
                _needs_encryption(self._failing[char])
                for char in (CHAR_STATE, CHAR_OPER, CHAR_CONFIG, CHAR_ADVANCED)
            ):
                raise BleakError(
                    f"{self.label} answers but refuses every read until the "
                    "link is paired (insufficient encryption). Pairing is "
                    "retried automatically; to pair now, put the VMC in "
                    "pairing mode (hold its button ~5s until the LED blinks) "
                    "and press the Pair button"
                )
            raise BleakError(f"No characteristic could be read from {self.label}")
        if self.name is None:
            await self._read_name_locked()

    async def _read_name_locked(self) -> None:
        """Read the GAP Device Name for log labels. Optional: never pairs."""
        client = self._client
        assert client is not None
        try:
            if client.services.get_characteristic(CHAR_DEVICE_NAME) is None:
                return  # e.g. a local BlueZ adapter, which hides the GAP service
            data = await client.read_gatt_char(CHAR_DEVICE_NAME)
        except (BleakError, TimeoutError) as err:
            _LOGGER.debug("Can't read the device name of %s: %s", self.label, err)
            return
        name = bytes(data).decode("utf-8", "replace").strip("\x00").strip()
        if name:
            _LOGGER.debug("%s is %s", self.address, name)
            self.name = name

    async def _read_char_locked(self, char: str) -> bytes | None:
        """Read one characteristic, or return None if only that read failed.

        Raises if the link itself went down, so the whole poll is abandoned.
        """
        try:
            data = await self._gatt_locked(lambda client: client.read_gatt_char(char))
        except BleakCharacteristicNotFoundError as err:
            # Likely a stale GATT cache; rediscover on the next connection.
            await self._clear_cache_locked()
            self._note_read_failure(char, err)
            return None
        except (BleakError, TimeoutError) as err:
            if not self.connected:
                raise
            self._note_read_failure(char, err)
            return None
        if char in self._failing:
            del self._failing[char]
            _LOGGER.info(
                "Reading %s from %s works again", CHAR_NAMES[char], self.label
            )
        return bytes(data)

    def _note_read_failure(self, char: str, err: Exception) -> None:
        known = char in self._failing
        self._failing[char] = err
        if known:
            _LOGGER.debug(
                "Still can't read %s from %s: %s", CHAR_NAMES[char], self.label, err
            )
            return
        _LOGGER.warning(
            "Can't read %s from %s: %s", CHAR_NAMES[char], self.label, err
        )

    # ------------------------------------------------------------------
    # Parsing (C_STATE, C_SETTING_OPERATION, C_CONFIGURATION, C_ADVANCED)
    # ------------------------------------------------------------------
    def _decode(self, field: str, raw: int, mapping: dict[int, str]) -> str | None:
        """Map a coded byte to its enum key; an undocumented value becomes None."""
        if (key := mapping.get(raw)) is not None:
            return key
        if (field, raw) not in self._unknown_logged:
            self._unknown_logged.add((field, raw))
            _LOGGER.warning(
                "%s reported an undocumented %s value %s; showing it as unknown",
                self.label,
                field,
                raw,
            )
        return None

    def _parse_state(self, data: bytes) -> None:
        if len(data) < 9:
            self._clear_state()
            return
        self._parse_running(data[0], data[1])
        # A stopped unit has no airflow; its direction byte is then
        # meaningless, so don't decode (and warn about) it.
        self.state.direction = (
            DIRECTION_OFF
            if data[0] & 0x0F == MODE_OFF
            else self._decode("direction", data[2], VALUE_TO_DIRECTION)
        )
        # The device reports fixed "no reading" values (documented for the
        # vendor cloud API as 327.67 / 143 / 65535); show those as unknown.
        temp_raw = int.from_bytes(data[3:5], "big", signed=True)
        self.state.temperature = (
            None if temp_raw == TEMPERATURE_NO_READING else temp_raw / 100.0
        )
        humidity = int.from_bytes(data[5:7], "big", signed=False) / 100.0
        self.state.humidity = humidity if humidity <= 100 else None
        voc_raw = int.from_bytes(data[7:9], "big", signed=False)
        self.state.voc = None if voc_raw == VOC_NO_READING else float(voc_raw)

    def _clear_state(self) -> None:
        self.state.operating_mode = None
        self.state.speed_level = None
        self.state.running_speed = None
        self.state.direction = None
        self.state.temperature = None
        self.state.humidity = None
        self.state.voc = None

    def _parse_running(self, mode_state: int, speed_state: int) -> None:
        """Decode the running mode/speed in C_STATE bytes 0-1.

        Same registers and decoding as the vendor cloud API's mode_state/
        speed_state (and the Intelliclima app): the running speed is in the
        low 3 bits, with flags for sensor/program control (0x10), an advanced
        threshold's one-step bump (0x20), boost (0x40) and Sleep mode (0x80).
        Unlike C_SETTING_OPERATION, this follows what the unit does on its
        own in Sensor/Auto mode.
        """
        profiled = bool(speed_state & SPEED_AUTO_FLAG)
        advanced = bool(speed_state & SPEED_ADVANCED_FLAG)
        boost = bool(speed_state & SPEED_BOOST_FLAG)
        sleep = bool(speed_state & SPEED_SLEEP_FLAG)

        speed = speed_state & RUNNING_SPEED_MASK
        # Override order as in the vendor app: advanced bump, then boost, then Sleep.
        if advanced and 1 < speed < 5:
            speed += 1
        if boost:
            speed = 5
        if sleep:
            speed = 1

        mode = mode_state & 0x0F
        self.state.operating_mode = self._decode(
            "running mode",
            mode,
            {
                MODE_OFF: "off",
                MODE_IN: "in",
                MODE_OUT: "out",
                MODE_IN_OUT: "in_out",
                MODE_SENSOR_AUTO: "auto" if profiled else "sensor",
            },
        )
        if mode == MODE_OFF:
            self.state.speed_level = "off"
            self.state.running_speed = None
            return
        self.state.speed_level = self._decode(
            "running speed", speed, VALUE_TO_SPEED_LEVEL
        )
        self.state.running_speed = min(speed, 4) if speed >= 1 else None

    def _parse_oper(self, data: bytes) -> None:
        if len(data) < 2:
            self._clear_oper()
            return
        mode = data[0]
        raw_speed = data[1]

        speed = raw_speed & 0x0F
        self.state.commanded_speed = speed if 1 <= speed <= 4 else None

        if mode == MODE_OFF:
            self.state.is_on = False
            self.state.preset = None
            return
        self.state.is_on = True
        if mode == MODE_SENSOR_AUTO:
            preset = PRESET_AUTO if (raw_speed & SPEED_AUTO_FLAG) else PRESET_SENSOR
        else:
            preset = self._decode(
                "operating mode",
                mode,
                {MODE_IN: PRESET_IN, MODE_OUT: PRESET_OUT, MODE_IN_OUT: PRESET_IN_OUT},
            )
        self.state.preset = preset

        # Keep the desired command in sync with reality, so a speed-only
        # change keeps the preset and vice versa.
        if preset is not None:
            self.desired_preset_name = preset
        if 1 <= speed <= 4:
            self.desired_speed = speed

    def _clear_oper(self) -> None:
        self.state.is_on = None
        self.state.preset = None
        self.state.commanded_speed = None

    def _parse_config(self, data: bytes) -> None:
        if len(data) < 5:
            self._clear_config()
            return
        self.state.role = self._decode("role", data[0], VALUE_TO_ROLE)

        # Thresholds are levels 0-3; anything else is undocumented and shown
        # as unknown (and not resent by a write of the other thresholds).
        hum_raw = data[1]
        hum_adv = hum_raw >= THRESHOLD_ADVANCED_FLAG
        hum_base = hum_raw - THRESHOLD_ADVANCED_FLAG if hum_adv else hum_raw
        self.state.humidity_threshold = hum_base if hum_base <= 3 else None
        self.state.humidity_advanced = hum_adv

        lum = data[2]
        self.state.luminosity_threshold = lum if lum <= 3 else None

        voc_raw = data[3]
        voc_adv = voc_raw >= THRESHOLD_ADVANCED_FLAG
        voc_base = voc_raw - THRESHOLD_ADVANCED_FLAG if voc_adv else voc_raw
        self.state.voc_threshold = voc_base if voc_base <= 3 else None
        self.state.voc_advanced = voc_adv

        self.desired_humidity_threshold = self.state.humidity_threshold
        self.desired_humidity_advanced = hum_adv
        self.desired_luminosity_threshold = self.state.luminosity_threshold
        self.desired_voc_threshold = self.state.voc_threshold
        self.desired_voc_advanced = voc_adv
        if len(data) >= 12:
            self._config_address = bytes(data[6:12])

        # Byte 4: season in the high nibble (0 winter, 1 summer), free cooling
        # level in the low nibble. Matches the write values: 0x1F = summer
        # keeping free cooling (0xF = keep), 0x00 = winter with free cooling
        # off, 0x70 + level = keep season (0x7 = keep) and set free cooling.
        byte4 = data[4]
        self.state.season = self._decode(
            "season", byte4 >> 4, {0: SEASON_WINTER, 1: SEASON_SUMMER}
        )
        self.state.free_cooling = self._decode(
            "free cooling", byte4 & 0x0F, VALUE_TO_FREE_COOLING
        )

    def _clear_config(self) -> None:
        self.state.role = None
        self.state.humidity_threshold = None
        self.state.humidity_advanced = None
        self.state.luminosity_threshold = None
        self.state.voc_threshold = None
        self.state.voc_advanced = None
        self.state.season = None
        self.state.free_cooling = None

    def _parse_advanced(self, data: bytes) -> None:
        if len(data) < 4:
            self._clear_advanced()
            return
        temp = int.from_bytes(data[0:2], "big", signed=True) / 100.0
        humidity = int.from_bytes(data[2:4], "big", signed=True) / 100.0
        self.state.temp_offset = temp
        self.state.humidity_offset = humidity
        self.desired_temp_offset = temp
        self.desired_humidity_offset = humidity

    def _clear_advanced(self) -> None:
        self.state.temp_offset = None
        self.state.humidity_offset = None

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------
    async def _run_bounded_locked(
        self, command: Awaitable[None], timeout: float = COMMAND_TIMEOUT
    ) -> None:
        """Run a command under a hard timeout, dropping the link if it fails."""
        try:
            async with asyncio.timeout(timeout):
                await command
        except Exception:
            # Don't leave a possibly broken link for the next command.
            await self._disconnect_locked()
            raise

    async def _write_locked(self, char: str, value: bytes) -> None:
        await self._run_bounded_locked(self._write_command_locked(char, value))

    async def _write_command_locked(self, char: str, value: bytes) -> None:
        await self._ensure_connected()
        _LOGGER.debug("Writing %s <- %s", char, value.hex())

        async def write(client: BleakClientWithServiceCache) -> None:
            await client.write_gatt_char(char, value)

        try:
            await self._gatt_locked(write)
        except BleakError as err:
            if "not permitted" not in str(err).lower():
                raise
            # ATT 0x03: the attribute we wrote to isn't writable at all. Most
            # likely a stale service map pointing at the wrong handle, so
            # rediscover and retry once.
            self._log_characteristic(char, err)
            await self._rediscover_locked()
            await self._gatt_locked(write)

    def _log_characteristic(self, char: str, err: Exception) -> None:
        """Log how the device describes a characteristic, for diagnosing errors."""
        services = self._client.services if self._client is not None else None
        characteristic = services.get_characteristic(char) if services else None
        if characteristic is None:
            _LOGGER.warning(
                "%s: %s rejected (%s); characteristic not in service table",
                self.label,
                CHAR_NAMES[char],
                err,
            )
            return
        _LOGGER.warning(
            "%s: %s rejected (%s); handle=%s properties=%s. Rediscovering "
            "services and retrying",
            self.label,
            CHAR_NAMES[char],
            err,
            characteristic.handle,
            ",".join(characteristic.properties),
        )

    async def _clear_cache_locked(self) -> None:
        """Drop cached services (in HA and on the proxy). Never raises."""
        if self._client is None:
            return
        try:
            await self._client.clear_cache()
        except (BleakError, NotImplementedError, TimeoutError) as err:
            _LOGGER.debug("Clearing GATT cache for %s failed: %s", self.label, err)

    async def _rediscover_locked(self) -> None:
        """Drop cached services and reconnect."""
        if self.connected:
            await self._clear_cache_locked()
        await self._disconnect_locked()
        await self._ensure_connected()

    # The send methods take the change itself and merge it with the last
    # readback under the lock: setting desired_* before waiting for the lock
    # let a poll in progress overwrite the change with the old value.
    async def async_send_operation(
        self, preset: str | None = None, speed: int | None = None
    ) -> None:
        """Write a preset and/or speed, keeping the other as last read.

        A speed on its own in Auto switches to Sensor at that speed: Auto has
        no manual speed (the unit ignores it), and Sensor shares Auto's mode
        byte, so the unit keeps reacting to its sensors.
        """
        async with self._lock:
            if (
                preset is None
                and speed is not None
                and self.desired_preset_name == PRESET_AUTO
            ):
                preset = PRESET_SENSOR
            preset = preset or self.desired_preset_name
            speed = self.desired_speed if speed is None else speed
            # "Auto" hands the speed to the unit: speed byte = auto flag.
            speed_byte = SPEED_AUTO_FLAG if preset == PRESET_AUTO else speed
            await self._write_locked(
                CHAR_OPER, bytes([PRESET_TO_MODE[preset], speed_byte])
            )
            self.desired_preset_name = preset
            self.desired_speed = speed

    async def async_send_off(self) -> None:
        """Turn the unit off."""
        async with self._lock:
            await self._write_locked(CHAR_OPER, bytes([MODE_OFF, MODE_OFF]))

    def _config_command(
        self,
        thresholds: tuple[int, int, int] = (CONFIG_PRESERVE,) * 3,
        byte4: int = CONFIG_PRESERVE,
    ) -> bytes:
        """Build a C_CONFIGURATION write that changes only the given bytes.

        Role (byte 0) and rotation (byte 5) are kept with 0x7F. Bytes 6-11
        (a satellite's main-unit address) are sent back as last read: the
        original package wrote zeros there, and nothing documents whether
        0x7F means "keep" in those bytes too.
        """
        if self._config_address is None:
            raise HomeAssistantError(
                _NOT_READ_YET.format(what="configuration settings")
            )
        return (
            bytes([CONFIG_PRESERVE, *thresholds, byte4, CONFIG_PRESERVE])
            + self._config_address
        )

    async def async_write_season(self, season: str) -> None:
        """Write the season, preserving the rest of the configuration."""
        season_byte = (
            SEASON_WRITE_SUMMER if season == SEASON_SUMMER else SEASON_WRITE_WINTER
        )
        async with self._lock:
            await self._write_locked(
                CHAR_CONFIG, self._config_command(byte4=season_byte)
            )

    async def async_write_free_cooling(self, level: str) -> None:
        """Write the free cooling level, preserving the season bit."""
        byte4 = FREE_COOLING_WRITE_PREFIX + FREE_COOLING_TO_VALUE[level]
        async with self._lock:
            await self._write_locked(CHAR_CONFIG, self._config_command(byte4=byte4))

    async def async_send_thresholds(
        self,
        *,
        humidity: int | None = None,
        humidity_advanced: bool | None = None,
        luminosity: int | None = None,
        voc: int | None = None,
        voc_advanced: bool | None = None,
    ) -> None:
        """Change thresholds; all of them are written in one command."""
        async with self._lock:
            hum = _pick(humidity, self.desired_humidity_threshold)
            hum_adv = _pick(humidity_advanced, self.desired_humidity_advanced)
            lum = _pick(luminosity, self.desired_luminosity_threshold)
            voc_level = _pick(voc, self.desired_voc_threshold)
            voc_adv = _pick(voc_advanced, self.desired_voc_advanced)
            if None in (hum, hum_adv, lum, voc_level, voc_adv):
                raise HomeAssistantError(_NOT_READ_YET.format(what="thresholds"))
            value = self._config_command(
                (
                    hum + (THRESHOLD_ADVANCED_FLAG if hum_adv else 0),
                    lum,
                    voc_level + (THRESHOLD_ADVANCED_FLAG if voc_adv else 0),
                )
            )
            await self._write_locked(CHAR_CONFIG, value)
            self.desired_humidity_threshold = hum
            self.desired_humidity_advanced = hum_adv
            self.desired_luminosity_threshold = lum
            self.desired_voc_threshold = voc_level
            self.desired_voc_advanced = voc_adv

    async def async_send_offsets(
        self, *, temp: float | None = None, humidity: float | None = None
    ) -> None:
        """Change calibration offsets; both are written in one command."""
        async with self._lock:
            temp = _pick(temp, self.desired_temp_offset)
            humidity = _pick(humidity, self.desired_humidity_offset)
            if temp is None or humidity is None:
                raise HomeAssistantError(
                    _NOT_READ_YET.format(what="calibration offsets")
                )
            # round(), not int(): int(2.3 * 100) is 229.
            value = round(temp * 100).to_bytes(2, "big", signed=True) + round(
                humidity * 100
            ).to_bytes(2, "big", signed=True)
            await self._write_locked(CHAR_ADVANCED, value)
            self.desired_temp_offset = temp
            self.desired_humidity_offset = humidity

    async def async_pair(self) -> None:
        """Connect and pair fresh (the Pair button).

        Raises BleakError if pairing doesn't succeed (TimeoutError if the
        whole attempt overruns), so the user gets feedback. The VMC must be in
        pairing mode.

        Doesn't unpair first: the original ESPHome package this protocol is
        based on never does either, calling pair() unconditionally on every
        connect (cheap/instant if already bonded). Unpairing first only adds
        a round trip, and a possible reconnect if the backend drops the link
        on unpair, against the VMC's short pairing-mode window.
        """
        async with self._lock:
            await self._run_bounded_locked(
                self._pair_fresh_locked(), PAIR_BUTTON_TIMEOUT
            )

    async def _pair_fresh_locked(self) -> None:
        await self._disconnect_locked()
        self._pairing_unsupported = False
        self._pair_retry_at = 0.0
        await self._connect_locked()
        if not await self._pair_locked():
            raise BleakError(
                f"Pairing with {self.label} failed; put the VMC in pairing "
                "mode (hold its button ~5s until the LED blinks) and try again"
            )
        self._failing.clear()
        await self._write_clock_locked()

    async def _write_clock_locked(self) -> None:
        now = dt_util.now()
        # Device day-of-week: 0 = Monday .. 6 = Sunday, matching datetime.weekday().
        value = bytes(
            [
                now.year % 100,
                now.month,
                now.day,
                now.weekday(),
                now.hour,
                now.minute,
                now.second,
                0x00,
            ]
        )
        try:
            await self._gatt_locked(
                lambda client: client.write_gatt_char(CHAR_CLOCK, value)
            )
        except (BleakError, TimeoutError) as err:
            _LOGGER.debug("Clock sync failed for %s: %s", self.label, err)
            if not self.connected:
                return  # the link dropped: try again on the next poll
        # Also recorded when the unit refuses, so one that always refuses is
        # retried hourly rather than on every poll.
        self.last_clock_sync = dt_util.utcnow()
