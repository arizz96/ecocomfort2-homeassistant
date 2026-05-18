"""Ecocomfort 2 BLE device communication."""
import asyncio
import struct
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from bleak import BleakClient, BleakGATTCharacteristic


@dataclass
class EcocomfortState:
    """Current device state."""

    temperature: Optional[float] = None
    humidity: Optional[float] = None
    voc: Optional[int] = None
    direction: Optional[int] = None
    operating_mode: Optional[int] = None
    firmware: Optional[str] = None
    serial: Optional[str] = None


class EcocomfortDevice:
    """Interface to Ecocomfort 2 BLE device."""

    # Service and characteristic UUIDs
    SERVICE_UUID = "f4b827c3-e660-4bc8-bdf6-3c8e9b845e0d"
    CHAR_INFO = "f5f56229-dd4f-480f-a829-9189269d8b37"
    CHAR_STATE = "438d3433-7e5a-459a-a8e4-66343fad2bb0"
    CHAR_SETTING_OPER = "b9d6f678-bc0d-4a73-90c8-60b0f07301f1"
    CHAR_CONFIGURATION = "d3dac48e-b4e1-4f3a-8715-326ddf1da89a"
    CHAR_SETTING_CLOCK = "82788997-49e4-4533-b949-7ed433678044"
    CHAR_ADVANCED = "f8b2284e-61dd-44e3-a782-a93c9503ab2d"

    def __init__(self, mac_address: str):
        """Initialize the device."""
        self.mac_address = mac_address
        self.client: Optional[BleakClient] = None
        self.state = EcocomfortState()

    async def async_connect(self) -> bool:
        """Connect to the device."""
        try:
            self.client = BleakClient(self.mac_address)
            await self.client.connect()
            return True
        except Exception as e:
            print(f"Failed to connect to {self.mac_address}: {e}")
            return False

    async def async_disconnect(self) -> None:
        """Disconnect from the device."""
        if self.client and self.client.is_connected:
            await self.client.disconnect()

    async def async_update(self) -> EcocomfortState:
        """Update device state by reading all characteristics."""
        if not self.client or not self.client.is_connected:
            await self.async_connect()

        try:
            # Read device info
            info_data = await self.client.read_gatt_char(self.CHAR_INFO)
            self._parse_info(info_data)

            # Read current state
            state_data = await self.client.read_gatt_char(self.CHAR_STATE)
            self._parse_state(state_data)

            # Read operating mode
            oper_data = await self.client.read_gatt_char(self.CHAR_SETTING_OPER)
            self._parse_operating_mode(oper_data)

            # Sync clock on first read of the day
            await self._sync_clock_if_needed()

        except Exception as e:
            print(f"Error updating device state: {e}")

        return self.state

    def _parse_info(self, data: bytes) -> None:
        """Parse device info characteristic."""
        if len(data) >= 8:
            # Firmware version from first 4 bytes
            fw_bytes = data[:4]
            self.state.firmware = f"{fw_bytes[0]}.{fw_bytes[1]}.{fw_bytes[2]}"

            # Serial number from remaining bytes
            self.state.serial = data[4:].hex().upper()

    def _parse_state(self, data: bytes) -> None:
        """Parse device state characteristic."""
        if len(data) >= 8:
            # Temperature (bytes 0-1, signed int16, scaled by 0.1)
            temp_raw = struct.unpack("<h", data[0:2])[0]
            self.state.temperature = temp_raw / 10.0

            # Humidity (byte 2, uint8, 0-100%)
            self.state.humidity = data[2]

            # VOC (bytes 3-4, uint16)
            self.state.voc = struct.unpack("<H", data[3:5])[0]

            # Direction (byte 5, uint8)
            self.state.direction = data[5]

    def _parse_operating_mode(self, data: bytes) -> None:
        """Parse operating mode characteristic."""
        if len(data) >= 2:
            self.state.operating_mode = struct.unpack("<H", data[0:2])[0]

    async def _sync_clock_if_needed(self) -> None:
        """Sync device clock if needed."""
        try:
            now = datetime.now()
            # Clock sync format: YY, MM, DD, HH, MM, SS, DOW (day of week), padding
            clock_data = struct.pack(
                "<BBBBBBB",
                now.year % 100,
                now.month,
                now.day,
                now.hour,
                now.minute,
                now.second,
                now.weekday(),
            )
            clock_data += b"\x00"  # padding

            await self.client.write_gatt_char(self.CHAR_SETTING_CLOCK, clock_data)
        except Exception as e:
            print(f"Error syncing clock: {e}")

    async def async_set_operating_mode(self, mode: int) -> bool:
        """Set the operating mode."""
        if not self.client or not self.client.is_connected:
            await self.async_connect()

        try:
            mode_data = struct.pack("<H", mode)
            await self.client.write_gatt_char(self.CHAR_SETTING_OPER, mode_data)
            self.state.operating_mode = mode
            return True
        except Exception as e:
            print(f"Error setting operating mode: {e}")
            return False

    async def async_set_configuration(self, config: bytes) -> bool:
        """Set device configuration (12 bytes)."""
        if not self.client or not self.client.is_connected:
            await self.async_connect()

        if len(config) != 12:
            print("Configuration must be 12 bytes")
            return False

        try:
            await self.client.write_gatt_char(self.CHAR_CONFIGURATION, config)
            return True
        except Exception as e:
            print(f"Error setting configuration: {e}")
            return False

    async def async_set_advanced(self, calibration: bytes) -> bool:
        """Set advanced/calibration settings (4 bytes)."""
        if not self.client or not self.client.is_connected:
            await self.async_connect()

        if len(calibration) != 4:
            print("Calibration data must be 4 bytes")
            return False

        try:
            await self.client.write_gatt_char(self.CHAR_ADVANCED, calibration)
            return True
        except Exception as e:
            print(f"Error setting advanced settings: {e}")
            return False
