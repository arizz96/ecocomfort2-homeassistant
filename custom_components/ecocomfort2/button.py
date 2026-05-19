"""Button platform for Ecocomfort 2 (manual BLE pairing trigger)."""
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import DOMAIN
from .ecocomfort import EcocomfortDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = config_entry.runtime_data
    async_add_entities(
        [EcocomfortPairButton(data["device"], config_entry)],
        update_before_add=False,
    )


class EcocomfortPairButton(ButtonEntity):
    """Button that triggers a manual BLE connection attempt."""

    _attr_has_entity_name = True
    _attr_translation_key = "pair"

    def __init__(self, device: EcocomfortDevice, config_entry: ConfigEntry) -> None:
        self.device = device
        mac = config_entry.data[CONF_MAC]
        self._attr_unique_id = f"{mac}_pair"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, mac)},
            "name": f"Ecocomfort 2 {mac}",
            "manufacturer": "Fantini Cosmi",
            "model": "Ecocomfort 2",
        }

    async def async_press(self) -> None:
        """Initiate a BLE connection (pairing trigger)."""
        await self.device.async_disconnect()
        await self.device.async_connect()
