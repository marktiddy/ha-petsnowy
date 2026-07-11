"""Local device driver for the OilClear AI Water Fountain (PS-120).

The OilClear is a Tuya ``cwysj`` fountain (product ``cwrqimudzkuuipcg``) that
shares data points 1-7 with the PetSnowy PS-010 fountain but adds a battery,
water heater, water-weight sensor, and temperature readout — none of which the
upstream :class:`petsnowy.Fountain` class models. It also relocates a couple of
DPs: the indicator light is DP109 here (not DP102, which is the battery charge
status).

Rather than fork the library, this subclass reuses ``Fountain``'s connection and
DPS plumbing while defining the full OilClear data-point map locally.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from petsnowy import Fountain, WorkMode  # type: ignore[attr-defined]


class OilClearDPS:
    """Tuya Data Point IDs for the OilClear AI Water Fountain (PS-120).

    Product ID: cwrqimudzkuuipcg
    Category: cwysj
    """

    SWITCH = 1
    WORK_MODE = 2  # "normal", "night"
    FILTER_DAYS = 3  # filter days remaining (read-only)
    PUMP_TIME = 4  # pump cleaning days remaining (read-only)
    FILTER_RESET = 5  # momentary button
    PUMP_RESET = 6  # momentary button
    FILTER_LIFE = 7  # filter replacement reminder period (0-30 days)
    HEATING = 101  # water heater on/off
    BATTERY_CHARGE_STATUS = 102  # enum, e.g. "charge"
    WATER_TEMP = 104  # water temperature (°C)
    BATTERY_CAPACITY = 106  # battery charge (0-100 %)
    RESET_WEIGHT = 107  # momentary button (tare/calibrate the scale)
    CURR_WEIGHT = 108  # current water weight (grams)
    LIGHT = 109  # indicator light on/off


@dataclass(frozen=True)
class OilClearState:
    """Parsed snapshot of OilClear fountain data points."""

    switch: bool
    work_mode: WorkMode
    filter_days: int
    pump_time: int
    filter_life: int
    heating: bool
    battery_charge_status: str
    water_temp: int
    battery_capacity: int
    curr_weight: int
    light: bool
    raw_dps: dict[str, Any]

    @classmethod
    def from_dps(cls, dps: dict[str, Any]) -> OilClearState:
        """Build an OilClearState from a raw DPS dict (string keys)."""

        def _bool(key: int, default: bool = False) -> bool:
            v = dps.get(str(key))
            return bool(v) if v is not None else default

        def _int(key: int, default: int = 0) -> int:
            v = dps.get(str(key))
            return int(v) if v is not None else default

        def _str(key: int, default: str = "") -> str:
            v = dps.get(str(key))
            return str(v) if v is not None else default

        mode_raw = dps.get(str(OilClearDPS.WORK_MODE), "normal")
        try:
            work_mode = WorkMode(mode_raw)
        except ValueError:
            work_mode = WorkMode.NORMAL

        return cls(
            switch=_bool(OilClearDPS.SWITCH),
            work_mode=work_mode,
            filter_days=_int(OilClearDPS.FILTER_DAYS),
            pump_time=_int(OilClearDPS.PUMP_TIME),
            filter_life=_int(OilClearDPS.FILTER_LIFE),
            heating=_bool(OilClearDPS.HEATING),
            battery_charge_status=_str(OilClearDPS.BATTERY_CHARGE_STATUS),
            water_temp=_int(OilClearDPS.WATER_TEMP),
            battery_capacity=_int(OilClearDPS.BATTERY_CAPACITY),
            curr_weight=_int(OilClearDPS.CURR_WEIGHT),
            light=_bool(OilClearDPS.LIGHT),
            raw_dps=dict(dps),
        )


class OilClearFountain(Fountain):
    """Async interface to an OilClear AI Water Fountain (PS-120).

    Inherits power (DP1), work-mode (DP2), filter/pump reset (DP5/DP6), and the
    filter reminder (DP7) from :class:`petsnowy.Fountain`, and adds the
    OilClear-specific heater, weight calibration, and richer state.
    """

    def __init__(
        self,
        device_id: str,
        address: str,
        local_key: str,
        version: float = 3.3,
    ) -> None:
        super().__init__(device_id, address, local_key, version=version)

    # -- State reading ---------------------------------------------------------

    async def get_state(self) -> OilClearState:  # type: ignore[override]
        """Read and parse the full OilClear fountain state."""
        dps = await self.get_raw_dps()
        return OilClearState.from_dps(dps)

    # -- Commands --------------------------------------------------------------

    async def set_light(self, enabled: bool) -> None:
        """Turn the indicator light on or off (DP109, not the DP102 of PS-010)."""
        await self._set_dps(OilClearDPS.LIGHT, enabled)

    async def set_heating(self, enabled: bool) -> None:
        """Turn the water heater on or off."""
        await self._set_dps(OilClearDPS.HEATING, enabled)

    async def reset_weight(self) -> None:
        """Tare/calibrate the built-in scale."""
        await self._send_button(OilClearDPS.RESET_WEIGHT)
