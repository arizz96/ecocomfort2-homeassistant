"""Sensor platform for the Ecocomfort 2.0 VMC."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfRatio,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    DIRECTION_OPTIONS,
    OPERATING_MODE_OPTIONS,
    ROLE_OPTIONS,
    SPEED_LEVEL_OPTIONS,
)
from .coordinator import EcoComfort2ConfigEntry
from .device import EcoComfort2State
from .entity import EcoComfort2Entity


@dataclass(frozen=True, kw_only=True)
class EcoComfort2SensorDescription(SensorEntityDescription):
    """Describes an Ecocomfort 2.0 sensor."""

    value_fn: Callable[[EcoComfort2State], float | str | None]


SENSORS: tuple[EcoComfort2SensorDescription, ...] = (
    EcoComfort2SensorDescription(
        key="temperature",
        name="Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        value_fn=lambda state: state.temperature,
    ),
    EcoComfort2SensorDescription(
        key="humidity",
        name="Humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
        value_fn=lambda state: state.humidity,
    ),
    EcoComfort2SensorDescription(
        key="voc",
        name="VOC",
        # The device's own air-quality scale, labelled "ppm" by the manufacturer
        # (manual: VOC thresholds 250/300/350 ppm; the app graphs it as
        # "quality"). Not a physical concentration, so no VOC device class:
        # that would let HA convert it (e.g. to ppb) as if it were one.
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfRatio.PARTS_PER_MILLION,
        icon="mdi:air-filter",
        value_fn=lambda state: state.voc,
    ),
    EcoComfort2SensorDescription(
        key="direction",
        translation_key="direction",
        name="Direction",
        icon="mdi:arrow-left-right",
        device_class=SensorDeviceClass.ENUM,
        options=DIRECTION_OPTIONS,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.direction,
    ),
    EcoComfort2SensorDescription(
        key="actual_mode",
        translation_key="actual_mode",
        name="Actual Mode",
        icon="mdi:fan",
        device_class=SensorDeviceClass.ENUM,
        options=OPERATING_MODE_OPTIONS,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.operating_mode,
    ),
    EcoComfort2SensorDescription(
        key="actual_speed",
        translation_key="actual_speed",
        name="Actual Speed",
        icon="mdi:speedometer",
        device_class=SensorDeviceClass.ENUM,
        options=SPEED_LEVEL_OPTIONS,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.speed_level,
    ),
    EcoComfort2SensorDescription(
        key="role",
        translation_key="role",
        name="Role",
        icon="mdi:account-cog",
        device_class=SensorDeviceClass.ENUM,
        options=ROLE_OPTIONS,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.role,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EcoComfort2ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the VMC sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        EcoComfort2Sensor(coordinator, description) for description in SENSORS
    )


class EcoComfort2Sensor(EcoComfort2Entity, SensorEntity):
    """A read-only sensor backed by the device state."""

    entity_description: EcoComfort2SensorDescription

    def __init__(
        self,
        coordinator,
        description: EcoComfort2SensorDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.address}_{description.key}"

    @property
    def native_value(self) -> float | str | None:
        """Return the current value."""
        return self.entity_description.value_fn(self.data)
