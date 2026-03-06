"""Fan platform for PetSnowy Air Purifier."""

from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from . import PetSnowyConfigEntry
from .const import DEVICE_TYPE_PURIFIER
from .coordinator import PetSnowyCoordinator
from .entity import PetSnowyEntity

SPEED_LIST = ["1", "2", "3", "4", "5", "6"]
PRESET_MODES = ["auto", "sleep"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PetSnowyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PetSnowy fan entities."""
    coordinator = entry.runtime_data
    if coordinator.device_type == DEVICE_TYPE_PURIFIER:
        async_add_entities([PetSnowyPurifierFan(coordinator)])


class PetSnowyPurifierFan(PetSnowyEntity, FanEntity):
    """Representation of the PetSnowy Air Purifier as a fan entity."""

    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_speed_count = len(SPEED_LIST)
    _attr_preset_modes = PRESET_MODES
    _attr_translation_key = "air_purifier"

    def __init__(self, coordinator: PetSnowyCoordinator) -> None:
        super().__init__(coordinator, "air_purifier")

    @property
    def is_on(self) -> bool | None:
        """Return True if the purifier is on."""
        state = self.coordinator.data
        if state is None:
            return None
        return state.switch

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        state = self.coordinator.data
        if state is None or not state.switch:
            return 0
        return ordered_list_item_to_percentage(SPEED_LIST, state.speed)

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        state = self.coordinator.data
        if state is None:
            return None
        return str(state.mode)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the purifier."""
        await self.coordinator.device.turn_on()
        if percentage is not None:
            speed = percentage_to_ordered_list_item(SPEED_LIST, percentage)
            await self.coordinator.device.set_speed(speed)
        if preset_mode is not None:
            await self.coordinator.device.set_mode(preset_mode)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the purifier."""
        await self.coordinator.device.turn_off()
        await self.coordinator.async_request_refresh()

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage."""
        if percentage == 0:
            await self.async_turn_off()
            return
        speed = percentage_to_ordered_list_item(SPEED_LIST, percentage)
        await self.coordinator.device.set_speed(speed)
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode."""
        await self.coordinator.device.set_mode(preset_mode)
        await self.coordinator.async_request_refresh()
