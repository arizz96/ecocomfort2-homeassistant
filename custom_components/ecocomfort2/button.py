"""Button platform for the Ecocomfort 2.0 VMC (manual re-pair)."""

from __future__ import annotations

from bleak.exc import BleakError

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import EcoComfort2ConfigEntry
from .entity import EcoComfort2Entity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EcoComfort2ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the VMC pair button."""
    async_add_entities([EcoComfort2PairButton(entry.runtime_data)])


class EcoComfort2PairButton(EcoComfort2Entity, ButtonEntity):
    """Forces a BLE reconnect and pairing attempt."""

    _attr_name = "Pair"
    _attr_icon = "mdi:bluetooth-settings"
    _attr_entity_category = EntityCategory.CONFIG
    _available_when_disconnected = True

    def __init__(self, coordinator) -> None:
        """Initialise the pair button."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_pair"

    async def async_press(self) -> None:
        """Reconnect and pair with the device."""
        try:
            await self.device.async_pair()
        except TimeoutError as err:
            raise HomeAssistantError(
                f"Pairing with {self.coordinator.device_name} timed out; put the "
                "VMC in pairing mode (hold its button ~5s until the LED blinks) "
                "and try again"
            ) from err
        except BleakError as err:
            raise HomeAssistantError(str(err)) from err
        # The device read its state back over the paired link.
        self.coordinator.async_update_listeners()
