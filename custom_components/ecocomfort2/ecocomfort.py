"""Ecocomfort 2 BLE device communication."""
import struct
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from bleak import BleakClient

# Speed code → HA percentage
SPEED_TO_PCT = {1: 25, 2: 50, 3: 75, 4: 100}
PCT_TO_SPEED = {25: 1, 50: 2, 75: 3, 100: 4}

# Operating mode byte → preset name
MODE_TO_PRESET = {1: "In", 2: "Out", 3: "In-Out", 4: "Sensor"}
PRESET_TO_MODE = {"In": 1, "Out": 2, "In-Out": 3, "Sensor": 4}

SEASON_WINTER = 0
SEASON_SUMMER = 1

FREE_COOLING_OFF = 0
FREE_COOLING_LOW = 1     # 2°C delta
FREE_COOLING_MEDIUM = 2  # 4°C delta
FREE_COOLING_HIGH = 3    # 6°C delta


@dataclass
class EcocomfortState:
    """Current device state — mirrors all readable characteristics."""

    # C_STATE
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    voc: Optional[int] = None
    direction: Optional[int] = None

    # C_SETTING_OPER
    operating_mode: Optional[int] = None   # 0=Off, 1=In, 2=Out, 3=In-Out, 4=Sensor
    speed: Optional[int] = None            # 1=Sleep, 2=Vel1, 3=Vel2, 4=Vel3
    boost_active: bool = False
    auto_mode: bool = False
    night_mode: bool = False

    # C_INFO
    firmware: Optional[str] = None
    serial: Optional[str] = None

    # C_CONFIGURATION
    role: Optional[int] = None
    humidity_threshold: Optional[int] = None   # 0-3
    humidity_advanced: bool = False
    luminosity_threshold: Optional[int] = None  # 0-3
    voc_threshold: Optional[int] = None        # 0-3
    voc_advanced: bool = False
    free_cooling: Optional[int] = None          # 0-3
    season: Optional[int] = None               # 0=Winter, 1=Summer

    # C_ADVANCED
    temp_offset: Optional[float] = None
    hum_offset: Optional[float] = None

    # Connectivity
    connected: bool = False


class EcocomfortDevice:
    """BLE interface for Fantini Cosmi Ecocomfort 2."""

    SERVICE_UUID = "f4b827c3-e660-4bc8-bdf6-3c8e9b845e0d"
    CHAR_INFO = "f5f56229-dd4f-480f-a829-9189269d8b37"
    CHAR_STATE = "438d3433-7e5a-459a-a8e4-66343fad2bb0"
    CHAR_SETTING_OPER = "b9d6f678-bc0d-4a73-90c8-60b0f07301f1"
    CHAR_CONFIGURATION = "d3dac48e-b4e1-4f3a-8715-326ddf1da89a"
    CHAR_SETTING_CLOCK = "82788997-49e4-4533-b949-7ed433678044"
    CHAR_ADVANCED = "f8b2284e-61dd-44e3-a782-a93c9503ab2d"
    CHAR_PROGRAMS = "TODO"   # 168-byte weekly schedule, not yet implemented
    CHAR_STATS = "TODO"      # Usage statistics, read-only, not yet implemented

    def __init__(self, mac_address: str) -> None:
        self.mac_address = mac_address
        self.client: Optional[BleakClient] = None
        self.state = EcocomfortState()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    async def async_connect(self) -> bool:
        try:
            self.client = BleakClient(self.mac_address)
            await self.client.connect()
            self.state.connected = True
            return True
        except Exception as exc:
            self.state.connected = False
            print(f"Failed to connect to {self.mac_address}: {exc}")
            return False

    async def async_disconnect(self) -> None:
        if self.client and self.client.is_connected:
            await self.client.disconnect()
        self.state.connected = False

    # ------------------------------------------------------------------
    # State update
    # ------------------------------------------------------------------

    async def async_update(self) -> EcocomfortState:
        """Read all characteristics and return updated state."""
        if not self.client or not self.client.is_connected:
            connected = await self.async_connect()
            if not connected:
                return self.state

        try:
            self._parse_info(await self.client.read_gatt_char(self.CHAR_INFO))
            self._parse_state(await self.client.read_gatt_char(self.CHAR_STATE))
            self._parse_operating_mode(await self.client.read_gatt_char(self.CHAR_SETTING_OPER))
            self._parse_configuration(await self.client.read_gatt_char(self.CHAR_CONFIGURATION))
            self._parse_advanced(await self.client.read_gatt_char(self.CHAR_ADVANCED))
            self.state.connected = True
            await self._sync_clock()
        except Exception as exc:
            self.state.connected = False
            print(f"Error updating device state: {exc}")

        return self.state

    # ------------------------------------------------------------------
    # Characteristic parsers
    # ------------------------------------------------------------------

    def _parse_info(self, data: bytes) -> None:
        """C_INFO: nibble-encoded firmware version + serial."""
        if len(data) < 2:
            return
        major = (data[0] >> 4) & 0x0F
        combined = ((data[0] & 0x0F) << 8) | data[1]
        minor = (combined >> 6) & 0x3F
        patch = combined & 0x3F
        self.state.firmware = f"{major}.{minor}.{patch}"
        if len(data) >= 8:
            self.state.serial = data[2:8].hex().upper()

    def _parse_state(self, data: bytes) -> None:
        """C_STATE: bytes 0-1 reserved, byte 2 direction, 3-4 temp, 5-6 humidity, 7-8 VOC."""
        if len(data) < 9:
            return
        self.state.direction = data[2]
        self.state.temperature = struct.unpack("<h", data[3:5])[0] / 100.0
        self.state.humidity = struct.unpack("<H", data[5:7])[0] / 100.0
        self.state.voc = struct.unpack("<H", data[7:9])[0]

    def _parse_operating_mode(self, data: bytes) -> None:
        """C_SETTING_OPER: byte 0 = mode, byte 1 = speed + flags."""
        if len(data) < 2:
            return
        self.state.operating_mode = data[0]
        speed_byte = data[1]
        self.state.boost_active = bool(speed_byte & 0x40)
        self.state.auto_mode = bool(speed_byte & 0x10)
        self.state.night_mode = bool(speed_byte & 0x80)
        raw_speed = speed_byte & 0x0F
        # Night mode forces Sleep; boost overrides to Vel3
        if speed_byte & 0x80:
            self.state.speed = 1
        elif self.state.boost_active:
            self.state.speed = 4
        else:
            self.state.speed = raw_speed

    def _parse_configuration(self, data: bytes) -> None:
        """C_CONFIGURATION: 12 bytes with thresholds, season, free cooling."""
        if len(data) < 5:
            return
        self.state.role = data[0]
        self.state.humidity_threshold = data[1] & 0x7F
        self.state.humidity_advanced = bool(data[1] & 0x80)
        self.state.luminosity_threshold = data[2]
        self.state.voc_threshold = data[3] & 0x7F
        self.state.voc_advanced = bool(data[3] & 0x80)
        byte4 = data[4]
        self.state.free_cooling = byte4 & 0x03
        self.state.season = SEASON_SUMMER if (byte4 & 0x08) else SEASON_WINTER

    def _parse_advanced(self, data: bytes) -> None:
        """C_ADVANCED: big-endian signed int16 × 100 for each offset."""
        if len(data) < 4:
            return
        self.state.temp_offset = struct.unpack(">h", data[0:2])[0] / 100.0
        self.state.hum_offset = struct.unpack(">h", data[2:4])[0] / 100.0

    # ------------------------------------------------------------------
    # Clock sync
    # ------------------------------------------------------------------

    async def _sync_clock(self) -> None:
        """Write current datetime to device clock characteristic."""
        try:
            now = datetime.now()
            clock_data = struct.pack(
                "BBBBBBBB",
                now.year % 100,
                now.month,
                now.day,
                now.hour,
                now.minute,
                now.second,
                now.weekday(),
                0,  # padding
            )
            await self.client.write_gatt_char(self.CHAR_SETTING_CLOCK, clock_data)
        except Exception as exc:
            print(f"Error syncing clock: {exc}")

    # ------------------------------------------------------------------
    # Write commands
    # ------------------------------------------------------------------

    async def async_set_operating_mode(self, mode: int, speed: int) -> bool:
        """Write operating mode and speed to C_SETTING_OPER."""
        if not await self._ensure_connected():
            return False
        try:
            await self.client.write_gatt_char(
                self.CHAR_SETTING_OPER, bytes([mode, speed])
            )
            self.state.operating_mode = mode
            self.state.speed = speed & 0x0F
            return True
        except Exception as exc:
            print(f"Error setting operating mode: {exc}")
            return False

    async def async_set_thresholds(
        self, humidity: int, luminosity: int, voc: int
    ) -> bool:
        """Write sensor activation thresholds (0-3), preserving other config bytes."""
        if not await self._ensure_connected():
            return False
        try:
            hum_byte = (humidity & 0x7F) | (0x80 if self.state.humidity_advanced else 0)
            voc_byte = (voc & 0x7F) | (0x80 if self.state.voc_advanced else 0)
            # 0x7F = preserve byte; bytes 6-11 (master MAC) set to 0x00
            data = bytes([0x7F, hum_byte, luminosity & 0xFF, voc_byte, 0x7F, 0x7F,
                          0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            await self.client.write_gatt_char(self.CHAR_CONFIGURATION, data)
            self.state.humidity_threshold = humidity
            self.state.luminosity_threshold = luminosity
            self.state.voc_threshold = voc
            return True
        except Exception as exc:
            print(f"Error setting thresholds: {exc}")
            return False

    async def async_set_humidity_advanced(self, advanced: bool) -> bool:
        """Toggle humidity advanced mode flag, preserving threshold value."""
        if self.state.humidity_threshold is None:
            return False
        return await self.async_set_thresholds(
            self.state.humidity_threshold,
            self.state.luminosity_threshold or 0,
            self.state.voc_threshold or 0,
        )

    async def async_set_voc_advanced(self, advanced: bool) -> bool:
        """Toggle VOC advanced mode flag, preserving threshold value."""
        # Update state flag first so async_set_thresholds picks it up
        self.state.voc_advanced = advanced
        if self.state.voc_threshold is None:
            return False
        return await self.async_set_thresholds(
            self.state.humidity_threshold or 0,
            self.state.luminosity_threshold or 0,
            self.state.voc_threshold,
        )

    async def async_set_season(self, season: int) -> bool:
        """Write season (SEASON_WINTER=0 / SEASON_SUMMER=1), preserving free-cooling bits."""
        if not await self._ensure_connected():
            return False
        try:
            fc_bits = (self.state.free_cooling or 0) & 0x03
            season_bit = 0x08 if season == SEASON_SUMMER else 0x00
            byte4 = fc_bits | season_bit
            data = bytes([0x7F, 0x7F, 0x7F, 0x7F, byte4, 0x7F,
                          0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            await self.client.write_gatt_char(self.CHAR_CONFIGURATION, data)
            self.state.season = season
            return True
        except Exception as exc:
            print(f"Error setting season: {exc}")
            return False

    async def async_set_free_cooling(self, level: int) -> bool:
        """Write free-cooling intensity (0=Off … 3=High), preserving season bit."""
        if not await self._ensure_connected():
            return False
        try:
            season_bit = 0x08 if self.state.season == SEASON_SUMMER else 0x00
            byte4 = (level & 0x03) | season_bit
            data = bytes([0x7F, 0x7F, 0x7F, 0x7F, byte4, 0x7F,
                          0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            await self.client.write_gatt_char(self.CHAR_CONFIGURATION, data)
            self.state.free_cooling = level
            return True
        except Exception as exc:
            print(f"Error setting free cooling: {exc}")
            return False

    async def async_set_offsets(self, temp_offset: float, hum_offset: float) -> bool:
        """Write calibration offsets to C_ADVANCED (big-endian int16 × 100)."""
        if not await self._ensure_connected():
            return False
        try:
            temp_raw = int(temp_offset * 100)
            hum_raw = int(hum_offset * 100)
            data = struct.pack(">hh", temp_raw, hum_raw)
            await self.client.write_gatt_char(self.CHAR_ADVANCED, data)
            self.state.temp_offset = temp_offset
            self.state.hum_offset = hum_offset
            return True
        except Exception as exc:
            print(f"Error setting offsets: {exc}")
            return False

    async def async_set_configuration(self, config: bytes) -> bool:
        """Write raw 12-byte configuration blob."""
        if len(config) != 12:
            return False
        if not await self._ensure_connected():
            return False
        try:
            await self.client.write_gatt_char(self.CHAR_CONFIGURATION, config)
            return True
        except Exception as exc:
            print(f"Error setting configuration: {exc}")
            return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _ensure_connected(self) -> bool:
        if self.client and self.client.is_connected:
            return True
        return await self.async_connect()
