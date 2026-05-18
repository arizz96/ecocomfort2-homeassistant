"""Tests for EcocomfortSensor entities."""
from unittest.mock import MagicMock

import pytest

from custom_components.ecocomfort2.ecocomfort import EcocomfortState
from custom_components.ecocomfort2.sensor import SENSOR_DESCRIPTIONS, EcocomfortSensor
from tests.conftest import MAC_ADDRESS


def make_sensor(description, state: EcocomfortState):
    """Build an EcocomfortSensor wired to the given state."""
    coordinator = MagicMock()
    device = MagicMock()
    device.state = state

    config_entry = MagicMock()
    config_entry.data = {"mac": MAC_ADDRESS}

    entity = EcocomfortSensor(coordinator, device, config_entry, description)
    return entity


def get_description(key: str):
    return next(d for d in SENSOR_DESCRIPTIONS if d.key == key)


class TestSensorDescriptions:
    def test_all_expected_keys_present(self):
        keys = {d.key for d in SENSOR_DESCRIPTIONS}
        assert keys == {"temperature", "humidity", "voc", "direction"}

    def test_temperature_has_celsius_unit(self):
        desc = get_description("temperature")
        from homeassistant.const import UnitOfTemperature
        assert desc.native_unit_of_measurement == UnitOfTemperature.CELSIUS

    def test_humidity_has_percent_unit(self):
        desc = get_description("humidity")
        from homeassistant.const import PERCENTAGE
        assert desc.native_unit_of_measurement == PERCENTAGE

    def test_voc_has_ppb_unit(self):
        desc = get_description("voc")
        assert desc.native_unit_of_measurement == "ppb"


class TestNativeValue:
    def test_temperature_sensor(self):
        state = EcocomfortState(temperature=22.3)
        sensor = make_sensor(get_description("temperature"), state)
        assert sensor.native_value == pytest.approx(22.3)

    def test_temperature_sensor_negative(self):
        state = EcocomfortState(temperature=-3.1)
        sensor = make_sensor(get_description("temperature"), state)
        assert sensor.native_value == pytest.approx(-3.1)

    def test_humidity_sensor(self):
        state = EcocomfortState(humidity=65)
        sensor = make_sensor(get_description("humidity"), state)
        assert sensor.native_value == 65

    def test_voc_sensor(self):
        state = EcocomfortState(voc=412)
        sensor = make_sensor(get_description("voc"), state)
        assert sensor.native_value == 412

    def test_direction_sensor(self):
        state = EcocomfortState(direction=2)
        sensor = make_sensor(get_description("direction"), state)
        assert sensor.native_value == 2

    def test_returns_none_when_state_is_none(self):
        state = EcocomfortState()
        for desc in SENSOR_DESCRIPTIONS:
            sensor = make_sensor(desc, state)
            assert sensor.native_value is None, f"{desc.key} should be None"


class TestUniqueId:
    def test_unique_id_includes_mac_and_key(self):
        state = EcocomfortState()
        desc = get_description("temperature")
        sensor = make_sensor(desc, state)
        assert MAC_ADDRESS.replace(":", "").lower() in sensor.unique_id.lower() or MAC_ADDRESS in sensor.unique_id
        assert "temperature" in sensor.unique_id
