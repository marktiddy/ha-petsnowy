"""Unit tests for the cloud-backed OilClear fountain driver."""

from __future__ import annotations

import json
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.util import dt as dt_util

from custom_components.petsnowy.const import CONF_DEVICE_ID
from custom_components.petsnowy.coordinator import PetSnowyCoordinator
from custom_components.petsnowy.oilclear import (
    OilClearCloudFountain,
    OilClearCode,
    OilClearState,
    _decode_water_record,
)
from custom_components.petsnowy.switch import OILCLEAR_SWITCHES, PetSnowySwitch

FULL_PROPERTIES = [
    {"code": "switch", "value": True},
    {"code": "work_mode", "value": "intelligent"},
    {"code": "filter_days", "value": 28},
    {"code": "pump_time", "value": 3},
    {"code": "filter_life", "value": 25},
    {"code": "heating", "value": True},
    {"code": "battery_charge_status", "value": "charge"},
    {"code": "water_temp", "value": 5},
    {"code": "battery_capacity", "value": 100},
    {"code": "curr_weight", "value": 3036},
    {"code": "light", "value": True},
    {"code": "water_record", "value": "00070005"},
]

DEVICE_ID = "dev123"
PROPERTIES_URL = f"/v2.0/cloud/thing/{DEVICE_ID}/shadow/properties"
ISSUE_URL = f"/v2.0/cloud/thing/{DEVICE_ID}/shadow/properties/issue"


class TestOilClearState:
    """Validate thing-shadow property parsing for the OilClear (PS-120)."""

    def test_parses_full_properties(self) -> None:
        """A full shadow-properties payload maps to the expected fields."""
        state = OilClearState.from_properties(FULL_PROPERTIES)
        assert state.switch is True
        assert state.work_mode == "intelligent"
        assert state.filter_days == 28
        assert state.pump_time == 3
        assert state.filter_life == 25
        assert state.heating is True
        assert state.battery_charge_status == "charge"
        assert state.water_temp == 5
        assert state.battery_capacity == 100
        assert state.curr_weight == 3036
        assert state.light is True

    def test_light_and_charge_status_do_not_collide(self) -> None:
        """Light and battery charge status are distinct codes."""
        state = OilClearState.from_properties(
            [
                {"code": "battery_charge_status", "value": "charge"},
                {"code": "light", "value": False},
            ]
        )
        assert state.light is False
        assert state.battery_charge_status == "charge"

    def test_missing_codes_default_safely(self) -> None:
        """Absent codes fall back to defaults instead of raising."""
        state = OilClearState.from_properties([])
        assert state.switch is False
        assert state.work_mode == "normal"
        assert state.curr_weight == 0
        assert state.battery_charge_status == ""
        assert state.drink_count_today == 0
        assert state.water_consumed_ml == 0

    def test_decodes_drinking_data(self) -> None:
        """water_record decodes into today's drink count and volume."""
        state = OilClearState.from_properties(FULL_PROPERTIES)
        assert state.drink_count_today == 7
        assert state.water_consumed_ml == 5


class TestWaterRecordDecode:
    """Validate the water_record hex decoder."""

    def test_two_uint16_halves(self) -> None:
        """An 8-char hex string splits into two big-endian uint16 halves."""
        assert _decode_water_record("0005000C") == (5, 12)
        assert _decode_water_record("00070005") == (7, 5)

    def test_empty_is_zero(self) -> None:
        """An empty or short record decodes to zeros."""
        assert _decode_water_record("") == (0, 0)
        assert _decode_water_record("00") == (0, 0)

    def test_invalid_hex_is_zero(self) -> None:
        """Non-hex content decodes to zeros rather than raising."""
        assert _decode_water_record("zzzzzzzz") == (0, 0)


class TestVolumeConversion:
    """Validate the ml/oz conversion used by the water-consumed sensor."""

    def test_ml_passthrough(self) -> None:
        """Millilitres are returned unchanged."""
        from custom_components.petsnowy.const import VOLUME_UNIT_ML
        from custom_components.petsnowy.sensor import _volume_unit, _volume_value

        assert _volume_value(100, VOLUME_UNIT_ML) == 100
        assert _volume_unit(VOLUME_UNIT_ML) == "mL"

    def test_oz_conversion(self) -> None:
        """Millilitres convert to fluid ounces, rounded to 2 dp."""
        from custom_components.petsnowy.const import VOLUME_UNIT_OZ
        from custom_components.petsnowy.sensor import _volume_unit, _volume_value

        assert _volume_value(100, VOLUME_UNIT_OZ) == 3.38
        assert _volume_unit(VOLUME_UNIT_OZ) == "fl. oz."


class TestOilClearCommands:
    """Validate that commands issue the correct thing-model properties."""

    def _device(self) -> OilClearCloudFountain:
        dev = OilClearCloudFountain(DEVICE_ID, "eu", "id", "secret")
        dev._cloud = MagicMock()
        dev._cloud.cloudrequest = MagicMock(
            return_value={"success": True, "result": {"properties": FULL_PROPERTIES}}
        )
        return dev

    @pytest.mark.asyncio
    async def test_turn_on_issues_switch(self) -> None:
        """Power on issues the switch property to the issue endpoint."""
        dev = self._device()
        await dev.turn_on()
        dev._cloud.cloudrequest.assert_called_once_with(
            ISSUE_URL, "POST", {"properties": json.dumps({"switch": True})}
        )

    @pytest.mark.asyncio
    async def test_set_light_uses_light_code(self) -> None:
        """The indicator light is its own code, not the charge status."""
        dev = self._device()
        await dev.set_light(True)
        dev._cloud.cloudrequest.assert_called_once_with(
            ISSUE_URL,
            "POST",
            {"properties": json.dumps({OilClearCode.LIGHT: True})},
        )

    @pytest.mark.asyncio
    async def test_set_heating_issues_heating(self) -> None:
        """Heating toggles the heating property."""
        dev = self._device()
        await dev.set_heating(False)
        dev._cloud.cloudrequest.assert_called_once_with(
            ISSUE_URL, "POST", {"properties": json.dumps({"heating": False})}
        )

    @pytest.mark.asyncio
    async def test_reset_weight_issues_button(self) -> None:
        """Weight calibration issues the reset_weight property."""
        dev = self._device()
        await dev.reset_weight()
        dev._cloud.cloudrequest.assert_called_once_with(
            ISSUE_URL, "POST", {"properties": json.dumps({"reset_weight": True})}
        )

    @pytest.mark.asyncio
    async def test_set_work_mode_accepts_intelligent(self) -> None:
        """Intelligent is a valid work mode for this device."""
        dev = self._device()
        await dev.set_work_mode("intelligent")
        dev._cloud.cloudrequest.assert_called_once_with(
            ISSUE_URL, "POST", {"properties": json.dumps({"work_mode": "intelligent"})}
        )

    @pytest.mark.asyncio
    async def test_set_work_mode_rejects_night(self) -> None:
        """The PS-010's 'night' mode is not valid on the OilClear."""
        dev = self._device()
        with pytest.raises(ValueError):
            await dev.set_work_mode("night")

    @pytest.mark.asyncio
    async def test_filter_reminder_out_of_range_raises(self) -> None:
        """Filter reminder is clamped to the device's 0-30 range."""
        dev = self._device()
        with pytest.raises(ValueError):
            await dev.set_filter_reminder(60)

    @pytest.mark.asyncio
    async def test_get_state_parses_shadow_properties(self) -> None:
        """get_state reads the shadow properties endpoint and parses them."""
        dev = self._device()
        state = await dev.get_state()
        dev._cloud.cloudrequest.assert_called_once_with(PROPERTIES_URL)
        assert isinstance(state, OilClearState)
        assert state.curr_weight == 3036
        assert state.work_mode == "intelligent"

    @pytest.mark.asyncio
    async def test_get_state_raises_on_failure(self) -> None:
        """A failed cloud read surfaces as an error."""
        from petsnowy import ConnectionError as PetSnowyConnectionError

        dev = self._device()
        dev._cloud.cloudrequest = MagicMock(
            return_value={"success": False, "msg": "device offline"}
        )
        with pytest.raises(PetSnowyConnectionError):
            await dev.get_state()

    @pytest.mark.asyncio
    async def test_command_failure_raises(self) -> None:
        """A rejected command surfaces as a CommandError."""
        from petsnowy import CommandError

        dev = self._device()
        dev._cloud.cloudrequest = MagicMock(
            return_value={"success": False, "msg": "nope"}
        )
        with pytest.raises(CommandError):
            await dev.turn_on()


class TestOilClearOptimisticSwitch:
    """The OilClear heating switch holds the requested state instead of snapping back.

    The device queues commands and only reports them once awake, so an
    immediate poll would read the stale value; the switch instead updates the
    coordinator optimistically (while still rendering as a normal toggle).
    """

    def _coordinator(self, state: OilClearState) -> MagicMock:
        coordinator = MagicMock()
        coordinator.data = state
        coordinator.device = MagicMock()
        coordinator.device.set_heating = AsyncMock()
        coordinator.async_request_refresh = AsyncMock()
        coordinator.async_set_pending = MagicMock()
        coordinator.config_entry.data = {CONF_DEVICE_ID: "dev123"}
        return coordinator

    def _heating_switch(self, coordinator: MagicMock) -> PetSnowySwitch:
        desc = next(d for d in OILCLEAR_SWITCHES if d.key == "heating")
        return PetSnowySwitch(coordinator, desc)

    @pytest.mark.asyncio
    async def test_turn_off_holds_pending_and_skips_poll(self) -> None:
        """Toggling heating registers a pending value instead of re-polling."""
        state = OilClearState.from_properties([{"code": "heating", "value": True}])
        coordinator = self._coordinator(state)
        switch = self._heating_switch(coordinator)

        await switch.async_turn_off()

        coordinator.device.set_heating.assert_awaited_once_with(False)
        coordinator.async_request_refresh.assert_not_called()
        coordinator.async_set_pending.assert_called_once_with("heating", False)
        # Renders as a normal toggle, not an assumed-state pair of buttons.
        assert switch.assumed_state is False


class TestPendingOverlay:
    """The coordinator holds a requested value until the device confirms it."""

    def _coordinator(self) -> PetSnowyCoordinator:
        # Build a bare coordinator without running __init__ (which needs hass);
        # only the overlay state is required for these tests.
        coordinator = object.__new__(PetSnowyCoordinator)
        coordinator._pending_overlay = {}
        return coordinator

    def _state(self, heating: bool) -> OilClearState:
        return OilClearState.from_properties([{"code": "heating", "value": heating}])

    def test_holds_requested_value_until_confirmed(self) -> None:
        """While the device still reports the old value, the request is held."""
        coordinator = self._coordinator()
        future = dt_util.utcnow() + timedelta(minutes=5)
        coordinator._pending_overlay = {"heating": (False, future)}

        result = coordinator._apply_pending_overlay(self._state(heating=True))

        assert result.heating is False  # requested value held
        assert "heating" in coordinator._pending_overlay  # still waiting

    def test_clears_pending_once_device_confirms(self) -> None:
        """When the device reports the requested value, the pending entry clears."""
        coordinator = self._coordinator()
        future = dt_util.utcnow() + timedelta(minutes=5)
        coordinator._pending_overlay = {"heating": (False, future)}

        result = coordinator._apply_pending_overlay(self._state(heating=False))

        assert result.heating is False
        assert "heating" not in coordinator._pending_overlay  # confirmed

    def test_gives_up_after_timeout(self) -> None:
        """After the timeout, the device's actual value wins again."""
        coordinator = self._coordinator()
        past = dt_util.utcnow() - timedelta(seconds=1)
        coordinator._pending_overlay = {"heating": (False, past)}

        result = coordinator._apply_pending_overlay(self._state(heating=True))

        assert result.heating is True  # reverted to device truth
        assert "heating" not in coordinator._pending_overlay  # gave up
