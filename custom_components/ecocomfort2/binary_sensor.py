"""Binary sensor platform for Ecocomfort 2."""
import logging
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN
from .ecocomfort import EcocomfortDevice

_LOGGER = logging.getLogger(__name__)


@dataclass
class EcocomfortBinarySensorDescription(BinarySensorEntityDescription):
    value_fn: callable = None


BINARY_SENSOR_DESCRIPTIONS = [
    EcocomfortBinarySensorDescription(
        key="connected",
        translation_key="connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda state: state.connected,
    ),
    EcocomfortBinarySensorDescription(
        key="boost_active",
        translation_key="boost_active",
        value_fn=lambda state: state.boost_active,
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
            EcocomfortBinarySensor(data["coordinator"], data["device"], config_entry, desc)
            for desc in BINARY_SENSOR_DESCRIPTIONS
        ],
        update_before_add=False,
    )


class EcocomfortBinarySensor(CoordinatorEntity, BinarySensorEntity):
    entity_description: EcocomfortBinarySensorDescription
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
