"""Select platform for Ecocomfort 2 (season and free-cooling intensity)."""
import logging
from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN
from .ecocomfort import (
    EcocomfortDevice,
    FREE_COOLING_HIGH,
    FREE_COOLING_LOW,
    FREE_COOLING_MEDIUM,
    FREE_COOLING_OFF,
    SEASON_SUMMER,
    SEASON_WINTER,
)

_LOGGER = logging.getLogger(__name__)

SEASON_OPTIONS = ["Winter", "Summer"]
FREE_COOLING_OPTIONS = ["Off", "Low", "Medium", "High"]

_FREE_COOLING_TO_INT = {
    "Off": FREE_COOLING_OFF,
    "Low": FREE_COOLING_LOW,
    "Medium": FREE_COOLING_MEDIUM,
    "High": FREE_COOLING_HIGH,
}
_INT_TO_FREE_COOLING = {v: k for k, v in _FREE_COOLING_TO_INT.items()}


@dataclass
class EcocomfortSelectDescription(SelectEntityDescription):
    options: list = None
    value_fn: callable = None
    select_fn: callable = None


SELECT_DESCRIPTIONS = [
    EcocomfortSelectDescription(
        key="season",
        translation_key="season",
        options=SEASON_OPTIONS,
        value_fn=lambda state: "Summer" if state.season == SEASON_SUMMER else "Winter"
        if state.season is not None
        else None,
        select_fn=lambda device, v: device.async_set_season(
            SEASON_SUMMER if v == "Summer" else SEASON_WINTER
        ),
    ),
    EcocomfortSelectDescription(
        key="free_cooling",
        translation_key="free_cooling",
        options=FREE_COOLING_OPTIONS,
        value_fn=lambda state: _INT_TO_FREE_COOLING.get(state.free_cooling),
        select_fn=lambda device, v: device.async_set_free_cooling(_FREE_COOLING_TO_INT[v]),
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
            EcocomfortSelect(data["coordinator"], data["device"], config_entry, desc)
            for desc in SELECT_DESCRIPTIONS
        ],
        update_before_add=False,
    )


class EcocomfortSelect(CoordinatorEntity, SelectEntity):
    entity_description: EcocomfortSelectDescription
    _attr_has_entity_name = True

    def __init__(self, coordinator, device: EcocomfortDevice, config_entry, description) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self.device = device
        mac = config_entry.data[CONF_MAC]
        self._attr_unique_id = f"{mac}_{description.key}"
        self._attr_options = description.options
        self._attr_device_info = {
            "identifiers": {(DOMAIN, mac)},
            "name": f"Ecocomfort 2 {mac}",
            "manufacturer": "Fantini Cosmi",
            "model": "Ecocomfort 2",
        }

    @property
    def current_option(self) -> str | None:
        return self.entity_description.value_fn(self.device.state)

    async def async_select_option(self, option: str) -> None:
        if await self.entity_description.select_fn(self.device, option):
            await self.coordinator.async_request_refresh()
