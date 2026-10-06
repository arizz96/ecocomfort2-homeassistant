"""Fan platform for the Ecocomfort 2.0 VMC."""

from __future__ import annotations

import math
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from .const import PRESET_MODES, SPEED_RANGE
from .coordinator import EcoComfort2ConfigEntry
from .entity import EcoComfort2Entity


def _speed(percentage: int) -> int:
    """Map a non-zero percentage to a device speed level (1-4)."""
    speed = math.ceil(percentage_to_ranged_value(SPEED_RANGE, percentage))
    return max(1, min(4, speed))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EcoComfort2ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the VMC fan entity."""
    async_add_entities([EcoComfort2Fan(entry.runtime_data)])


class EcoComfort2Fan(EcoComfort2Entity, FanEntity):
    """The main VMC control: on/off, speed and preset modes."""

    _attr_name = None
    _attr_icon = "mdi:air-purifier"
    _attr_speed_count = 4
    _attr_preset_modes = PRESET_MODES
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator) -> None:
        """Initialise the fan entity."""
        super().__init__(coordinator)
        self._attr_unique_id = coordinator.address

    @property
    def is_on(self) -> bool | None:
        """Return whether the unit is running."""
        return self.data.is_on

    @property
    def percentage(self) -> int | None:
        """Return the current speed as a percentage."""
        if self.data.is_on is None:
            return None
        if not self.data.is_on:
            return 0
        # The setpoint when there is one; in Auto (no manual speed) show what
        # the unit is actually running at.
        speed = self.data.commanded_speed or self.data.running_speed
        if speed is None:
            return None
        return ranged_value_to_percentage(SPEED_RANGE, speed)

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        return self.data.preset

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the fan speed."""
        if percentage == 0:
            await self.async_turn_off()
            return
        await self._async_command(
            self.device.async_send_operation(speed=_speed(percentage))
        )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset (airflow direction) mode."""
        await self._async_command(
            self.device.async_send_operation(preset=preset_mode)
        )

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn the unit on, optionally with a speed and/or preset."""
        speed = _speed(percentage) if percentage else None
        await self._async_command(
            self.device.async_send_operation(preset=preset_mode, speed=speed)
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the unit off."""
        await self._async_command(self.device.async_send_off())
