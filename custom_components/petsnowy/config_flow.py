"""Config flow for PetSnowy integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import (
    CONF_ADDRESS,
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_LOCAL_KEY,
    CONF_VERSION,
    DEFAULT_VERSIONS,
    DEVICE_TYPES,
    DOMAIN,
)
from .coordinator import _DEVICE_CLASSES

_LOGGER = logging.getLogger(__name__)


class PetSnowyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PetSnowy."""

    VERSION = 1

    def __init__(self) -> None:
        self._device_type: str = ""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: Select device type."""
        if user_input is not None:
            self._device_type = user_input[CONF_DEVICE_TYPE]
            return await self.async_step_device()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_DEVICE_TYPE): vol.In(DEVICE_TYPES)}
            ),
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: Enter device credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID]
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()

            version = user_input.get(CONF_VERSION, DEFAULT_VERSIONS[self._device_type])

            cls = _DEVICE_CLASSES[self._device_type]
            device = cls(
                device_id,
                user_input[CONF_ADDRESS],
                user_input[CONF_LOCAL_KEY],
                version=version,
            )
            try:
                await device.connect()
                await device.disconnect()
            except Exception:
                _LOGGER.exception("Failed to connect to PetSnowy device")
                errors["base"] = "cannot_connect"

            if not errors:
                return self.async_create_entry(
                    title=f"PetSnowy {DEVICE_TYPES[self._device_type]}",
                    data={
                        CONF_DEVICE_TYPE: self._device_type,
                        CONF_DEVICE_ID: device_id,
                        CONF_ADDRESS: user_input[CONF_ADDRESS],
                        CONF_LOCAL_KEY: user_input[CONF_LOCAL_KEY],
                        CONF_VERSION: version,
                    },
                )

        default_version = DEFAULT_VERSIONS[self._device_type]

        return self.async_show_form(
            step_id="device",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_ID): str,
                    vol.Required(CONF_ADDRESS): str,
                    vol.Required(CONF_LOCAL_KEY): str,
                    vol.Optional(CONF_VERSION, default=default_version): vol.Coerce(
                        float
                    ),
                }
            ),
            errors=errors,
        )
