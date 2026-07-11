"""Config flow for PetSnowy integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import (
    CONF_ADDRESS,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_EXTERNAL_MOTION_SENSOR,
    CONF_LOCAL_KEY,
    CONF_PIR_GRACE_MINUTES,
    CONF_REGION,
    CONF_VERSION,
    CONF_WEIGHT_OFFSET,
    DEFAULT_PIR_GRACE_MINUTES,
    DEFAULT_REGION,
    DEFAULT_VERSIONS,
    DEVICE_TYPE_LITTERBOX,
    DEVICE_TYPE_OILCLEAR,
    DEVICE_TYPES,
    DOMAIN,
    TUYA_REGIONS,
)
from .coordinator import build_device

_LOGGER = logging.getLogger(__name__)


class PetSnowyConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for PetSnowy."""

    VERSION = 1

    def __init__(self) -> None:
        self._device_type: str = ""

    @staticmethod
    @callback  # type: ignore[untyped-decorator]
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow for this config entry."""
        return PetSnowyOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: Select device type."""
        if user_input is not None:
            self._device_type = user_input[CONF_DEVICE_TYPE]
            if self._device_type == DEVICE_TYPE_OILCLEAR:
                return await self.async_step_cloud()
            return await self.async_step_device()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_DEVICE_TYPE): vol.In(DEVICE_TYPES)}
            ),
        )

    async def _validate_and_create(
        self, device_id: str, data: dict[str, Any]
    ) -> ConfigFlowResult | str:
        """Validate connectivity for `data`; create the entry or return an error.

        Returns the created entry result on success, or an error key on failure.
        """
        await self.async_set_unique_id(device_id)
        self._abort_if_unique_id_configured()

        device = build_device(self._device_type, data)
        try:
            await device.connect()
            await device.disconnect()
        except Exception:
            _LOGGER.exception("Failed to connect to PetSnowy device")
            return "cannot_connect"

        return self.async_create_entry(
            title=f"PetSnowy {DEVICE_TYPES[self._device_type]}",
            data={CONF_DEVICE_TYPE: self._device_type, **data},
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2 (local devices): Enter LAN credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data = {
                CONF_DEVICE_ID: user_input[CONF_DEVICE_ID],
                CONF_ADDRESS: user_input[CONF_ADDRESS],
                CONF_LOCAL_KEY: user_input[CONF_LOCAL_KEY],
                CONF_VERSION: user_input.get(
                    CONF_VERSION, DEFAULT_VERSIONS[self._device_type]
                ),
            }
            result = await self._validate_and_create(user_input[CONF_DEVICE_ID], data)
            if isinstance(result, str):
                errors["base"] = result
            else:
                return result

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

    async def async_step_cloud(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2 (OilClear): Enter Tuya Cloud credentials.

        The OilClear is power-managed and unreachable on the LAN between cloud
        syncs, so it is polled through the Tuya Cloud API instead.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            data = {
                CONF_DEVICE_ID: user_input[CONF_DEVICE_ID],
                CONF_REGION: user_input[CONF_REGION],
                CONF_CLIENT_ID: user_input[CONF_CLIENT_ID],
                CONF_CLIENT_SECRET: user_input[CONF_CLIENT_SECRET],
            }
            result = await self._validate_and_create(user_input[CONF_DEVICE_ID], data)
            if isinstance(result, str):
                errors["base"] = result
            else:
                return result

        return self.async_show_form(
            step_id="cloud",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_ID): str,
                    vol.Required(CONF_REGION, default=DEFAULT_REGION): vol.In(
                        TUYA_REGIONS
                    ),
                    vol.Required(CONF_CLIENT_ID): str,
                    vol.Required(CONF_CLIENT_SECRET): str,
                }
            ),
            errors=errors,
        )


class PetSnowyOptionsFlow(OptionsFlow):
    """Handle litterbox meta-sensor calibration options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage weight offset and external motion sensor."""
        if self.config_entry.data.get(CONF_DEVICE_TYPE) != DEVICE_TYPE_LITTERBOX:
            return self.async_abort(reason="not_supported")

        if user_input is not None:
            cleaned: dict[str, Any] = {
                CONF_WEIGHT_OFFSET: int(user_input.get(CONF_WEIGHT_OFFSET, 0)),
                CONF_PIR_GRACE_MINUTES: int(
                    user_input.get(CONF_PIR_GRACE_MINUTES, DEFAULT_PIR_GRACE_MINUTES)
                ),
            }
            motion = user_input.get(CONF_EXTERNAL_MOTION_SENSOR)
            if motion:
                cleaned[CONF_EXTERNAL_MOTION_SENSOR] = motion
            return self.async_create_entry(title="", data=cleaned)

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_WEIGHT_OFFSET,
                    default=options.get(CONF_WEIGHT_OFFSET, 0),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=-2000,
                        max=2000,
                        step=1,
                        unit_of_measurement="g",
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_EXTERNAL_MOTION_SENSOR,
                    description={
                        "suggested_value": options.get(CONF_EXTERNAL_MOTION_SENSOR)
                    },
                ): EntitySelector(
                    EntitySelectorConfig(
                        domain="binary_sensor",
                        device_class="motion",
                    )
                ),
                vol.Optional(
                    CONF_PIR_GRACE_MINUTES,
                    default=options.get(
                        CONF_PIR_GRACE_MINUTES, DEFAULT_PIR_GRACE_MINUTES
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0,
                        max=30,
                        step=1,
                        unit_of_measurement="min",
                        mode=NumberSelectorMode.BOX,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
