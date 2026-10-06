"""Data update coordinator for the Ecocomfort 2.0 VMC integration."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import CLOCK_SYNC_INTERVAL, DOMAIN, UPDATE_INTERVAL
from .device import EcoComfort2Device, EcoComfort2State

_LOGGER = logging.getLogger(__name__)

EcoComfort2ConfigEntry = ConfigEntry["EcoComfort2Coordinator"]


def _stagger_offset(address: str) -> float:
    """Spread units' poll cycles across the interval instead of starting aligned.

    Multiple units are often reachable only through the same BLE proxy, which
    has few simultaneous connection slots; if every unit's timer fires at once
    they queue behind each other and are more likely to time out. Deriving the
    offset from the address keeps it stable across restarts.
    """
    return int(address.replace(":", ""), 16) % UPDATE_INTERVAL.total_seconds()


class EcoComfort2Coordinator(DataUpdateCoordinator[EcoComfort2State]):
    """Polls a single VMC unit over BLE and shares the result with entities."""

    config_entry: EcoComfort2ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: EcoComfort2ConfigEntry,
        address: str,
    ) -> None:
        """Set up the coordinator for one device."""
        self.device = EcoComfort2Device(hass, address, entry.data.get(CONF_NAME))
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=self.device.label,
            update_interval=UPDATE_INTERVAL,
        )
        self.address = address
        self.device_name = entry.title
        self._device_info_synced = False
        self._initial_delay = _stagger_offset(address)

    async def async_first_refresh(self) -> None:
        """Delay briefly, then run the first refresh.

        Runs as a background task from async_setup_entry, so the stagger
        doesn't block Home Assistant startup.
        """
        await asyncio.sleep(self._initial_delay)
        await self.async_refresh()

    async def _async_update_data(self) -> EcoComfort2State:
        """Poll the device. Never raises: connection state is part of the data."""
        # The device records an attempt only once it reached the unit, so a
        # failed poll (state.connected stays True for a couple of those)
        # doesn't postpone the sync by an hour.
        last = self.device.last_clock_sync
        sync_clock = last is None or dt_util.utcnow() - last >= CLOCK_SYNC_INTERVAL
        state = await self.device.async_poll(sync_clock=sync_clock)
        self._sync_device_info(state)
        self._store_name()
        return state

    def _store_name(self) -> None:
        """Keep the unit's Bluetooth name, so logs use it from the start."""
        name = self.device.name
        if name is None or self.config_entry.data.get(CONF_NAME) == name:
            return
        self.name = name
        self.hass.config_entries.async_update_entry(
            self.config_entry, data={**self.config_entry.data, CONF_NAME: name}
        )

    def _sync_device_info(self, state: EcoComfort2State) -> None:
        """Record firmware and serial in the device registry once known.

        Entities are created before the first poll, so these aren't available
        when the device entry is made.
        """
        if self._device_info_synced or state.firmware is None:
            return
        registry = dr.async_get(self.hass)
        device = registry.async_get_device_by_identifier(
            (DOMAIN, self.address), self.config_entry.entry_id
        )
        if device is None:
            return
        registry.async_update_device(
            device.id, sw_version=state.firmware, serial_number=state.serial
        )
        self._device_info_synced = True

    async def async_shutdown_device(self) -> None:
        """Disconnect from the device on unload."""
        await self.device.async_disconnect()
