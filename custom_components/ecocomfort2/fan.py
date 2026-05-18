"""Fan platform for Ecocomfort 2 (ventilation unit)."""
import logging
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN
from .ecocomfort import (
    EcocomfortDevice,
    MODE_TO_PRESET,
    PRESET_TO_MODE,
    PCT_TO_SPEED,
    SPEED_TO_PCT,
)

_LOGGER = logging.getLogger(__name__)

ORDERED_SPEEDS = [1, 2, 3, 4]   # Sleep → Vel3
PRESET_MODES = ["In", "Out", "In-Out", "Sensor"]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [EcocomfortFan(data["coordinator"], data["device"], config_entry)],
        update_before_add=True,
    )


class EcocomfortFan(CoordinatorEntity, FanEntity):
    """Fan entity representing the Ecocomfort 2 ventilation unit."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_preset_modes = PRESET_MODES

    def __init__(self, coordinator, device: EcocomfortDevice, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self.device = device
        mac = config_entry.data[CONF_MAC]
        self._attr_unique_id = f"{mac}_fan"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, mac)},
            "name": f"Ecocomfort 2 {mac}",
            "manufacturer": "Fantini Cosmi",
            "model": "Ecocomfort 2",
        }

    @property
    def is_on(self) -> bool:
        return bool(self.device.state.operating_mode)

    @property
    def percentage(self) -> int | None:
        speed = self.device.state.speed
        if not speed:
            return None
        return SPEED_TO_PCT.get(speed)

    @property
    def speed_count(self) -> int:
        return len(ORDERED_SPEEDS)

    @property
    def preset_mode(self) -> str | None:
        mode = self.device.state.operating_mode
        return MODE_TO_PRESET.get(mode)

    @property
    def available(self) -> bool:
        return self.device.state.connected

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        mode = PRESET_TO_MODE.get(preset_mode or "", self.device.state.operating_mode or 3)
        if percentage is not None:
            speed = PCT_TO_SPEED.get(percentage, 2)
        else:
            speed = self.device.state.speed or 2
        if await self.device.async_set_operating_mode(mode, speed):
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        if await self.device.async_set_operating_mode(0, 0):
            await self.coordinator.async_request_refresh()

    async def async_set_percentage(self, percentage: int) -> None:
        speed = PCT_TO_SPEED.get(percentage, 2)
        mode = self.device.state.operating_mode or 3
        if await self.device.async_set_operating_mode(mode, speed):
            await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        mode = PRESET_TO_MODE.get(preset_mode)
        if mode is None:
            return
        speed = self.device.state.speed or 2
        if await self.device.async_set_operating_mode(mode, speed):
            await self.coordinator.async_request_refresh()
