"""Tests for EcocomfortBinarySensor entities."""
from unittest.mock import MagicMock

from custom_components.ecocomfort2.binary_sensor import BINARY_SENSOR_DESCRIPTIONS, EcocomfortBinarySensor
from custom_components.ecocomfort2.ecocomfort import EcocomfortState
from tests.conftest import MAC_ADDRESS


def make_entity(description, state: EcocomfortState):
    coordinator = MagicMock()
    device = MagicMock()
    device.state = state
    config_entry = MagicMock()
    config_entry.data = {"mac": MAC_ADDRESS}
    return EcocomfortBinarySensor(coordinator, device, config_entry, description)


def desc(key):
    return next(d for d in BINARY_SENSOR_DESCRIPTIONS if d.key == key)


class TestConnected:
    def test_true_when_connected(self):
        assert make_entity(desc("connected"), EcocomfortState(connected=True)).is_on is True

    def test_false_when_disconnected(self):
        assert make_entity(desc("connected"), EcocomfortState(connected=False)).is_on is False


class TestBoostActive:
    def test_true_when_boost(self):
        assert make_entity(desc("boost_active"), EcocomfortState(boost_active=True)).is_on is True

    def test_false_when_no_boost(self):
        assert make_entity(desc("boost_active"), EcocomfortState(boost_active=False)).is_on is False
