"""Switch platform for PetSnowy integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import PetSnowyConfigEntry
from .const import (
    DEVICE_TYPE_FOUNTAIN,
    DEVICE_TYPE_LITTERBOX,
    DEVICE_TYPE_OILCLEAR,
    DEVICE_TYPE_PURIFIER,
)
from .coordinator import PetSnowyCoordinator
from .entity import PetSnowyEntity


@dataclass(frozen=True, kw_only=True)
class PetSnowySwitchDescription(SwitchEntityDescription):
    """Describe a PetSnowy switch entity."""

    value_fn: str
    # For bool-setter pattern: method(bool)
    set_fn: str | None = None
    # For on/off method pattern: on_method(), off_method()
    on_fn: str | None = None
    off_fn: str | None = None
    # Optimistically hold the requested state until the next poll (for cloud/
    # battery devices that apply commands only once awake).
    optimistic: bool = False


LITTERBOX_SWITCHES: tuple[PetSnowySwitchDescription, ...] = (
    PetSnowySwitchDescription(
        key="auto_clean",
        translation_key="auto_clean",
        icon="mdi:broom",
        value_fn="auto_clean",
        set_fn="set_auto_clean",
    ),
    PetSnowySwitchDescription(
        key="sleep_mode",
        translation_key="sleep_mode",
        icon="mdi:sleep",
        value_fn="sleep_mode",
        set_fn="set_sleep_mode",
    ),
    PetSnowySwitchDescription(
        key="light",
        translation_key="light",
        icon="mdi:lightbulb",
        value_fn="light",
        set_fn="set_light",
    ),
    PetSnowySwitchDescription(
        key="child_lock",
        translation_key="child_lock",
        icon="mdi:lock",
        value_fn="child_locked",
        set_fn="set_child_lock",
    ),
    PetSnowySwitchDescription(
        key="auto_deodorize",
        translation_key="auto_deodorize",
        icon="mdi:spray",
        value_fn="auto_deodorize",
        set_fn="set_auto_deodorize",
    ),
    PetSnowySwitchDescription(
        key="scheduled_deodorize",
        translation_key="scheduled_deodorize",
        icon="mdi:spray",
        value_fn="scheduled_deodorize",
        set_fn="set_scheduled_deodorize",
    ),
    PetSnowySwitchDescription(
        key="scheduled_clean",
        translation_key="scheduled_clean",
        icon="mdi:broom",
        value_fn="scheduled_clean",
        set_fn="set_scheduled_clean",
    ),
)

FOUNTAIN_SWITCHES: tuple[PetSnowySwitchDescription, ...] = (
    PetSnowySwitchDescription(
        key="power",
        translation_key="power",
        icon="mdi:power",
        value_fn="switch",
        on_fn="turn_on",
        off_fn="turn_off",
    ),
    PetSnowySwitchDescription(
        key="fountain_light",
        translation_key="light",
        icon="mdi:lightbulb",
        value_fn="light",
        set_fn="set_light",
    ),
)

OILCLEAR_SWITCHES: tuple[PetSnowySwitchDescription, ...] = (
    PetSnowySwitchDescription(
        key="heating",
        translation_key="heating",
        icon="mdi:radiator",
        value_fn="heating",
        set_fn="set_heating",
        optimistic=True,
    ),
)

PURIFIER_SWITCHES: tuple[PetSnowySwitchDescription, ...] = (
    PetSnowySwitchDescription(
        key="anion",
        translation_key="anion",
        icon="mdi:atom",
        value_fn="anion",
        set_fn="set_anion",
    ),
)

_SWITCHES_BY_TYPE: dict[str, tuple[PetSnowySwitchDescription, ...]] = {
    DEVICE_TYPE_LITTERBOX: LITTERBOX_SWITCHES,
    DEVICE_TYPE_FOUNTAIN: FOUNTAIN_SWITCHES,
    DEVICE_TYPE_OILCLEAR: OILCLEAR_SWITCHES,
    DEVICE_TYPE_PURIFIER: PURIFIER_SWITCHES,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PetSnowyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PetSnowy switch entities."""
    coordinator = entry.runtime_data
    descriptions = _SWITCHES_BY_TYPE.get(coordinator.device_type, ())
    async_add_entities(PetSnowySwitch(coordinator, desc) for desc in descriptions)


class PetSnowySwitch(PetSnowyEntity, SwitchEntity):
    """Representation of a PetSnowy switch."""

    entity_description: PetSnowySwitchDescription

    def __init__(
        self,
        coordinator: PetSnowyCoordinator,
        description: PetSnowySwitchDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return True if the switch is on."""
        state = self.coordinator.data
        if state is None:
            return None
        return getattr(state, self.entity_description.value_fn, None)

    async def _async_set(self, value: bool) -> None:
        """Issue the command, then optimistically hold or poll for the result."""
        desc = self.entity_description
        if value and desc.on_fn:
            await getattr(self.coordinator.device, desc.on_fn)()
        elif not value and desc.off_fn:
            await getattr(self.coordinator.device, desc.off_fn)()
        elif desc.set_fn:
            await getattr(self.coordinator.device, desc.set_fn)(value)
        if desc.optimistic:
            self._set_optimistic_state(desc.value_fn, value)
        else:
            await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._async_set(False)
