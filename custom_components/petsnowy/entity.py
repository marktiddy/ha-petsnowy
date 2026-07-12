"""Base entity for PetSnowy integration."""

from __future__ import annotations

import dataclasses
from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_ID, CONF_DEVICE_TYPE, DEVICE_TYPES, DOMAIN
from .coordinator import PetSnowyCoordinator


class PetSnowyEntity(CoordinatorEntity[PetSnowyCoordinator]):
    """Base class for all PetSnowy entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PetSnowyCoordinator, key: str) -> None:
        super().__init__(coordinator)
        device_id = coordinator.config_entry.data[CONF_DEVICE_ID]
        self._attr_unique_id = f"{device_id}_{key}"

    def _set_optimistic_state(self, attr: str, value: Any) -> None:
        """Optimistically reflect a just-issued command in the coordinator state.

        Cloud/battery devices (the OilClear) queue commands and only report the
        new value once they next wake, so an immediate poll reads the stale
        value and the UI snaps back. Patch the cached state instead and let the
        next scheduled poll reconcile it with what the device actually did.
        """
        data = self.coordinator.data
        if data is None or not dataclasses.is_dataclass(data):
            return
        try:
            new_data = dataclasses.replace(data, **{attr: value})
        except TypeError:
            return
        self.coordinator.async_set_updated_data(new_data)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for the device registry."""
        entry = self.coordinator.config_entry
        device_type = entry.data[CONF_DEVICE_TYPE]
        return DeviceInfo(
            identifiers={(DOMAIN, entry.data[CONF_DEVICE_ID])},
            name=entry.title,
            manufacturer="PetSnowy",
            model=DEVICE_TYPES.get(device_type, device_type),
        )
