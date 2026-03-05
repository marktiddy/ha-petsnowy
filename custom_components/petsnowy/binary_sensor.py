"""Binary sensor platform for PetSnowy integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from petsnowy import Fault

from . import PetSnowyConfigEntry
from petsnowy.purifier import PurifierFault

from .const import (
    DEVICE_TYPE_FEEDER,
    DEVICE_TYPE_LITTERBOX,
    DEVICE_TYPE_PURIFIER,
)
from .coordinator import PetSnowyCoordinator
from .entity import PetSnowyEntity


@dataclass(frozen=True, kw_only=True)
class PetSnowyBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a PetSnowy binary sensor entity."""

    is_on_fn: Callable[[Any], bool | None]


LITTERBOX_BINARY_SENSORS: tuple[PetSnowyBinarySensorDescription, ...] = (
    PetSnowyBinarySensorDescription(
        key="fault_top_cover",
        translation_key="fault_top_cover",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:alert",
        is_on_fn=lambda s: bool(s.faults & Fault.TOP_COVER),
    ),
    PetSnowyBinarySensorDescription(
        key="fault_drawer",
        translation_key="fault_drawer",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:alert",
        is_on_fn=lambda s: bool(s.faults & Fault.DRAWER),
    ),
    PetSnowyBinarySensorDescription(
        key="fault_drawer_full",
        translation_key="fault_drawer_full",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:delete-alert",
        is_on_fn=lambda s: bool(s.faults & Fault.DRAWER_FULL),
    ),
    PetSnowyBinarySensorDescription(
        key="fault_cat_stuck",
        translation_key="fault_cat_stuck",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:cat",
        is_on_fn=lambda s: bool(s.faults & Fault.CAT_STUCK),
    ),
    PetSnowyBinarySensorDescription(
        key="fault_check",
        translation_key="fault_check",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:alert-circle",
        is_on_fn=lambda s: bool(s.faults & Fault.CHECK_FAULT),
    ),
    PetSnowyBinarySensorDescription(
        key="fault_cat_stayed_long",
        translation_key="fault_cat_stayed_long",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:cat",
        is_on_fn=lambda s: bool(s.faults & Fault.CAT_STAYED_LONG),
    ),
    PetSnowyBinarySensorDescription(
        key="fault_trouble_removal",
        translation_key="fault_trouble_removal",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:alert",
        is_on_fn=lambda s: bool(s.faults & Fault.TROUBLE_REMOVAL),
    ),
)

PURIFIER_BINARY_SENSORS: tuple[PetSnowyBinarySensorDescription, ...] = (
    PetSnowyBinarySensorDescription(
        key="fault_hall",
        translation_key="fault_hall",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:alert",
        is_on_fn=lambda s: bool(s.faults & PurifierFault.HALL),
    ),
    PetSnowyBinarySensorDescription(
        key="fault_topple_over",
        translation_key="fault_topple_over",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:alert",
        is_on_fn=lambda s: bool(s.faults & PurifierFault.TOPPLE_OVER),
    ),
    PetSnowyBinarySensorDescription(
        key="fault_fan",
        translation_key="fault_fan",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:fan-alert",
        is_on_fn=lambda s: bool(s.faults & PurifierFault.FAN_ERR),
    ),
    PetSnowyBinarySensorDescription(
        key="fault_filter_missing",
        translation_key="fault_filter_missing",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:air-filter",
        is_on_fn=lambda s: bool(s.faults & PurifierFault.FILTER_NO),
    ),
)

FEEDER_BINARY_SENSORS: tuple[PetSnowyBinarySensorDescription, ...] = (
    PetSnowyBinarySensorDescription(
        key="cover",
        translation_key="cover",
        device_class=BinarySensorDeviceClass.OPENING,
        is_on_fn=lambda s: not s.cover_closed,
    ),
)

_BINARY_SENSORS_BY_TYPE: dict[
    str, tuple[PetSnowyBinarySensorDescription, ...]
] = {
    DEVICE_TYPE_LITTERBOX: LITTERBOX_BINARY_SENSORS,
    DEVICE_TYPE_PURIFIER: PURIFIER_BINARY_SENSORS,
    DEVICE_TYPE_FEEDER: FEEDER_BINARY_SENSORS,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PetSnowyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PetSnowy binary sensor entities."""
    coordinator = entry.runtime_data
    descriptions = _BINARY_SENSORS_BY_TYPE.get(coordinator.device_type, ())
    async_add_entities(
        PetSnowyBinarySensor(coordinator, desc) for desc in descriptions
    )


class PetSnowyBinarySensor(PetSnowyEntity, BinarySensorEntity):
    """Representation of a PetSnowy binary sensor."""

    entity_description: PetSnowyBinarySensorDescription

    def __init__(
        self,
        coordinator: PetSnowyCoordinator,
        description: PetSnowyBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return True if the binary sensor is on."""
        state = self.coordinator.data
        if state is None:
            return None
        return self.entity_description.is_on_fn(state)
