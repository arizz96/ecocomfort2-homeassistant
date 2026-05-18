"""Sensor platform for Ecocomfort 2."""
import logging
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_MAC,
    PERCENTAGE,
    UnitOfTemperature,
    CONCENTRATION_PARTS_PER_MILLION,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN
from .ecocomfort import EcocomfortDevice

_LOGGER = logging.getLogger(__name__)


@dataclass
class EcocomfortSensorDescription(SensorEntityDescription):
    """Ecocomfort sensor description."""

    value_fn: callable = None


SENSOR_DESCRIPTIONS = [
    EcocomfortSensorDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda state: state.temperature,
    ),
    EcocomfortSensorDescription(
        key="humidity",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda state: state.humidity,
    ),
    EcocomfortSensorDescription(
        key="voc",
        translation_key="voc",
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="ppb",
        value_fn=lambda state: state.voc,
    ),
    EcocomfortSensorDescription(
        key="direction",
        translation_key="direction",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state: state.direction,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor entities."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    device = data["device"]
    coordinator = data["coordinator"]

    entities = [
        EcocomfortSensor(
            coordinator,
            device,
            config_entry,
            description,
        )
        for description in SENSOR_DESCRIPTIONS
    ]

    async_add_entities(entities, update_before_add=True)


class EcocomfortSensor(CoordinatorEntity, SensorEntity):
    """Ecocomfort sensor entity."""

    entity_description: EcocomfortSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        device: EcocomfortDevice,
        config_entry: ConfigEntry,
        description: EcocomfortSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self.device = device
        self._attr_unique_id = f"{config_entry.data[CONF_MAC]}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.data[CONF_MAC])},
            "name": f"Ecocomfort 2 {config_entry.data[CONF_MAC]}",
            "manufacturer": "Fantini Cosmi",
            "model": "Ecocomfort 2",
        }

    @property
    def native_value(self):
        """Return the sensor value."""
        return self.entity_description.value_fn(self.device.state)
