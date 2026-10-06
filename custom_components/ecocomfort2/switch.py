"""Switch platform for the Ecocomfort 2.0 VMC (threshold advanced modes)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import (
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import EcoComfort2ConfigEntry
from .device import EcoComfort2Device, EcoComfort2State
from .entity import EcoComfort2Entity


@dataclass(frozen=True, kw_only=True)
class EcoComfort2SwitchDescription(SwitchEntityDescription):
    """Describes an Ecocomfort 2.0 switch."""

    value_fn: Callable[[EcoComfort2State], bool | None]
    write_fn: Callable[[EcoComfort2Device, bool], Awaitable[None]]


SWITCHES: tuple[EcoComfort2SwitchDescription, ...] = (
    EcoComfort2SwitchDescription(
        key="humidity_advanced",
        name="Humidity Advanced",
        icon="mdi:water-plus",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda state: state.humidity_advanced,
        write_fn=lambda device, value: device.async_send_thresholds(
            humidity_advanced=value
        ),
    ),
    EcoComfort2SwitchDescription(
        key="voc_advanced",
        name="VOC Advanced",
        icon="mdi:molecule",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda state: state.voc_advanced,
        write_fn=lambda device, value: device.async_send_thresholds(
            voc_advanced=value
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EcoComfort2ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the VMC switches."""
    coordinator = entry.runtime_data
    async_add_entities(
        EcoComfort2Switch(coordinator, description) for description in SWITCHES
    )


class EcoComfort2Switch(EcoComfort2Entity, SwitchEntity):
    """A switch that toggles a threshold "advanced" mode."""

    entity_description: EcoComfort2SwitchDescription

    def __init__(
        self,
        coordinator,
        description: EcoComfort2SwitchDescription,
    ) -> None:
        """Initialise the switch."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.address}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        """Return whether advanced mode is enabled."""
        return self.entity_description.value_fn(self.data)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable advanced mode."""
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable advanced mode."""
        await self._async_set(False)

    async def _async_set(self, value: bool) -> None:
        await self._async_command(
            self.entity_description.write_fn(self.device, value)
        )
