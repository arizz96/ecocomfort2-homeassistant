"""Number platform for the Ecocomfort 2.0 VMC (calibration offsets)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import EntityCategory, PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .device import EcoComfort2Device, EcoComfort2State
from .coordinator import EcoComfort2ConfigEntry
from .entity import EcoComfort2Entity


@dataclass(frozen=True, kw_only=True)
class EcoComfort2NumberDescription(NumberEntityDescription):
    """Describes an Ecocomfort 2.0 number entity."""

    value_fn: Callable[[EcoComfort2State], float | None]
    write_fn: Callable[[EcoComfort2Device, float], Awaitable[None]]


NUMBERS: tuple[EcoComfort2NumberDescription, ...] = (
    EcoComfort2NumberDescription(
        key="set_temp_offset",
        name="Set Temp Offset",
        icon="mdi:thermometer-plus",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=-5.0,
        native_max_value=5.0,
        native_step=0.1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda state: state.temp_offset,
        write_fn=lambda device, value: device.async_send_offsets(temp=value),
    ),
    EcoComfort2NumberDescription(
        key="set_humidity_offset",
        name="Set Humidity Offset",
        icon="mdi:water-plus-outline",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=-5.0,
        native_max_value=5.0,
        native_step=0.1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda state: state.humidity_offset,
        write_fn=lambda device, value: device.async_send_offsets(humidity=value),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EcoComfort2ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the VMC number entities."""
    coordinator = entry.runtime_data
    async_add_entities(
        EcoComfort2Number(coordinator, description) for description in NUMBERS
    )


class EcoComfort2Number(EcoComfort2Entity, NumberEntity):
    """A sensor calibration offset."""

    entity_description: EcoComfort2NumberDescription

    def __init__(
        self,
        coordinator,
        description: EcoComfort2NumberDescription,
    ) -> None:
        """Initialise the number entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.address}_{description.key}"

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self.entity_description.value_fn(self.data)

    async def async_set_native_value(self, value: float) -> None:
        """Write a new value to the device."""
        await self._async_command(
            self.entity_description.write_fn(self.device, value)
        )
