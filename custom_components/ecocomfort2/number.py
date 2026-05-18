"""Number platform for Ecocomfort 2 (thresholds and calibration offsets)."""
import logging
from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN
from .ecocomfort import EcocomfortDevice

_LOGGER = logging.getLogger(__name__)


@dataclass
class EcocomfortNumberDescription(NumberEntityDescription):
    value_fn: callable = None
    set_fn: callable = None


THRESHOLD_DESCRIPTIONS = [
    EcocomfortNumberDescription(
        key="humidity_threshold",
        translation_key="humidity_threshold",
        native_min_value=0,
        native_max_value=3,
        native_step=1,
        mode=NumberMode.SLIDER,
        value_fn=lambda state: state.humidity_threshold,
        set_fn=lambda device, v: device.async_set_thresholds(
            int(v), device.state.luminosity_threshold or 0, device.state.voc_threshold or 0
        ),
    ),
    EcocomfortNumberDescription(
        key="luminosity_threshold",
        translation_key="luminosity_threshold",
        native_min_value=0,
        native_max_value=3,
        native_step=1,
        mode=NumberMode.SLIDER,
        value_fn=lambda state: state.luminosity_threshold,
        set_fn=lambda device, v: device.async_set_thresholds(
            device.state.humidity_threshold or 0, int(v), device.state.voc_threshold or 0
        ),
    ),
    EcocomfortNumberDescription(
        key="voc_threshold",
        translation_key="voc_threshold",
        native_min_value=0,
        native_max_value=3,
        native_step=1,
        mode=NumberMode.SLIDER,
        value_fn=lambda state: state.voc_threshold,
        set_fn=lambda device, v: device.async_set_thresholds(
            device.state.humidity_threshold or 0, device.state.luminosity_threshold or 0, int(v)
        ),
    ),
]

OFFSET_DESCRIPTIONS = [
    EcocomfortNumberDescription(
        key="temp_offset",
        translation_key="temp_offset",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=-5.0,
        native_max_value=5.0,
        native_step=0.1,
        mode=NumberMode.BOX,
        value_fn=lambda state: state.temp_offset,
        set_fn=lambda device, v: device.async_set_offsets(v, device.state.hum_offset or 0.0),
    ),
    EcocomfortNumberDescription(
        key="hum_offset",
        translation_key="hum_offset",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=-5.0,
        native_max_value=5.0,
        native_step=0.1,
        mode=NumberMode.BOX,
        value_fn=lambda state: state.hum_offset,
        set_fn=lambda device, v: device.async_set_offsets(device.state.temp_offset or 0.0, v),
    ),
]

NUMBER_DESCRIPTIONS = THRESHOLD_DESCRIPTIONS + OFFSET_DESCRIPTIONS


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            EcocomfortNumber(data["coordinator"], data["device"], config_entry, desc)
            for desc in NUMBER_DESCRIPTIONS
        ],
        update_before_add=False,
    )


class EcocomfortNumber(CoordinatorEntity, NumberEntity):
    entity_description: EcocomfortNumberDescription
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
    def native_value(self) -> float | None:
        return self.entity_description.value_fn(self.device.state)

    async def async_set_native_value(self, value: float) -> None:
        if await self.entity_description.set_fn(self.device, value):
            await self.coordinator.async_request_refresh()
