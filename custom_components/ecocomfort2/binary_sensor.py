"""Binary sensor platform for the Ecocomfort 2.0 VMC."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import EcoComfort2ConfigEntry
from .device import EcoComfort2State
from .entity import EcoComfort2Entity


@dataclass(frozen=True, kw_only=True)
class EcoComfort2BinarySensorDescription(BinarySensorEntityDescription):
    """Describes an Ecocomfort 2.0 binary sensor."""

    value_fn: Callable[[EcoComfort2State], bool | None]


BINARY_SENSORS: tuple[EcoComfort2BinarySensorDescription, ...] = (
    EcoComfort2BinarySensorDescription(
        key="connected",
        name="Connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:bluetooth-connect",
        value_fn=lambda state: state.connected,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EcoComfort2ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the VMC binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        EcoComfort2BinarySensor(coordinator, description)
        for description in BINARY_SENSORS
    )


class EcoComfort2BinarySensor(EcoComfort2Entity, BinarySensorEntity):
    """A read-only binary sensor backed by the device state."""

    entity_description: EcoComfort2BinarySensorDescription

    def __init__(
        self,
        coordinator,
        description: EcoComfort2BinarySensorDescription,
    ) -> None:
        """Initialise the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.address}_{description.key}"
        self._available_when_disconnected = description.key == "connected"

    @property
    def is_on(self) -> bool | None:
        """Return the current state."""
        return self.entity_description.value_fn(self.data)
