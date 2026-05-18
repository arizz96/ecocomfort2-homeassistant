"""The Ecocomfort 2 integration."""
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .ecocomfort import EcocomfortDevice

_LOGGER = logging.getLogger(__name__)

DOMAIN = "ecocomfort2"
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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ecocomfort 2 from a config entry."""
    device = EcocomfortDevice(entry.data[CONF_MAC])

    async def _async_update():
        state = await device.async_update()
        if not state.connected:
            raise UpdateFailed("Device not reachable")
        return state

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Ecocomfort 2",
        update_method=_async_update,
        update_interval=SCAN_INTERVAL,
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "device": device,
        "coordinator": coordinator,
    }

    _LOGGER.debug("Starting async_forward_entry_setups for platforms: %s", PLATFORMS)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.debug("Completed async_forward_entry_setups")

    _LOGGER.debug("Setup complete, coordinator will poll every %s", SCAN_INTERVAL)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await hass.data[DOMAIN][entry.entry_id]["device"].async_disconnect()
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
