"""Number platform for PetSnowy integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import PetSnowyConfigEntry
from .const import DEVICE_TYPE_FOUNTAIN, DEVICE_TYPE_LITTERBOX
from .coordinator import PetSnowyCoordinator
from .entity import PetSnowyEntity


@dataclass(frozen=True, kw_only=True)
class PetSnowyNumberDescription(NumberEntityDescription):
    """Describe a PetSnowy number entity."""

    value_fn: str
    set_fn: str


LITTERBOX_NUMBERS: tuple[PetSnowyNumberDescription, ...] = (
    PetSnowyNumberDescription(
        key="clean_delay",
        translation_key="clean_delay",
        icon="mdi:timer",
        native_min_value=2,
        native_max_value=60,
        native_step=2,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        value_fn="delay_clean_time",
        set_fn="set_clean_delay",
    ),
)

FOUNTAIN_NUMBERS: tuple[PetSnowyNumberDescription, ...] = (
    PetSnowyNumberDescription(
        key="filter_reminder",
        translation_key="filter_reminder",
        icon="mdi:air-filter",
        native_min_value=0,
        native_max_value=90,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.DAYS,
        value_fn="filter_life",
        set_fn="set_filter_reminder",
    ),
)

_NUMBERS_BY_TYPE: dict[str, tuple[PetSnowyNumberDescription, ...]] = {
    DEVICE_TYPE_LITTERBOX: LITTERBOX_NUMBERS,
    DEVICE_TYPE_FOUNTAIN: FOUNTAIN_NUMBERS,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PetSnowyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PetSnowy number entities."""
    coordinator = entry.runtime_data
    descriptions = _NUMBERS_BY_TYPE.get(coordinator.device_type, ())
    async_add_entities(
        PetSnowyNumber(coordinator, desc) for desc in descriptions
    )


class PetSnowyNumber(PetSnowyEntity, NumberEntity):
    """Representation of a PetSnowy number."""

    entity_description: PetSnowyNumberDescription

    def __init__(
        self,
        coordinator: PetSnowyCoordinator,
        description: PetSnowyNumberDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        state = self.coordinator.data
        if state is None:
            return None
        value = getattr(state, self.entity_description.value_fn, None)
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Set the number value."""
        await getattr(self.coordinator.device, self.entity_description.set_fn)(
            int(value)
        )
        await self.coordinator.async_request_refresh()
