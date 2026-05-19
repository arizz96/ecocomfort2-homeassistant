"""Stub homeassistant.components.bluetooth for tests."""
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator


class ActiveBluetoothDataUpdateCoordinator(DataUpdateCoordinator):
    """Stub for ActiveBluetoothDataUpdateCoordinator."""

    def __init__(self, hass, logger, address, name, update_method, update_interval, ble_device_callback):
        super().__init__(hass, logger, name=name, update_method=update_method, update_interval=update_interval)
        self.address = address
        self.ble_device_callback = ble_device_callback


def async_ble_device_from_address(hass, address, connectable=True):
    return None
