"""Tests for EcocomfortDevice BLE communication."""
import struct
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ecocomfort2.ecocomfort import EcocomfortDevice, EcocomfortState
from tests.conftest import MAC_ADDRESS, make_info_bytes, make_oper_bytes, make_state_bytes


class TestEcocomfortState:
    def test_defaults_are_none(self):
        state = EcocomfortState()
        assert state.temperature is None
        assert state.humidity is None
        assert state.voc is None
        assert state.direction is None
        assert state.operating_mode is None
        assert state.firmware is None
        assert state.serial is None


class TestParseInfo:
    def test_parses_firmware_version(self, device):
        device._parse_info(make_info_bytes(1, 2, 3))
        assert device.state.firmware == "1.2.3"

    def test_parses_serial_as_hex(self, device):
        device._parse_info(make_info_bytes(serial_hex="DEADBEEF"))
        assert device.state.serial == "DEADBEEF"

    def test_ignores_short_payload(self, device):
        device._parse_info(b"\x01\x02\x03")  # 3 bytes, needs >= 8
        assert device.state.firmware is None
        assert device.state.serial is None

    def test_exact_8_bytes(self, device):
        data = bytes([2, 0, 5, 0]) + bytes([0xAA, 0xBB, 0xCC, 0xDD])
        device._parse_info(data)
        assert device.state.firmware == "2.0.5"
        assert device.state.serial == "AABBCCDD"

    def test_longer_payload_uses_all_serial_bytes(self, device):
        data = bytes([1, 0, 0, 0]) + bytes([0x01, 0x02, 0x03, 0x04, 0x05])
        device._parse_info(data)
        assert device.state.serial == "0102030405"


class TestParseState:
    def test_positive_temperature(self, device):
        device._parse_state(make_state_bytes(temp_c=21.5))
        assert device.state.temperature == pytest.approx(21.5)

    def test_negative_temperature(self, device):
        device._parse_state(make_state_bytes(temp_c=-5.3))
        assert device.state.temperature == pytest.approx(-5.3)

    def test_zero_temperature(self, device):
        device._parse_state(make_state_bytes(temp_c=0.0))
        assert device.state.temperature == pytest.approx(0.0)

    def test_humidity(self, device):
        device._parse_state(make_state_bytes(humidity=72))
        assert device.state.humidity == 72

    def test_humidity_boundaries(self, device):
        device._parse_state(make_state_bytes(humidity=0))
        assert device.state.humidity == 0
        device._parse_state(make_state_bytes(humidity=100))
        assert device.state.humidity == 100

    def test_voc(self, device):
        device._parse_state(make_state_bytes(voc=350))
        assert device.state.voc == 350

    def test_direction(self, device):
        device._parse_state(make_state_bytes(direction=3))
        assert device.state.direction == 3

    def test_ignores_short_payload(self, device):
        device._parse_state(b"\x00\x00\x00")  # < 8 bytes
        assert device.state.temperature is None


class TestParseOperatingMode:
    def test_mode_zero(self, device):
        device._parse_operating_mode(make_oper_bytes(0))
        assert device.state.operating_mode == 0

    def test_mode_fan(self, device):
        device._parse_operating_mode(make_oper_bytes(1))
        assert device.state.operating_mode == 1

    def test_mode_auto(self, device):
        device._parse_operating_mode(make_oper_bytes(4))
        assert device.state.operating_mode == 4

    def test_ignores_single_byte(self, device):
        device._parse_operating_mode(b"\x02")  # needs >= 2 bytes
        assert device.state.operating_mode is None

    def test_little_endian_word(self, device):
        # High byte non-zero to confirm little-endian parsing
        data = struct.pack("<H", 0x0102)
        device._parse_operating_mode(data)
        assert device.state.operating_mode == 0x0102


class TestAsyncConnect:
    async def test_returns_true_on_success(self):
        dev = EcocomfortDevice(MAC_ADDRESS)
        mock_client = AsyncMock()
        with patch("custom_components.ecocomfort2.ecocomfort.BleakClient", return_value=mock_client):
            result = await dev.async_connect()
        assert result is True
        mock_client.connect.assert_awaited_once()

    async def test_returns_false_on_exception(self):
        dev = EcocomfortDevice(MAC_ADDRESS)
        mock_client = AsyncMock()
        mock_client.connect.side_effect = OSError("unreachable")
        with patch("custom_components.ecocomfort2.ecocomfort.BleakClient", return_value=mock_client):
            result = await dev.async_connect()
        assert result is False


class TestAsyncDisconnect:
    async def test_disconnects_when_connected(self, device):
        device.client.is_connected = True
        await device.async_disconnect()
        device.client.disconnect.assert_awaited_once()

    async def test_skips_when_not_connected(self, device):
        device.client.is_connected = False
        await device.async_disconnect()
        device.client.disconnect.assert_not_awaited()

    async def test_skips_when_no_client(self):
        dev = EcocomfortDevice(MAC_ADDRESS)
        dev.client = None
        await dev.async_disconnect()  # must not raise


class TestAsyncUpdate:
    async def test_reads_all_three_characteristics(self, device):
        device.client.read_gatt_char.side_effect = [
            make_info_bytes(1, 0, 0),
            make_state_bytes(temp_c=20.0, humidity=50, voc=200, direction=1),
            make_oper_bytes(2),
        ]

        state = await device.async_update()

        assert device.client.read_gatt_char.await_count == 3
        assert state.firmware == "1.0.0"
        assert state.temperature == pytest.approx(20.0)
        assert state.humidity == 50
        assert state.voc == 200
        assert state.direction == 1
        assert state.operating_mode == 2

    async def test_syncs_clock(self, device):
        device.client.read_gatt_char.side_effect = [
            make_info_bytes(),
            make_state_bytes(),
            make_oper_bytes(),
        ]
        await device.async_update()
        device.client.write_gatt_char.assert_awaited_once()

    async def test_connects_when_client_missing(self):
        dev = EcocomfortDevice(MAC_ADDRESS)
        mock_client = AsyncMock()
        mock_client.is_connected = True
        mock_client.read_gatt_char.side_effect = [
            make_info_bytes(),
            make_state_bytes(),
            make_oper_bytes(),
        ]
        with patch("custom_components.ecocomfort2.ecocomfort.BleakClient", return_value=mock_client):
            await dev.async_update()
        mock_client.connect.assert_awaited_once()

    async def test_returns_state_on_read_error(self, device):
        device.client.read_gatt_char.side_effect = OSError("BLE error")
        state = await device.async_update()
        assert isinstance(state, EcocomfortState)


class TestAsyncSetOperatingMode:
    async def test_writes_little_endian_mode(self, device):
        result = await device.async_set_operating_mode(3)
        assert result is True
        device.client.write_gatt_char.assert_awaited_once_with(
            EcocomfortDevice.CHAR_SETTING_OPER, struct.pack("<H", 3)
        )

    async def test_updates_state_on_success(self, device):
        await device.async_set_operating_mode(2)
        assert device.state.operating_mode == 2

    async def test_returns_false_on_ble_error(self, device):
        device.client.write_gatt_char.side_effect = OSError("write failed")
        result = await device.async_set_operating_mode(1)
        assert result is False


class TestAsyncSetConfiguration:
    async def test_writes_12_bytes(self, device):
        config = bytes(12)
        result = await device.async_set_configuration(config)
        assert result is True
        device.client.write_gatt_char.assert_awaited_once_with(
            EcocomfortDevice.CHAR_CONFIGURATION, config
        )

    async def test_rejects_wrong_length(self, device):
        result = await device.async_set_configuration(bytes(8))
        assert result is False
        device.client.write_gatt_char.assert_not_awaited()

    async def test_returns_false_on_ble_error(self, device):
        device.client.write_gatt_char.side_effect = OSError("write failed")
        result = await device.async_set_configuration(bytes(12))
        assert result is False


class TestAsyncSetAdvanced:
    async def test_writes_4_bytes(self, device):
        calibration = bytes([0x01, 0x02, 0x03, 0x04])
        result = await device.async_set_advanced(calibration)
        assert result is True
        device.client.write_gatt_char.assert_awaited_once_with(
            EcocomfortDevice.CHAR_ADVANCED, calibration
        )

    async def test_rejects_wrong_length(self, device):
        result = await device.async_set_advanced(bytes(3))
        assert result is False
        device.client.write_gatt_char.assert_not_awaited()

    async def test_returns_false_on_ble_error(self, device):
        device.client.write_gatt_char.side_effect = OSError("write failed")
        result = await device.async_set_advanced(bytes(4))
        assert result is False


class TestSyncClock:
    async def test_clock_payload_format(self, device):
        fixed_now = datetime(2024, 6, 15, 10, 30, 45)  # Saturday → weekday() == 5
        with patch("custom_components.ecocomfort2.ecocomfort.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_now
            await device._sync_clock_if_needed()

        call_args = device.client.write_gatt_char.call_args
        char_uuid, payload = call_args[0]
        assert char_uuid == EcocomfortDevice.CHAR_SETTING_CLOCK
        assert len(payload) == 8
        assert payload[0] == 24   # year % 100
        assert payload[1] == 6    # month
        assert payload[2] == 15   # day
        assert payload[3] == 10   # hour
        assert payload[4] == 30   # minute
        assert payload[5] == 45   # second
        assert payload[6] == 5    # weekday (Saturday)
        assert payload[7] == 0    # padding

    async def test_swallows_ble_error(self, device):
        device.client.write_gatt_char.side_effect = OSError("write failed")
        await device._sync_clock_if_needed()  # must not raise
