"""PetSnowy integration for Home Assistant."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import PLATFORMS
from .coordinator import PetSnowyCoordinator

type PetSnowyConfigEntry = ConfigEntry[PetSnowyCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: PetSnowyConfigEntry) -> bool:
    """Set up PetSnowy from a config entry."""
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
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PetSnowyConfigEntry) -> bool:
    """Unload a PetSnowy config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_shutdown()
    return unload_ok
