"""Tests for EcocomfortNumber entities."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ecocomfort2.number import NUMBER_DESCRIPTIONS, EcocomfortNumber
from custom_components.ecocomfort2.ecocomfort import EcocomfortDevice, EcocomfortState
from tests.conftest import MAC_ADDRESS


def make_number(description, **state_kwargs):
    coordinator = MagicMock()
    coordinator.async_request_refresh = AsyncMock()
    device = MagicMock(spec=EcocomfortDevice)
    defaults = dict(
        humidity_threshold=1, luminosity_threshold=1, voc_threshold=1,
        temp_offset=0.0, hum_offset=0.0,
    )
    defaults.update(state_kwargs)
    device.state = EcocomfortState(**defaults)
    device.async_set_thresholds = AsyncMock(return_value=True)
    device.async_set_offsets = AsyncMock(return_value=True)
    config_entry = MagicMock()
    config_entry.data = {"mac": MAC_ADDRESS}
    entity = EcocomfortNumber(coordinator, device, config_entry, description)
    entity.coordinator = coordinator
    return entity


def desc(key):
    return next(d for d in NUMBER_DESCRIPTIONS if d.key == key)


class TestThresholdNumbers:
    def test_humidity_value(self):
        assert make_number(desc("humidity_threshold"), humidity_threshold=2).native_value == 2

    def test_luminosity_value(self):
        assert make_number(desc("luminosity_threshold"), luminosity_threshold=3).native_value == 3

    def test_voc_value(self):
        assert make_number(desc("voc_threshold"), voc_threshold=1).native_value == 1

    async def test_set_humidity(self):
        n = make_number(desc("humidity_threshold"))
        await n.async_set_native_value(3.0)
        n.device.async_set_thresholds.assert_awaited_once()
        args = n.device.async_set_thresholds.call_args[0]
        assert args[0] == 3  # humidity

    async def test_set_luminosity_preserves_others(self):
        n = make_number(desc("luminosity_threshold"), humidity_threshold=2, voc_threshold=1)
        await n.async_set_native_value(2.0)
        args = n.device.async_set_thresholds.call_args[0]
        assert args[0] == 2  # humidity preserved
        assert args[1] == 2  # new luminosity
        assert args[2] == 1  # voc preserved

    async def test_requests_refresh(self):
        n = make_number(desc("humidity_threshold"))
        await n.async_set_native_value(1.0)
        n.coordinator.async_request_refresh.assert_awaited_once()


class TestOffsetNumbers:
    def test_temp_offset_value(self):
        assert make_number(desc("set_temp_offset"), temp_offset=1.5).native_value == pytest.approx(1.5)

    def test_hum_offset_value(self):
        assert make_number(desc("set_hum_offset"), hum_offset=-2.0).native_value == pytest.approx(-2.0)

    async def test_set_temp_offset(self):
        n = make_number(desc("set_temp_offset"), hum_offset=-1.0)
        await n.async_set_native_value(0.5)
        args = n.device.async_set_offsets.call_args[0]
        assert args[0] == pytest.approx(0.5)
        assert args[1] == pytest.approx(-1.0)  # hum preserved

    async def test_set_hum_offset(self):
        n = make_number(desc("set_hum_offset"), temp_offset=0.5)
        await n.async_set_native_value(-2.0)
        args = n.device.async_set_offsets.call_args[0]
        assert args[0] == pytest.approx(0.5)  # temp preserved
        assert args[1] == pytest.approx(-2.0)

    async def test_no_refresh_on_failure(self):
        n = make_number(desc("set_temp_offset"))
        n.device.async_set_offsets = AsyncMock(return_value=False)
        await n.async_set_native_value(1.0)
        n.coordinator.async_request_refresh.assert_not_awaited()
