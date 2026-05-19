"""Switch platform for Ecocomfort 2 (advanced sensor modes)."""
import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN
from .ecocomfort import EcocomfortDevice

_LOGGER = logging.getLogger(__name__)


@dataclass
class EcocomfortSwitchDescription(SwitchEntityDescription):
    value_fn: callable = None
    turn_on_fn: callable = None
    turn_off_fn: callable = None


SWITCH_DESCRIPTIONS = [
    EcocomfortSwitchDescription(
        key="humidity_advanced",
        translation_key="humidity_advanced",
        value_fn=lambda state: state.humidity_advanced,
        turn_on_fn=lambda device: device.async_set_humidity_advanced(True),
        turn_off_fn=lambda device: device.async_set_humidity_advanced(False),
    ),
    EcocomfortSwitchDescription(
        key="voc_advanced",
        translation_key="voc_advanced",
        value_fn=lambda state: state.voc_advanced,
        turn_on_fn=lambda device: device.async_set_voc_advanced(True),
        turn_off_fn=lambda device: device.async_set_voc_advanced(False),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = config_entry.runtime_data
    async_add_entities(
        [
            EcocomfortSwitch(data["coordinator"], data["device"], config_entry, desc)
            for desc in SWITCH_DESCRIPTIONS
        ],
        update_before_add=False,
    )


class EcocomfortSwitch(CoordinatorEntity, SwitchEntity):
    entity_description: EcocomfortSwitchDescription
    _attr_has_entity_name = True

    def __init__(self, coordinator, device: EcocomfortDevice, config_entry, description) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self.device = device
        mac = config_entry.data[CONF_MAC]
        self._attr_unique_id = f"{mac}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, mac)},
            "name": f"Ecocomfort 2 {mac}",
            "manufacturer": "Fantini Cosmi",
            "model": "Ecocomfort 2",
        }

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.device.state)

    async def async_turn_on(self, **kwargs: Any) -> None:
        if await self.entity_description.turn_on_fn(self.device):
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        if await self.entity_description.turn_off_fn(self.device):
            await self.coordinator.async_request_refresh()
