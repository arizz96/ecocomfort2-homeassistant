"""Select platform for the Ecocomfort 2.0 VMC (season, free cooling, thresholds)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import FREE_COOLING_OPTIONS, SEASON_OPTIONS, THRESHOLD_OPTIONS
from .coordinator import EcoComfort2ConfigEntry
from .device import EcoComfort2Device, EcoComfort2State
from .entity import EcoComfort2Entity


@dataclass(frozen=True, kw_only=True)
class EcoComfort2SelectDescription(SelectEntityDescription):
    """Describes an Ecocomfort 2.0 select entity."""

    value_fn: Callable[[EcoComfort2State], str | None]
    select_fn: Callable[[EcoComfort2Device, str], Awaitable[None]]


def _threshold_option(level: int | None) -> str | None:
    if level is None or not 0 <= level < len(THRESHOLD_OPTIONS):
        return None
    return THRESHOLD_OPTIONS[level]


SELECTS: tuple[EcoComfort2SelectDescription, ...] = (
    EcoComfort2SelectDescription(
        key="season",
        name="Season",
        icon="mdi:sun-snowflake-variant",
        options=SEASON_OPTIONS,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda state: state.season,
        select_fn=lambda device, option: device.async_write_season(option),
    ),
    EcoComfort2SelectDescription(
        key="free_cooling",
        name="Free Cooling",
        icon="mdi:snowflake-thermometer",
        options=FREE_COOLING_OPTIONS,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda state: state.free_cooling,
        select_fn=lambda device, option: device.async_write_free_cooling(option),
    ),
    *(
        EcoComfort2SelectDescription(
            key=f"{sensor}_threshold",
            translation_key=f"{sensor}_threshold",
            name=name,
            icon=icon,
            options=THRESHOLD_OPTIONS,
            entity_category=EntityCategory.CONFIG,
            value_fn=lambda state, attr=f"{sensor}_threshold": _threshold_option(
                getattr(state, attr)
            ),
            select_fn=lambda device, option, sensor=sensor: (
                device.async_send_thresholds(
                    **{sensor: THRESHOLD_OPTIONS.index(option)}
                )
            ),
        )
        for sensor, name, icon in (
            ("humidity", "Humidity Threshold", "mdi:water-thermometer"),
            ("luminosity", "Luminosity Threshold", "mdi:brightness-6"),
            ("voc", "VOC Threshold", "mdi:scent"),
        )
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EcoComfort2ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the VMC select entities."""
    coordinator = entry.runtime_data
    async_add_entities(
        EcoComfort2Select(coordinator, description) for description in SELECTS
    )


class EcoComfort2Select(EcoComfort2Entity, SelectEntity):
    """A selectable device setting."""

    entity_description: EcoComfort2SelectDescription

    def __init__(
        self,
        coordinator,
        description: EcoComfort2SelectDescription,
    ) -> None:
        """Initialise the select entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.address}_{description.key}"

    @property
    def current_option(self) -> str | None:
        """Return the currently selected option."""
        return self.entity_description.value_fn(self.data)

    async def async_select_option(self, option: str) -> None:
        """Write the selected option to the device."""
        await self._async_command(self.entity_description.select_fn(self.device, option))
