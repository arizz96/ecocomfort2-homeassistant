"""The Ecocomfort 2 integration."""
import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.bluetooth import (
    ActiveBluetoothDataUpdateCoordinator,
    async_ble_device_from_address,
)
from homeassistant.config_entries import ConfigEntry, ConfigEntryNotReady
from homeassistant.const import CONF_MAC, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import CONF_RETRY_COUNT, DEFAULT_RETRY_COUNT, DOMAIN
from .ecocomfort import EcocomfortDevice

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.FAN,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.BUTTON,
]
SCAN_INTERVAL = timedelta(seconds=30)
STARTUP_TIMEOUT = timedelta(seconds=30)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ecocomfort 2 from a config entry."""
    mac = entry.data[CONF_MAC]
    retry_count = entry.options.get(CONF_RETRY_COUNT, DEFAULT_RETRY_COUNT)

    _LOGGER.debug("Setting up Ecocomfort 2 at %s (retry_count=%d)", mac, retry_count)

    # Get BLE device from HA's bluetooth manager
    ble_device = async_ble_device_from_address(hass, mac, connectable=True)
    if ble_device is None:
        _LOGGER.error(
            "Device %s not found. Ensure it is in Bluetooth range "
            "and HA Bluetooth integration is enabled",
            mac,
        )
        raise ConfigEntryNotReady(f"Device {mac} not found in Bluetooth range")

    device = EcocomfortDevice(hass, mac, retry_count=retry_count)

    async def _async_update() -> Any:
        """Fetch data from device."""
        try:
            state = await device.async_update()
            if not state.connected:
                raise UpdateFailed("Device not reachable")
            return state
        except Exception as exc:
            _LOGGER.error("Error fetching data from %s: %s", mac, exc)
            raise UpdateFailed(f"Error communicating with {mac}") from exc

    coordinator = ActiveBluetoothDataUpdateCoordinator(
        hass,
        _LOGGER,
        address=mac,
        name=f"Ecocomfort 2 {mac}",
        update_method=_async_update,
        update_interval=SCAN_INTERVAL,
        ble_device_callback=lambda *_: None,  # Device-level disconnect handled by Bleak
    )

    entry.runtime_data = {"device": device, "coordinator": coordinator}

    _LOGGER.debug("Waiting for coordinator readiness (timeout: %s)", STARTUP_TIMEOUT)
    try:
        async with asyncio.timeout(STARTUP_TIMEOUT.total_seconds()):
            await coordinator.async_request_refresh()
    except asyncio.TimeoutError:
        _LOGGER.error(
            "Coordinator startup timeout for %s — device may be unreachable "
            "or BLE connection issues",
            mac,
        )
        raise ConfigEntryNotReady("Device startup timeout") from None
    except UpdateFailed as exc:
        _LOGGER.error("First coordinator update failed for %s: %s", mac, exc)
        raise ConfigEntryNotReady("Device not responding to initial update") from exc

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.debug("Setup complete for %s", mac)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    mac = entry.data[CONF_MAC]
    _LOGGER.debug("Unloading %s", mac)

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        device: EcocomfortDevice = entry.runtime_data["device"]
        await device.async_disconnect()
    return unload_ok
