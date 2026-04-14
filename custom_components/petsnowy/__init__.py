"""PetSnowy integration for Home Assistant."""

from __future__ import annotations

from typing import TypeAlias

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er

from .const import CONF_DEVICE_ID, CONF_DEVICE_TYPE, DEVICE_TYPE_PURIFIER, DOMAIN, PLATFORMS
from .coordinator import PetSnowyCoordinator

PetSnowyConfigEntry: TypeAlias = ConfigEntry[PetSnowyCoordinator]

# Entity keys replaced by the fan entity in the purifier fan refactor.
_PURIFIER_ORPHANED_ENTITIES: list[tuple[str, str]] = [
    ("switch", "purifier_power"),
    ("select", "fan_speed"),
    ("select", "purifier_mode"),
]


async def async_setup_entry(hass: HomeAssistant, entry: PetSnowyConfigEntry) -> bool:
    """Set up PetSnowy from a config entry."""
    if entry.data.get(CONF_DEVICE_TYPE) == DEVICE_TYPE_PURIFIER:
        _cleanup_orphaned_purifier_entities(hass, entry)

    coordinator = PetSnowyCoordinator(hass, entry)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        await coordinator.async_shutdown()
        raise ConfigEntryNotReady(
            f"Unable to connect to PetSnowy device: {err}"
        ) from err
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: PetSnowyConfigEntry
) -> None:
    """Reload the config entry so option changes (weight offset, external sensor) take effect."""
    await hass.config_entries.async_reload(entry.entry_id)


def _cleanup_orphaned_purifier_entities(
    hass: HomeAssistant, entry: PetSnowyConfigEntry
) -> None:
    """Remove legacy purifier entities replaced by the fan entity."""
    registry = er.async_get(hass)
    device_id = entry.data[CONF_DEVICE_ID]
    for platform, key in _PURIFIER_ORPHANED_ENTITIES:
        unique_id = f"{device_id}_{key}"
        entity_id = registry.async_get_entity_id(platform, DOMAIN, unique_id)
        if entity_id is not None:
            registry.async_remove(entity_id)


async def async_unload_entry(hass: HomeAssistant, entry: PetSnowyConfigEntry) -> bool:
    """Unload a PetSnowy config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_shutdown()
    return unload_ok
