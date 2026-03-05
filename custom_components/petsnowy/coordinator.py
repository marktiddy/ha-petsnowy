"""Data update coordinator for PetSnowy devices."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from petsnowy import Feeder, Fountain, PetSnowy, Purifier

from .const import (
    CONF_ADDRESS,
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_LOCAL_KEY,
    CONF_VERSION,
    DEFAULT_SCAN_INTERVAL,
    DEVICE_TYPE_FEEDER,
    DEVICE_TYPE_FOUNTAIN,
    DEVICE_TYPE_LITTERBOX,
    DEVICE_TYPE_PURIFIER,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

_DEVICE_CLASSES: dict[str, type] = {
    DEVICE_TYPE_LITTERBOX: PetSnowy,
    DEVICE_TYPE_FOUNTAIN: Fountain,
    DEVICE_TYPE_PURIFIER: Purifier,
    DEVICE_TYPE_FEEDER: Feeder,
}


class PetSnowyCoordinator(DataUpdateCoordinator[Any]):
    """Coordinator that polls a PetSnowy device for state updates."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.device_type: str = entry.data[CONF_DEVICE_TYPE]

        cls = _DEVICE_CLASSES[self.device_type]
        self.device: PetSnowy | Fountain | Purifier | Feeder = cls(
            entry.data[CONF_DEVICE_ID],
            entry.data[CONF_ADDRESS],
            entry.data[CONF_LOCAL_KEY],
            version=entry.data[CONF_VERSION],
        )
        self._connected = False

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.data[CONF_DEVICE_ID]}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> Any:
        """Fetch state from the device."""
        try:
            if not self._connected:
                await self.device.connect()
                self._connected = True
            return await self.device.get_state()
        except Exception as err:
            self._connected = False
            try:
                await self.device.disconnect()
            except Exception:  # noqa: BLE001
                pass
            raise UpdateFailed(f"Error communicating with device: {err}") from err

    async def async_shutdown(self) -> None:
        """Disconnect from the device on shutdown."""
        await super().async_shutdown()
        if self._connected:
            await self.device.disconnect()
            self._connected = False
