"""Select platform for PetSnowy integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import PetSnowyConfigEntry
from .const import DEVICE_TYPE_FOUNTAIN, DEVICE_TYPE_PURIFIER
from .coordinator import PetSnowyCoordinator
from .entity import PetSnowyEntity


@dataclass(frozen=True, kw_only=True)
class PetSnowySelectDescription(SelectEntityDescription):
    """Describe a PetSnowy select entity."""

    value_fn: str
    set_fn: str


FOUNTAIN_SELECTS: tuple[PetSnowySelectDescription, ...] = (
    PetSnowySelectDescription(
        key="work_mode",
        translation_key="work_mode",
        icon="mdi:water-pump",
        options=["normal", "night"],
        value_fn="work_mode",
        set_fn="set_work_mode",
    ),
)

PURIFIER_SELECTS: tuple[PetSnowySelectDescription, ...] = (
    PetSnowySelectDescription(
        key="purifier_mode",
        translation_key="purifier_mode",
        icon="mdi:fan",
        options=["auto", "sleep"],
        value_fn="mode",
        set_fn="set_mode",
    ),
    PetSnowySelectDescription(
        key="fan_speed",
        translation_key="fan_speed",
        icon="mdi:fan",
        options=["1", "2", "3", "4", "5", "6"],
        value_fn="speed",
        set_fn="set_speed",
    ),
    PetSnowySelectDescription(
        key="countdown",
        translation_key="countdown",
        icon="mdi:timer",
        options=["cancel", "1h", "2h", "3h", "4h", "5h"],
        value_fn="countdown_set",
        set_fn="set_countdown",
    ),
)

_SELECTS_BY_TYPE: dict[str, tuple[PetSnowySelectDescription, ...]] = {
    DEVICE_TYPE_FOUNTAIN: FOUNTAIN_SELECTS,
    DEVICE_TYPE_PURIFIER: PURIFIER_SELECTS,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PetSnowyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PetSnowy select entities."""
    coordinator = entry.runtime_data
    descriptions = _SELECTS_BY_TYPE.get(coordinator.device_type, ())
    async_add_entities(
        PetSnowySelect(coordinator, desc) for desc in descriptions
    )


class PetSnowySelect(PetSnowyEntity, SelectEntity):
    """Representation of a PetSnowy select."""

    entity_description: PetSnowySelectDescription

    def __init__(
        self,
        coordinator: PetSnowyCoordinator,
        description: PetSnowySelectDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        state = self.coordinator.data
        if state is None:
            return None
        value = getattr(state, self.entity_description.value_fn, None)
        return str(value) if value is not None else None

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await getattr(self.coordinator.device, self.entity_description.set_fn)(option)
        await self.coordinator.async_request_refresh()
