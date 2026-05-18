"""Tests for EcocomfortSensor entities."""
from unittest.mock import MagicMock

import pytest

from custom_components.ecocomfort2.ecocomfort import EcocomfortState
from custom_components.ecocomfort2.sensor import SENSOR_DESCRIPTIONS, EcocomfortSensor
from tests.conftest import MAC_ADDRESS


def make_sensor(description, state: EcocomfortState):
    coordinator = MagicMock()
    device = MagicMock()
    device.state = state
    config_entry = MagicMock()
    config_entry.data = {"mac": MAC_ADDRESS}
    return EcocomfortSensor(coordinator, device, config_entry, description)


def desc(key):
    return next(d for d in SENSOR_DESCRIPTIONS if d.key == key)


class TestSensorDescriptions:
    def test_expected_keys(self):
        keys = {d.key for d in SENSOR_DESCRIPTIONS}
        assert keys == {"temperature", "humidity", "voc", "direction",
                        "actual_mode", "actual_speed", "firmware"}


class TestNativeValue:
    def test_temperature(self):
        assert make_sensor(desc("temperature"), EcocomfortState(temperature=22.3)).native_value == pytest.approx(22.3)

    def test_humidity(self):
        assert make_sensor(desc("humidity"), EcocomfortState(humidity=65.0)).native_value == pytest.approx(65.0)

    def test_voc(self):
        assert make_sensor(desc("voc"), EcocomfortState(voc=412)).native_value == 412

    def test_direction(self):
        assert make_sensor(desc("direction"), EcocomfortState(direction=2)).native_value == 2

    def test_actual_mode_in(self):
        assert make_sensor(desc("actual_mode"), EcocomfortState(operating_mode=1)).native_value == "In"

    def test_actual_mode_off(self):
        assert make_sensor(desc("actual_mode"), EcocomfortState(operating_mode=0)).native_value == "Off"

    def test_actual_mode_none(self):
        assert make_sensor(desc("actual_mode"), EcocomfortState(operating_mode=None)).native_value is None

    def test_actual_speed_50pct(self):
        assert make_sensor(desc("actual_speed"), EcocomfortState(speed=2)).native_value == 50

    def test_firmware(self):
        assert make_sensor(desc("firmware"), EcocomfortState(firmware="1.2.3")).native_value == "1.2.3"

    def test_returns_none_when_unset(self):
        state = EcocomfortState()
        for d in SENSOR_DESCRIPTIONS:
            assert make_sensor(d, state).native_value is None, f"{d.key} should be None"
