"""Unit tests for the local OilClear fountain driver."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.petsnowy.oilclear import (
    OilClearDPS,
    OilClearFountain,
    OilClearState,
)


class TestOilClearState:
    """Validate DP parsing for the OilClear (PS-120)."""

    def test_parses_full_state(self) -> None:
        """A full DPS dump maps to the expected fields."""
        state = OilClearState.from_dps(
            {
                "1": True,
                "2": "night",
                "3": 28,
                "4": 3,
                "7": 25,
                "101": True,
                "102": "charge",
                "104": 5,
                "106": 100,
                "108": 2881,
                "109": True,
            }
        )
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
        """Light is DP109; DP102 is the battery charge status, not the light.

        The upstream PS-010 Fountain maps DP102 to the light, so this guards
        against reintroducing that collision for the OilClear.
        """
        state = OilClearState.from_dps({"102": "charge", "109": False})
        assert state.light is False
        assert state.battery_charge_status == "charge"

    def test_missing_dps_default_safely(self) -> None:
        """Absent data points fall back to defaults instead of raising."""
        state = OilClearState.from_dps({})
        assert state.switch is False
        assert state.work_mode == "normal"
        assert state.curr_weight == 0
        assert state.battery_charge_status == ""

    def test_unknown_work_mode_falls_back_to_normal(self) -> None:
        """An unexpected work_mode value degrades gracefully."""
        state = OilClearState.from_dps({"2": "bogus"})
        assert state.work_mode == "normal"


class TestOilClearCommands:
    """Validate that commands write the correct data points."""

    def _device(self) -> OilClearFountain:
        dev = OilClearFountain("id", "1.2.3.4", "key")
        dev._set_dps = AsyncMock()  # type: ignore[method-assign]
        dev._send_button = AsyncMock()  # type: ignore[method-assign]
        return dev

    @pytest.mark.asyncio
    async def test_set_light_writes_dp109(self) -> None:
        """The indicator light is DP109, not the PS-010's DP102."""
        dev = self._device()
        await dev.set_light(True)
        dev._set_dps.assert_awaited_once_with(OilClearDPS.LIGHT, True)
        assert OilClearDPS.LIGHT == 109

    @pytest.mark.asyncio
    async def test_set_heating_writes_dp101(self) -> None:
        """Heating toggles DP101."""
        dev = self._device()
        await dev.set_heating(False)
        dev._set_dps.assert_awaited_once_with(OilClearDPS.HEATING, False)

    @pytest.mark.asyncio
    async def test_reset_weight_sends_button_dp107(self) -> None:
        """Weight calibration is a momentary button on DP107."""
        dev = self._device()
        await dev.reset_weight()
        dev._send_button.assert_awaited_once_with(OilClearDPS.RESET_WEIGHT)

    @pytest.mark.asyncio
    async def test_get_state_returns_oilclear_state(self) -> None:
        """get_state parses raw DPS into an OilClearState."""
        dev = self._device()
        dev.get_raw_dps = AsyncMock(return_value={"1": True, "108": 1500})  # type: ignore[method-assign]
        state = await dev.get_state()
        assert isinstance(state, OilClearState)
        assert state.switch is True
        assert state.curr_weight == 1500
