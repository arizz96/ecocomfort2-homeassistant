"""Tests for EcocomfortSwitch entities."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ecocomfort2.switch import SWITCH_DESCRIPTIONS, EcocomfortSwitch
from custom_components.ecocomfort2.ecocomfort import EcocomfortDevice, EcocomfortState
from tests.conftest import MAC_ADDRESS


def make_switch(description, humidity_advanced=False, voc_advanced=False):
    coordinator = MagicMock()
    coordinator.async_request_refresh = AsyncMock()
    device = MagicMock(spec=EcocomfortDevice)
    device.state = EcocomfortState(
        humidity_advanced=humidity_advanced, voc_advanced=voc_advanced
    )
    device.async_set_humidity_advanced = AsyncMock(return_value=True)
    device.async_set_voc_advanced = AsyncMock(return_value=True)
    config_entry = MagicMock()
    config_entry.data = {"mac": MAC_ADDRESS}
    entity = EcocomfortSwitch(coordinator, device, config_entry, description)
    entity.coordinator = coordinator
    return entity


def desc(key):
    return next(d for d in SWITCH_DESCRIPTIONS if d.key == key)


class TestHumidityAdvanced:
    def test_is_on_reflects_state(self):
        assert make_switch(desc("humidity_advanced"), humidity_advanced=True).is_on is True
        assert make_switch(desc("humidity_advanced"), humidity_advanced=False).is_on is False

    async def test_turn_on_calls_set(self):
        sw = make_switch(desc("humidity_advanced"))
        await sw.async_turn_on()
        sw.device.async_set_humidity_advanced.assert_awaited_once_with(True)
        sw.coordinator.async_request_refresh.assert_awaited_once()

    async def test_turn_off_calls_set(self):
        sw = make_switch(desc("humidity_advanced"), humidity_advanced=True)
        await sw.async_turn_off()
        sw.device.async_set_humidity_advanced.assert_awaited_once_with(False)


class TestVocAdvanced:
    def test_is_on_reflects_state(self):
        assert make_switch(desc("voc_advanced"), voc_advanced=True).is_on is True

    async def test_turn_on_calls_set(self):
        sw = make_switch(desc("voc_advanced"))
        await sw.async_turn_on()
        sw.device.async_set_voc_advanced.assert_awaited_once_with(True)

    async def test_no_refresh_on_failure(self):
        sw = make_switch(desc("voc_advanced"))
        sw.device.async_set_voc_advanced = AsyncMock(return_value=False)
        await sw.async_turn_on()
        sw.coordinator.async_request_refresh.assert_not_awaited()
