"""Tests for EcocomfortSelect entities."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ecocomfort2.select import SELECT_DESCRIPTIONS, EcocomfortSelect
from custom_components.ecocomfort2.ecocomfort import EcocomfortDevice, EcocomfortState, SEASON_SUMMER, SEASON_WINTER
from tests.conftest import MAC_ADDRESS


def make_select(description, **state_kwargs):
    coordinator = MagicMock()
    coordinator.async_request_refresh = AsyncMock()
    device = MagicMock(spec=EcocomfortDevice)
    device.state = EcocomfortState(**state_kwargs)
    device.async_set_season = AsyncMock(return_value=True)
    device.async_set_free_cooling = AsyncMock(return_value=True)
    config_entry = MagicMock()
    config_entry.data = {"mac": MAC_ADDRESS}
    entity = EcocomfortSelect(coordinator, device, config_entry, description)
    entity.coordinator = coordinator
    return entity


def desc(key):
    return next(d for d in SELECT_DESCRIPTIONS if d.key == key)


class TestSeasonSelect:
    def test_winter_option(self):
        assert make_select(desc("season"), season=SEASON_WINTER).current_option == "Winter"

    def test_summer_option(self):
        assert make_select(desc("season"), season=SEASON_SUMMER).current_option == "Summer"

    def test_none_when_unset(self):
        assert make_select(desc("season"), season=None).current_option is None

    async def test_select_summer(self):
        s = make_select(desc("season"), season=SEASON_WINTER)
        await s.async_select_option("Summer")
        s.device.async_set_season.assert_awaited_once_with(SEASON_SUMMER)
        s.coordinator.async_request_refresh.assert_awaited_once()

    async def test_select_winter(self):
        s = make_select(desc("season"), season=SEASON_SUMMER)
        await s.async_select_option("Winter")
        s.device.async_set_season.assert_awaited_once_with(SEASON_WINTER)

    async def test_no_refresh_on_failure(self):
        s = make_select(desc("season"), season=SEASON_WINTER)
        s.device.async_set_season = AsyncMock(return_value=False)
        await s.async_select_option("Summer")
        s.coordinator.async_request_refresh.assert_not_awaited()


class TestFreeCoolingSelect:
    @pytest.mark.parametrize("level, expected", [(0, "Off"), (1, "Low"), (2, "Medium"), (3, "High")])
    def test_level_to_option(self, level, expected):
        assert make_select(desc("free_cooling"), free_cooling=level).current_option == expected

    def test_none_when_unset(self):
        assert make_select(desc("free_cooling"), free_cooling=None).current_option is None

    @pytest.mark.parametrize("option, expected_level", [
        ("Off", 0), ("Low", 1), ("Medium", 2), ("High", 3)
    ])
    async def test_select_level(self, option, expected_level):
        s = make_select(desc("free_cooling"), free_cooling=0)
        await s.async_select_option(option)
        s.device.async_set_free_cooling.assert_awaited_once_with(expected_level)

    def test_options_are_complete(self):
        s = make_select(desc("free_cooling"), free_cooling=0)
        assert set(s._attr_options) == {"Off", "Low", "Medium", "High"}
