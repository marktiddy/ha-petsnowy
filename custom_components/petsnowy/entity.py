"""Base entity for PetSnowy integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_ID, CONF_DEVICE_TYPE, DEVICE_TYPES, DOMAIN
from .coordinator import PetSnowyCoordinator


class PetSnowyEntity(CoordinatorEntity[PetSnowyCoordinator]):
    """Base class for all PetSnowy entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PetSnowyCoordinator, key: str) -> None:
        super().__init__(coordinator)
        device_id = coordinator.entry.data[CONF_DEVICE_ID]
        self._attr_unique_id = f"{device_id}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for the device registry."""
        entry = self.coordinator.entry
        device_type = entry.data[CONF_DEVICE_TYPE]
        return DeviceInfo(
            identifiers={(DOMAIN, entry.data[CONF_DEVICE_ID])},
            name=entry.title,
            manufacturer="PetSnowy",
            model=DEVICE_TYPES.get(device_type, device_type),
        )
