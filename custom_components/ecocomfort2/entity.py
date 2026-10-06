"""Shared base entity for the Ecocomfort 2.0 VMC integration."""

from __future__ import annotations

from collections.abc import Awaitable

from bleak.exc import BleakError

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import EcoComfort2Coordinator
from .device import EcoComfort2Device, EcoComfort2State, describe_command_error


class EcoComfort2Entity(CoordinatorEntity[EcoComfort2Coordinator]):
    """Base class wiring entities to the coordinator and device."""

    _attr_has_entity_name = True
    # Most entities mirror values read over BLE, so they go unavailable while
    # the link is down rather than showing stale values as current.
    _available_when_disconnected = False

    def __init__(self, coordinator: EcoComfort2Coordinator) -> None:
        """Initialise the entity and its device registry entry."""
        super().__init__(coordinator)
        self.device: EcoComfort2Device = coordinator.device
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_BLUETOOTH, coordinator.address)},
            identifiers={(DOMAIN, coordinator.address)},
            name=coordinator.device_name,
            manufacturer=MANUFACTURER,
            model=MODEL,
            # Firmware and serial are filled in by the coordinator after the
            # first poll; setting them here (still unknown) would clear them.
        )

    @property
    def available(self) -> bool:
        """Return whether the entity has live data to show."""
        if not super().available:
            return False
        return self._available_when_disconnected or self.data.connected

    @property
    def data(self) -> EcoComfort2State:
        """Return the latest device state snapshot."""
        return self.coordinator.data

    async def _async_command(self, command: Awaitable[None]) -> None:
        """Send a command, surfacing failures in the UI.

        The device reads its whole state back after a successful command, so
        entities only need to be told to update. Requesting a poll as well
        made every command wait for it (a fresh connection), and delayed the
        error message of a failed one.
        """
        try:
            await command
        except (BleakError, TimeoutError) as err:
            raise HomeAssistantError(
                describe_command_error(
                    self.coordinator.device_name, err, self.data.role
                )
            ) from err
        # Not async_set_updated_data, which would reset the poll timer.
        self.coordinator.async_update_listeners()
