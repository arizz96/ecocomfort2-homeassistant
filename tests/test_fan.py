"""Tests for EcocomfortFan entity."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ecocomfort2.fan import EcocomfortFan, PRESET_MODES
from custom_components.ecocomfort2.ecocomfort import EcocomfortDevice, EcocomfortState
from tests.conftest import MAC_ADDRESS


def make_fan(operating_mode=1, speed=2, connected=True, boost=False, auto=False):
    coordinator = MagicMock()
    coordinator.async_request_refresh = AsyncMock()

    device = MagicMock(spec=EcocomfortDevice)
    device.state = EcocomfortState(
        operating_mode=operating_mode,
        speed=speed,
        connected=connected,
        boost_active=boost,
        auto_mode=auto,
    )
    device.async_set_operating_mode = AsyncMock(return_value=True)

    config_entry = MagicMock()
    config_entry.data = {"mac": MAC_ADDRESS}

    entity = EcocomfortFan(coordinator, device, config_entry)
    entity.coordinator = coordinator
    return entity


class TestIsOn:
    def test_on_when_mode_nonzero(self):
        assert make_fan(operating_mode=1).is_on is True

    def test_off_when_mode_zero(self):
        assert make_fan(operating_mode=0).is_on is False

    def test_off_when_mode_none(self):
        assert make_fan(operating_mode=None).is_on is False


class TestPercentage:
    @pytest.mark.parametrize("speed, expected_pct", [(1, 25), (2, 50), (3, 75), (4, 100)])
    def test_speed_to_percentage(self, speed, expected_pct):
        assert make_fan(speed=speed).percentage == expected_pct

    def test_none_when_speed_zero(self):
        assert make_fan(speed=0).percentage is None

    def test_none_when_speed_none(self):
        assert make_fan(speed=None).percentage is None


class TestPresetMode:
    @pytest.mark.parametrize("mode, expected", [(1, "In"), (2, "Out"), (3, "In-Out"), (4, "Sensor")])
    def test_mode_to_preset(self, mode, expected):
        assert make_fan(operating_mode=mode).preset_mode == expected

    def test_none_when_off(self):
        assert make_fan(operating_mode=0).preset_mode is None


class TestAvailable:
    def test_available_when_connected(self):
        assert make_fan(connected=True).available is True

    def test_unavailable_when_disconnected(self):
        assert make_fan(connected=False).available is False


class TestTurnOn:
    async def test_turns_on_with_default_mode(self):
        fan = make_fan(operating_mode=0, speed=2)
        await fan.async_turn_on()
        fan.device.async_set_operating_mode.assert_awaited_once()

    async def test_turn_on_with_preset(self):
        fan = make_fan(operating_mode=0, speed=2)
        await fan.async_turn_on(preset_mode="Out")
        args = fan.device.async_set_operating_mode.call_args[0]
        assert args[0] == 2  # Out

    async def test_turn_on_with_percentage(self):
        fan = make_fan(operating_mode=1, speed=1)
        await fan.async_turn_on(percentage=100)
        args = fan.device.async_set_operating_mode.call_args[0]
        assert args[1] == 4  # Vel3

    async def test_requests_refresh_on_success(self):
        fan = make_fan()
        await fan.async_turn_on()
        fan.coordinator.async_request_refresh.assert_awaited_once()

    async def test_no_refresh_on_failure(self):
        fan = make_fan()
        fan.device.async_set_operating_mode = AsyncMock(return_value=False)
        await fan.async_turn_on()
        fan.coordinator.async_request_refresh.assert_not_awaited()


class TestTurnOff:
    async def test_sets_mode_to_zero(self):
        fan = make_fan(operating_mode=2, speed=3)
        await fan.async_turn_off()
        fan.device.async_set_operating_mode.assert_awaited_once_with(0, 0)

    async def test_requests_refresh(self):
        fan = make_fan()
        await fan.async_turn_off()
        fan.coordinator.async_request_refresh.assert_awaited_once()


class TestSetPercentage:
    @pytest.mark.parametrize("pct, expected_speed", [(25, 1), (50, 2), (75, 3), (100, 4)])
    async def test_percentage_to_speed(self, pct, expected_speed):
        fan = make_fan(operating_mode=1, speed=2)
        await fan.async_set_percentage(pct)
        args = fan.device.async_set_operating_mode.call_args[0]
        assert args[1] == expected_speed

    async def test_keeps_current_mode(self):
        fan = make_fan(operating_mode=3, speed=2)
        await fan.async_set_percentage(75)
        args = fan.device.async_set_operating_mode.call_args[0]
        assert args[0] == 3  # In-Out preserved


class TestSetPresetMode:
    @pytest.mark.parametrize("preset, expected_mode", [
        ("In", 1), ("Out", 2), ("In-Out", 3), ("Sensor", 4)
    ])
    async def test_preset_to_mode(self, preset, expected_mode):
        fan = make_fan(operating_mode=1, speed=2)
        await fan.async_set_preset_mode(preset)
        args = fan.device.async_set_operating_mode.call_args[0]
        assert args[0] == expected_mode

    async def test_keeps_current_speed(self):
        fan = make_fan(operating_mode=1, speed=3)
        await fan.async_set_preset_mode("Out")
        args = fan.device.async_set_operating_mode.call_args[0]
        assert args[1] == 3  # Vel2 preserved

    async def test_ignores_unknown_preset(self):
        fan = make_fan()
        await fan.async_set_preset_mode("bogus")
        fan.device.async_set_operating_mode.assert_not_awaited()
