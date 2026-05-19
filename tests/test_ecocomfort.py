"""Tests for EcocomfortDevice BLE communication."""
import struct
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.ecocomfort2.ecocomfort import (
    EcocomfortDevice,
    EcocomfortState,
    SEASON_SUMMER,
    SEASON_WINTER,
)
from tests.conftest import (
    MAC_ADDRESS,
    make_advanced_bytes,
    make_config_bytes,
    make_info_bytes,
    make_oper_bytes,
    make_state_bytes,
)


class TestEcocomfortState:
    def test_defaults_are_none(self):
        s = EcocomfortState()
        assert s.temperature is None
        assert s.humidity is None
        assert s.voc is None
        assert s.operating_mode is None
        assert s.speed is None
        assert s.firmware is None
        assert s.connected is False


# ---------------------------------------------------------------------------
# C_INFO
# ---------------------------------------------------------------------------

class TestParseInfo:
    def test_firmware_major_minor_patch(self, device):
        device._parse_info(make_info_bytes(major=1, minor=2, patch=3))
        assert device.state.firmware == "1.2.3"

    def test_zero_version(self, device):
        device._parse_info(make_info_bytes(major=0, minor=0, patch=0))
        assert device.state.firmware == "0.0.0"

    def test_large_minor_patch(self, device):
        device._parse_info(make_info_bytes(major=2, minor=63, patch=63))
        assert device.state.firmware == "2.63.63"

    def test_serial_parsed(self, device):
        device._parse_info(make_info_bytes(serial_hex="AABBCCDDEE00"))
        assert device.state.serial == "AABBCCDDEE00"

    def test_too_short_ignored(self, device):
        device._parse_info(b"\x01")  # < 2 bytes
        assert device.state.firmware is None


# ---------------------------------------------------------------------------
# C_STATE
# ---------------------------------------------------------------------------

class TestParseState:
    def test_temperature_positive(self, device):
        device._parse_state(make_state_bytes(temp_c=21.5))
        assert device.state.temperature == pytest.approx(21.5)

    def test_temperature_negative(self, device):
        device._parse_state(make_state_bytes(temp_c=-5.3))
        assert device.state.temperature == pytest.approx(-5.3, abs=0.01)

    def test_temperature_zero(self, device):
        device._parse_state(make_state_bytes(temp_c=0.0))
        assert device.state.temperature == pytest.approx(0.0)

    def test_humidity(self, device):
        device._parse_state(make_state_bytes(humidity_pct=72.5))
        assert device.state.humidity == pytest.approx(72.5)

    def test_voc(self, device):
        device._parse_state(make_state_bytes(voc=350))
        assert device.state.voc == 350

    def test_direction(self, device):
        device._parse_state(make_state_bytes(direction=3))
        assert device.state.direction == 3

    def test_too_short_ignored(self, device):
        device._parse_state(bytes(8))   # needs >= 9
        assert device.state.temperature is None


# ---------------------------------------------------------------------------
# C_SETTING_OPER
# ---------------------------------------------------------------------------

class TestParseOperatingMode:
    def test_mode_and_speed(self, device):
        device._parse_operating_mode(make_oper_bytes(mode=2, speed=3))
        assert device.state.operating_mode == 2
        assert device.state.speed == 3

    def test_boost_flag(self, device):
        device._parse_operating_mode(make_oper_bytes(speed=2, boost=True))
        assert device.state.boost_active is True
        assert device.state.speed == 4  # override to Vel3

    def test_night_flag_forces_sleep(self, device):
        device._parse_operating_mode(make_oper_bytes(speed=3, night=True))
        assert device.state.night_mode is True
        assert device.state.speed == 1  # override to Sleep

    def test_auto_flag(self, device):
        device._parse_operating_mode(make_oper_bytes(auto=True))
        assert device.state.auto_mode is True

    def test_off_mode(self, device):
        device._parse_operating_mode(make_oper_bytes(mode=0, speed=0))
        assert device.state.operating_mode == 0
        assert device.state.speed == 0

    def test_too_short_ignored(self, device):
        device._parse_operating_mode(b"\x01")
        assert device.state.operating_mode is None


# ---------------------------------------------------------------------------
# C_CONFIGURATION
# ---------------------------------------------------------------------------

class TestParseConfiguration:
    def test_basic_fields(self, device):
        device._parse_configuration(
            make_config_bytes(
                role=1,
                humidity_threshold=2,
                luminosity_threshold=3,
                voc_threshold=1,
                free_cooling=2,
                season=SEASON_SUMMER,
            )
        )
        assert device.state.role == 1
        assert device.state.humidity_threshold == 2
        assert device.state.luminosity_threshold == 3
        assert device.state.voc_threshold == 1
        assert device.state.free_cooling == 2
        assert device.state.season == SEASON_SUMMER

    def test_advanced_flags(self, device):
        device._parse_configuration(
            make_config_bytes(humidity_advanced=True, voc_advanced=True)
        )
        assert device.state.humidity_advanced is True
        assert device.state.voc_advanced is True

    def test_advanced_flags_off(self, device):
        device._parse_configuration(make_config_bytes())
        assert device.state.humidity_advanced is False
        assert device.state.voc_advanced is False

    def test_winter_season(self, device):
        device._parse_configuration(make_config_bytes(season=SEASON_WINTER))
        assert device.state.season == SEASON_WINTER

    def test_too_short_ignored(self, device):
        device._parse_configuration(bytes(4))  # needs >= 5
        assert device.state.humidity_threshold is None


# ---------------------------------------------------------------------------
# C_ADVANCED
# ---------------------------------------------------------------------------

class TestParseAdvanced:
    def test_positive_offsets(self, device):
        device._parse_advanced(make_advanced_bytes(temp_offset=1.5, hum_offset=2.0))
        assert device.state.temp_offset == pytest.approx(1.5)
        assert device.state.hum_offset == pytest.approx(2.0)

    def test_negative_offsets(self, device):
        device._parse_advanced(make_advanced_bytes(temp_offset=-1.5, hum_offset=-2.0))
        assert device.state.temp_offset == pytest.approx(-1.5)
        assert device.state.hum_offset == pytest.approx(-2.0)

    def test_zero_offsets(self, device):
        device._parse_advanced(make_advanced_bytes(0.0, 0.0))
        assert device.state.temp_offset == pytest.approx(0.0)
        assert device.state.hum_offset == pytest.approx(0.0)

    def test_big_endian(self, device):
        # +1.00°C = 100 = 0x0064 big-endian → bytes [0x00, 0x64, ...]
        data = bytes([0x00, 0x64, 0x00, 0x00])
        device._parse_advanced(data)
        assert device.state.temp_offset == pytest.approx(1.0)

    def test_too_short_ignored(self, device):
        device._parse_advanced(bytes(3))
        assert device.state.temp_offset is None


# ---------------------------------------------------------------------------
# Connect / Disconnect
# ---------------------------------------------------------------------------

class TestAsyncConnect:
    async def test_returns_true_on_success(self):
        dev = EcocomfortDevice(None, MAC_ADDRESS)
        mock_client = AsyncMock()
        with patch("custom_components.ecocomfort2.ecocomfort.BleakClient", return_value=mock_client):
            result = await dev.async_connect()
        assert result is True
        assert dev.state.connected is True

    async def test_returns_false_on_exception(self):
        dev = EcocomfortDevice(None, MAC_ADDRESS)
        mock_client = AsyncMock()
        mock_client.connect.side_effect = OSError("unreachable")
        with patch("custom_components.ecocomfort2.ecocomfort.BleakClient", return_value=mock_client):
            result = await dev.async_connect()
        assert result is False
        assert dev.state.connected is False


class TestAsyncDisconnect:
    async def test_disconnects_when_connected(self, device):
        device.client.is_connected = True
        await device.async_disconnect()
        device.client.disconnect.assert_awaited_once()
        assert device.state.connected is False

    async def test_skips_when_not_connected(self, device):
        device.client.is_connected = False
        await device.async_disconnect()
        device.client.disconnect.assert_not_awaited()

    async def test_skips_when_no_client(self):
        dev = EcocomfortDevice(None, MAC_ADDRESS)
        dev.client = None
        await dev.async_disconnect()


# ---------------------------------------------------------------------------
# async_update
# ---------------------------------------------------------------------------

class TestAsyncUpdate:
    async def test_reads_five_characteristics(self, device):
        device.client.read_gatt_char.side_effect = [
            make_info_bytes(1, 0, 0),
            make_state_bytes(temp_c=20.0, humidity_pct=50.0, voc=200, direction=1),
            make_oper_bytes(mode=2, speed=3),
            make_config_bytes(humidity_threshold=2, season=SEASON_SUMMER),
            make_advanced_bytes(temp_offset=0.5, hum_offset=-0.5),
        ]
        state = await device.async_update()
        assert device.client.read_gatt_char.await_count == 5
        assert state.firmware == "1.0.0"
        assert state.temperature == pytest.approx(20.0)
        assert state.humidity == pytest.approx(50.0)
        assert state.voc == 200
        assert state.operating_mode == 2
        assert state.speed == 3
        assert state.humidity_threshold == 2
        assert state.season == SEASON_SUMMER
        assert state.temp_offset == pytest.approx(0.5)

    async def test_syncs_clock(self, device):
        device.client.read_gatt_char.side_effect = [
            make_info_bytes(), make_state_bytes(), make_oper_bytes(),
            make_config_bytes(), make_advanced_bytes(),
        ]
        await device.async_update()
        device.client.write_gatt_char.assert_awaited_once()

    async def test_returns_state_on_read_error(self, device):
        device.client.read_gatt_char.side_effect = OSError("BLE error")
        state = await device.async_update()
        assert isinstance(state, EcocomfortState)
        assert state.connected is False


# ---------------------------------------------------------------------------
# Write commands
# ---------------------------------------------------------------------------

class TestAsyncSetOperatingMode:
    async def test_writes_two_bytes(self, device):
        await device.async_set_operating_mode(3, 2)
        device.client.write_gatt_char.assert_awaited_once_with(
            EcocomfortDevice.CHAR_SETTING_OPER, bytes([3, 2])
        )

    async def test_updates_state(self, device):
        await device.async_set_operating_mode(2, 3)
        assert device.state.operating_mode == 2
        assert device.state.speed == 3

    async def test_returns_false_on_error(self, device):
        device.client.write_gatt_char.side_effect = OSError("fail")
        assert await device.async_set_operating_mode(1, 1) is False


class TestAsyncSetThresholds:
    async def test_writes_with_preserve_markers(self, device):
        device.state.humidity_advanced = False
        device.state.voc_advanced = False
        await device.async_set_thresholds(2, 1, 3)
        call_args = device.client.write_gatt_char.call_args[0]
        data = call_args[1]
        assert data[0] == 0x7F  # role preserved
        assert data[1] == 2     # humidity threshold
        assert data[2] == 1     # luminosity threshold
        assert data[3] == 3     # VOC threshold
        assert data[4] == 0x7F  # byte4 preserved

    async def test_advanced_flag_in_threshold_byte(self, device):
        device.state.humidity_advanced = True
        device.state.voc_advanced = False
        await device.async_set_thresholds(2, 0, 1)
        data = device.client.write_gatt_char.call_args[0][1]
        assert data[1] == 2 | 0x80  # advanced flag set

    async def test_updates_state(self, device):
        device.state.humidity_advanced = False
        device.state.voc_advanced = False
        await device.async_set_thresholds(1, 2, 3)
        assert device.state.humidity_threshold == 1
        assert device.state.luminosity_threshold == 2
        assert device.state.voc_threshold == 3

    async def test_returns_false_on_error(self, device):
        device.client.write_gatt_char.side_effect = OSError("fail")
        assert await device.async_set_thresholds(0, 0, 0) is False


class TestAsyncSetSeason:
    async def test_summer_sets_bit3(self, device):
        device.state.free_cooling = 0
        await device.async_set_season(SEASON_SUMMER)
        data = device.client.write_gatt_char.call_args[0][1]
        assert data[4] & 0x08 != 0

    async def test_winter_clears_bit3(self, device):
        device.state.free_cooling = 0
        await device.async_set_season(SEASON_WINTER)
        data = device.client.write_gatt_char.call_args[0][1]
        assert data[4] & 0x08 == 0

    async def test_preserves_free_cooling_bits(self, device):
        device.state.free_cooling = 2  # Medium
        await device.async_set_season(SEASON_SUMMER)
        data = device.client.write_gatt_char.call_args[0][1]
        assert data[4] & 0x03 == 2

    async def test_other_bytes_are_preserve_markers(self, device):
        device.state.free_cooling = 0
        await device.async_set_season(SEASON_WINTER)
        data = device.client.write_gatt_char.call_args[0][1]
        assert data[0] == 0x7F
        assert data[1] == 0x7F

    async def test_updates_state(self, device):
        device.state.free_cooling = 0
        await device.async_set_season(SEASON_SUMMER)
        assert device.state.season == SEASON_SUMMER


class TestAsyncSetFreeCooling:
    async def test_level_written_to_bits_0_1(self, device):
        device.state.season = SEASON_WINTER
        await device.async_set_free_cooling(3)
        data = device.client.write_gatt_char.call_args[0][1]
        assert data[4] & 0x03 == 3

    async def test_preserves_season_bit(self, device):
        device.state.season = SEASON_SUMMER
        await device.async_set_free_cooling(1)
        data = device.client.write_gatt_char.call_args[0][1]
        assert data[4] & 0x08 != 0

    async def test_updates_state(self, device):
        device.state.season = SEASON_WINTER
        await device.async_set_free_cooling(2)
        assert device.state.free_cooling == 2


class TestAsyncSetOffsets:
    async def test_writes_big_endian(self, device):
        await device.async_set_offsets(1.0, -0.5)
        data = device.client.write_gatt_char.call_args[0][1]
        assert data == struct.pack(">hh", 100, -50)

    async def test_updates_state(self, device):
        await device.async_set_offsets(0.5, -1.0)
        assert device.state.temp_offset == pytest.approx(0.5)
        assert device.state.hum_offset == pytest.approx(-1.0)

    async def test_returns_false_on_error(self, device):
        device.client.write_gatt_char.side_effect = OSError("fail")
        assert await device.async_set_offsets(0.0, 0.0) is False


# ---------------------------------------------------------------------------
# Clock sync
# ---------------------------------------------------------------------------

class TestSyncClock:
    async def test_clock_payload(self, device):
        fixed = datetime(2024, 6, 15, 10, 30, 45)
        with patch("custom_components.ecocomfort2.ecocomfort.datetime") as mock_dt:
            mock_dt.now.return_value = fixed
            await device._sync_clock()
        _, payload = device.client.write_gatt_char.call_args[0]
        assert len(payload) == 8
        assert payload[0] == 24   # year % 100
        assert payload[1] == 6    # month
        assert payload[2] == 15   # day
        assert payload[3] == 10   # hour
        assert payload[4] == 30   # minute
        assert payload[5] == 45   # second
        assert payload[6] == fixed.weekday()
        assert payload[7] == 0    # padding

    async def test_swallows_ble_error(self, device):
        device.client.write_gatt_char.side_effect = OSError("fail")
        await device._sync_clock()  # must not raise
