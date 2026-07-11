"""Button platform for PetSnowy integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import PetSnowyConfigEntry
from .const import (
    DEVICE_TYPE_FEEDER,
    DEVICE_TYPE_FOUNTAIN,
    DEVICE_TYPE_LITTERBOX,
    DEVICE_TYPE_OILCLEAR,
)
from .coordinator import PetSnowyCoordinator
from .entity import PetSnowyEntity


@dataclass(frozen=True, kw_only=True)
class PetSnowyButtonDescription(ButtonEntityDescription):
    """Describe a PetSnowy button entity."""

    press_fn: str | None = None
    coordinator_fn: str | None = None


LITTERBOX_BUTTONS: tuple[PetSnowyButtonDescription, ...] = (
    PetSnowyButtonDescription(
        key="clean",
        translation_key="clean",
        icon="mdi:broom",
        press_fn="clean",
    ),
    PetSnowyButtonDescription(
        key="deodorize",
        translation_key="deodorize",
        icon="mdi:spray",
        press_fn="deodorize",
    ),
    PetSnowyButtonDescription(
        key="empty_litter",
        translation_key="empty_litter",
        icon="mdi:delete-empty",
        press_fn="empty_litter",
    ),
    PetSnowyButtonDescription(
        key="cancel_empty",
        translation_key="cancel_empty",
        icon="mdi:cancel",
        press_fn="cancel_empty",
    ),
    PetSnowyButtonDescription(
        key="pause",
        translation_key="pause",
        icon="mdi:pause",
        press_fn="pause",
    ),
    PetSnowyButtonDescription(
        key="resume",
        translation_key="resume",
        icon="mdi:play",
        press_fn="resume",
    ),
    PetSnowyButtonDescription(
        key="reset_filter",
        translation_key="reset_filter",
        icon="mdi:air-filter",
        press_fn="reset_filter",
    ),
    PetSnowyButtonDescription(
        key="calibrate_weight",
        translation_key="calibrate_weight",
        icon="mdi:scale-balance",
        press_fn="calibrate_weight",
    ),
    PetSnowyButtonDescription(
        key="reset_litter_age",
        translation_key="reset_litter_age",
        icon="mdi:restart",
        coordinator_fn="mark_litter_changed",
    ),
)

FOUNTAIN_BUTTONS: tuple[PetSnowyButtonDescription, ...] = (
    PetSnowyButtonDescription(
        key="fountain_reset_filter",
        translation_key="reset_filter",
        icon="mdi:air-filter",
        press_fn="reset_filter",
    ),
    PetSnowyButtonDescription(
        key="reset_pump",
        translation_key="reset_pump",
        icon="mdi:pump",
        press_fn="reset_pump",
    ),
)

OILCLEAR_BUTTONS: tuple[PetSnowyButtonDescription, ...] = (
    PetSnowyButtonDescription(
        key="oilclear_reset_filter",
        translation_key="reset_filter",
        icon="mdi:air-filter",
        press_fn="reset_filter",
    ),
    PetSnowyButtonDescription(
        key="reset_pump",
        translation_key="reset_pump",
        icon="mdi:pump",
        press_fn="reset_pump",
    ),
    PetSnowyButtonDescription(
        key="oilclear_calibrate_weight",
        translation_key="calibrate_weight",
        icon="mdi:scale-balance",
        press_fn="reset_weight",
    ),
)

FEEDER_BUTTONS: tuple[PetSnowyButtonDescription, ...] = (
    PetSnowyButtonDescription(
        key="quick_feed",
        translation_key="quick_feed",
        icon="mdi:food-drumstick",
        press_fn="quick_feed",
    ),
)

_BUTTONS_BY_TYPE: dict[str, tuple[PetSnowyButtonDescription, ...]] = {
    DEVICE_TYPE_LITTERBOX: LITTERBOX_BUTTONS,
    DEVICE_TYPE_FOUNTAIN: FOUNTAIN_BUTTONS,
    DEVICE_TYPE_OILCLEAR: OILCLEAR_BUTTONS,
    DEVICE_TYPE_FEEDER: FEEDER_BUTTONS,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PetSnowyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PetSnowy button entities."""
    coordinator = entry.runtime_data
    descriptions = _BUTTONS_BY_TYPE.get(coordinator.device_type, ())
    async_add_entities(PetSnowyButton(coordinator, desc) for desc in descriptions)


class PetSnowyButton(PetSnowyEntity, ButtonEntity):
    """Representation of a PetSnowy button."""

    entity_description: PetSnowyButtonDescription

    def __init__(
        self,
        coordinator: PetSnowyCoordinator,
        description: PetSnowyButtonDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        """Handle the button press."""
        desc = self.entity_description
        if desc.press_fn:
            await getattr(self.coordinator.device, desc.press_fn)()
        if desc.coordinator_fn:
            getattr(self.coordinator, desc.coordinator_fn)()
        await self.coordinator.async_request_refresh()
