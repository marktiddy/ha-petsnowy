"""Unit tests for the cloud-backed OilClear fountain driver."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.petsnowy.oilclear import (
    OilClearCloudFountain,
    OilClearCode,
    OilClearState,
)

FULL_STATUS = [
    {"code": "switch", "value": True},
    {"code": "work_mode", "value": "night"},
    {"code": "filter_days", "value": 28},
    {"code": "pump_time", "value": 3},
    {"code": "filter_life", "value": 25},
    {"code": "heating", "value": True},
    {"code": "battery_charge_status", "value": "charge"},
    {"code": "water_temp", "value": 5},
    {"code": "battery_capacity", "value": 100},
    {"code": "curr_weight", "value": 2881},
    {"code": "light", "value": True},
]


class TestOilClearState:
    """Validate cloud status parsing for the OilClear (PS-120)."""

    def test_parses_full_status(self) -> None:
        """A full cloud status payload maps to the expected fields."""
        state = OilClearState.from_status(FULL_STATUS)
        assert state.switch is True
        assert state.work_mode == "night"
        assert state.filter_days == 28
        assert state.pump_time == 3
        assert state.filter_life == 25
        assert state.heating is True
        assert state.battery_charge_status == "charge"
        assert state.water_temp == 5
        assert state.battery_capacity == 100
        assert state.curr_weight == 2881
        assert state.light is True

    def test_light_and_charge_status_do_not_collide(self) -> None:
        """Light and battery charge status are distinct codes."""
        state = OilClearState.from_status(
            [
                {"code": "battery_charge_status", "value": "charge"},
                {"code": "light", "value": False},
            ]
        )
        assert state.light is False
        assert state.battery_charge_status == "charge"

    def test_missing_codes_default_safely(self) -> None:
        """Absent codes fall back to defaults instead of raising."""
        state = OilClearState.from_status([])
        assert state.switch is False
        assert state.work_mode == "normal"
        assert state.curr_weight == 0
        assert state.battery_charge_status == ""

    def test_unknown_work_mode_falls_back_to_normal(self) -> None:
        """An unexpected work_mode value degrades gracefully."""
        state = OilClearState.from_status([{"code": "work_mode", "value": "bogus"}])
        assert state.work_mode == "normal"


class TestOilClearCommands:
    """Validate that commands issue the correct Tuya cloud codes."""

    def _device(self) -> OilClearCloudFountain:
        dev = OilClearCloudFountain("dev123", "eu", "id", "secret")
        dev._cloud = MagicMock()
        dev._cloud.sendcommand = MagicMock(return_value={"success": True})
        dev._cloud.getstatus = MagicMock(
            return_value={"success": True, "result": FULL_STATUS}
        )
        return dev

    @pytest.mark.asyncio
    async def test_turn_on_sends_switch(self) -> None:
        """Power on issues the switch code."""
        dev = self._device()
        await dev.turn_on()
        dev._cloud.sendcommand.assert_called_once_with(
            "dev123", {"commands": [{"code": "switch", "value": True}]}
        )

    @pytest.mark.asyncio
    async def test_set_light_uses_light_code(self) -> None:
        """The indicator light is its own code, not the charge status."""
        dev = self._device()
        await dev.set_light(True)
        dev._cloud.sendcommand.assert_called_once_with(
            "dev123", {"commands": [{"code": OilClearCode.LIGHT, "value": True}]}
        )

    @pytest.mark.asyncio
    async def test_set_heating_sends_heating_code(self) -> None:
        """Heating toggles the heating code."""
        dev = self._device()
        await dev.set_heating(False)
        dev._cloud.sendcommand.assert_called_once_with(
            "dev123", {"commands": [{"code": "heating", "value": False}]}
        )

    @pytest.mark.asyncio
    async def test_reset_weight_sends_button(self) -> None:
        """Weight calibration issues the reset_weight code."""
        dev = self._device()
        await dev.reset_weight()
        dev._cloud.sendcommand.assert_called_once_with(
            "dev123", {"commands": [{"code": "reset_weight", "value": True}]}
        )

    @pytest.mark.asyncio
    async def test_filter_reminder_out_of_range_raises(self) -> None:
        """Filter reminder is clamped to the device's 0-30 range."""
        dev = self._device()
        with pytest.raises(ValueError):
            await dev.set_filter_reminder(60)

    @pytest.mark.asyncio
    async def test_get_state_parses_cloud_status(self) -> None:
        """get_state maps the cloud status payload to an OilClearState."""
        dev = self._device()
        state = await dev.get_state()
        assert isinstance(state, OilClearState)
        assert state.curr_weight == 2881
        assert state.switch is True

    @pytest.mark.asyncio
    async def test_get_state_raises_on_failure(self) -> None:
        """A failed cloud read surfaces as an error."""
        from petsnowy import ConnectionError as PetSnowyConnectionError

        dev = self._device()
        dev._cloud.getstatus = MagicMock(
            return_value={"success": False, "msg": "device offline"}
        )
        with pytest.raises(PetSnowyConnectionError):
            await dev.get_state()

    @pytest.mark.asyncio
    async def test_command_failure_raises(self) -> None:
        """A rejected command surfaces as a CommandError."""
        from petsnowy import CommandError

        dev = self._device()
        dev._cloud.sendcommand = MagicMock(
            return_value={"success": False, "msg": "nope"}
        )
        with pytest.raises(CommandError):
            await dev.turn_on()
