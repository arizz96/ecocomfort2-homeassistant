"""The Ecocomfort 2 integration."""
import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .ecocomfort import EcocomfortDevice

_LOGGER = logging.getLogger(__name__)

DOMAIN = "ecocomfort2"
PLATFORMS = [Platform.CLIMATE, Platform.SENSOR]
SCAN_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ecocomfort 2 from a config entry."""
    mac_address = entry.data[CONF_MAC]

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Ecocomfort 2",
        update_method=async_update_data,
        update_interval=SCAN_INTERVAL,
    )

    device = EcocomfortDevice(mac_address)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "device": device,
        "coordinator": coordinator,
    }

    await coordinator.async_config_entry_first_refresh()

    async def async_update_data():
        """Fetch data from the device."""
        return await device.async_update()

    coordinator.async_update_method = async_update_data

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    ):
        device = hass.data[DOMAIN][entry.entry_id]["device"]
        await device.async_disconnect()
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
