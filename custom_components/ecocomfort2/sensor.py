"""Sensor platform for the Ecocomfort 2.0 VMC."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfRatio,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import (
    DIRECTION_OPTIONS,
    OPERATING_MODE_OPTIONS,
    ROLE_OPTIONS,
    SPEED_LEVEL_OPTIONS,
    SPEED_LEVEL_POWER,
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
        key="nominal_power",
        name="Nominal Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
        # Catalogue figure for the running speed, not a measurement.
        value_fn=lambda state: SPEED_LEVEL_POWER.get(state.speed_level),
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

ENERGY_DESCRIPTION = EcoComfort2SensorDescription(
    key="nominal_energy",
    name="Nominal Energy",
    device_class=SensorDeviceClass.ENERGY,
    state_class=SensorStateClass.TOTAL_INCREASING,
    native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    suggested_display_precision=3,
    entity_registry_enabled_default=False,
    value_fn=lambda state: SPEED_LEVEL_POWER.get(state.speed_level),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EcoComfort2ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the VMC sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            *(EcoComfort2Sensor(coordinator, description) for description in SENSORS),
            EcoComfort2EnergySensor(coordinator, ENERGY_DESCRIPTION),
        ]
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


class EcoComfort2EnergySensor(EcoComfort2Sensor, RestoreSensor):
    """Nominal energy: the nominal power integrated over time.

    Each interval between updates is charged at the power of the speed seen at
    its start. Time while the unit is unreachable is not counted. The total
    is restored across restarts.
    """

    def __init__(
        self,
        coordinator,
        description: EcoComfort2SensorDescription,
    ) -> None:
        """Initialise the energy sensor."""
        super().__init__(coordinator, description)
        self._total_kwh = 0.0
        self._last_time = None
        self._last_power: float | None = None

    async def async_added_to_hass(self) -> None:
        """Restore the running total and start integrating."""
        await super().async_added_to_hass()
        if (last := await self.async_get_last_sensor_data()) is not None:
            try:
                self._total_kwh = float(last.native_value)
            except (TypeError, ValueError):
                self._total_kwh = 0.0
        self._sample()

    def _sample(self) -> None:
        """Add the energy of the interval since the last sample."""
        now = dt_util.utcnow()
        if self._last_time is not None and self._last_power is not None:
            hours = (now - self._last_time).total_seconds() / 3600
            self._total_kwh += self._last_power * hours / 1000
        self._last_time = now
        self._last_power = (
            self.entity_description.value_fn(self.data) if self.data.connected else None
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Integrate, then publish the new total."""
        self._sample()
        super()._handle_coordinator_update()

    @property
    def native_value(self) -> float:
        """Return the accumulated energy in kWh."""
        return round(self._total_kwh, 6)
