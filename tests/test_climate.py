"""Tests for EcocomfortClimate entity."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.climate import HVACMode

from custom_components.ecocomfort2.climate import HVAC_MODES, EcocomfortClimate
from custom_components.ecocomfort2.ecocomfort import EcocomfortDevice, EcocomfortState
from tests.conftest import MAC_ADDRESS


def make_climate(operating_mode=None, temperature=None, humidity=None, voc=None, direction=None):
    """Build an EcocomfortClimate with a pre-populated state."""
    coordinator = MagicMock()
    coordinator.async_request_refresh = AsyncMock()

    device = MagicMock(spec=EcocomfortDevice)
    device.state = EcocomfortState(
        operating_mode=operating_mode,
        temperature=temperature,
        humidity=humidity,
        voc=voc,
        direction=direction,
        firmware="1.0.0",
        serial="DEADBEEF",
    )
    device.async_set_operating_mode = AsyncMock(return_value=True)

    config_entry = MagicMock()
    config_entry.data = {"mac": MAC_ADDRESS}

    entity = EcocomfortClimate(coordinator, device, config_entry)
    entity.coordinator = coordinator
    return entity


class TestHvacModeProperty:
    def test_none_mode_returns_off(self):
        entity = make_climate(operating_mode=None)
        assert entity.hvac_mode == HVACMode.OFF

    @pytest.mark.parametrize("mode_int, expected", list(HVAC_MODES.items()))
    def test_all_mapped_modes(self, mode_int, expected):
        entity = make_climate(operating_mode=mode_int)
        assert entity.hvac_mode == expected

    def test_unknown_mode_returns_off(self):
        entity = make_climate(operating_mode=99)
        assert entity.hvac_mode == HVACMode.OFF

    def test_mode_with_high_byte_masked(self):
        # operating_mode & 0xFF should resolve to 1 (FAN_ONLY)
        entity = make_climate(operating_mode=0x0101)
        assert entity.hvac_mode == HVACMode.FAN_ONLY


class TestCurrentTemperature:
    def test_returns_temperature(self):
        entity = make_climate(temperature=21.5)
        assert entity.current_temperature == pytest.approx(21.5)

    def test_returns_none_when_unset(self):
        entity = make_climate()
        assert entity.current_temperature is None


class TestCurrentHumidity:
    def test_returns_humidity(self):
        entity = make_climate(humidity=60)
        assert entity.current_humidity == 60

    def test_returns_none_when_unset(self):
        entity = make_climate()
        assert entity.current_humidity is None


class TestExtraStateAttributes:
    def test_contains_all_keys(self):
        entity = make_climate(voc=300, direction=2)
        attrs = entity.extra_state_attributes
        assert "voc" in attrs
        assert "direction" in attrs
        assert "firmware" in attrs
        assert "serial" in attrs

    def test_values_match_state(self):
        entity = make_climate(voc=420, direction=3)
        attrs = entity.extra_state_attributes
        assert attrs["voc"] == 420
        assert attrs["direction"] == 3
        assert attrs["firmware"] == "1.0.0"
        assert attrs["serial"] == "DEADBEEF"


class TestAsyncSetHvacMode:
    async def test_sets_known_mode(self):
        entity = make_climate()
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        entity.device.async_set_operating_mode.assert_awaited_once_with(2)

    async def test_requests_coordinator_refresh_on_success(self):
        entity = make_climate()
        entity.device.async_set_operating_mode = AsyncMock(return_value=True)
        await entity.async_set_hvac_mode(HVACMode.COOL)
        entity.coordinator.async_request_refresh.assert_awaited_once()

    async def test_does_not_refresh_on_failure(self):
        entity = make_climate()
        entity.device.async_set_operating_mode = AsyncMock(return_value=False)
        await entity.async_set_hvac_mode(HVACMode.AUTO)
        entity.coordinator.async_request_refresh.assert_not_awaited()

    async def test_ignores_unknown_mode(self):
        entity = make_climate()
        await entity.async_set_hvac_mode("invalid_mode")
        entity.device.async_set_operating_mode.assert_not_awaited()

    @pytest.mark.parametrize("hvac_mode, expected_int", [
        (HVACMode.OFF, 0),
        (HVACMode.FAN_ONLY, 1),
        (HVACMode.HEAT, 2),
        (HVACMode.COOL, 3),
        (HVACMode.AUTO, 4),
    ])
    async def test_all_modes_map_to_correct_int(self, hvac_mode, expected_int):
        entity = make_climate()
        await entity.async_set_hvac_mode(hvac_mode)
        entity.device.async_set_operating_mode.assert_awaited_once_with(expected_int)
