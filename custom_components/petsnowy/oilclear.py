"""Cloud device driver for the OilClear AI Water Fountain (PS-120).

Unlike the always-on PetSnowy litter box, this fountain is power-managed: it
keeps only a cloud connection alive and tears down its local Tuya listener
between syncs, so local polling (tinytuya.Device) can't hold a connection. This
driver talks to it through the Tuya Cloud API (tinytuya.Cloud) instead, which
returns the last-reported state regardless of whether the device is currently
awake on the LAN.

This device only reports through Tuya's newer *thing / device-shadow* model, so
reads use ``/v2.0/cloud/thing/{id}/shadow/properties`` and writes use
``/v2.0/cloud/thing/{id}/shadow/properties/issue`` rather than tinytuya's legacy
``iot-03/devices`` status/command helpers (which return nothing for it). Both
speak code/value pairs (``switch``, ``curr_weight`` …).
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any

import tinytuya
from petsnowy import CommandError  # type: ignore[attr-defined]
from petsnowy import ConnectionError as PetSnowyConnectionError

_LOGGER = logging.getLogger(__name__)

# Work modes reported by DP2. Note this is NOT the PS-010 fountain's
# normal/night pair — the OilClear uses normal/intelligent.
WORK_MODES: tuple[str, ...] = ("normal", "intelligent")
DEFAULT_WORK_MODE = "normal"


def _decode_water_record(raw: str) -> tuple[int, int]:
    """Decode the ``water_record`` string into (drink_count, volume_ml) for today.

    The value is an 8-char hex string of two big-endian uint16 halves, e.g.
    ``"00070005"`` -> (7, 5). It is empty when there is no record yet.

    NOTE: the volume half matches the app's "ml today"; the count half is a
    best-guess and still to be confirmed against the app — if it turns out
    reversed, swap the two return values here (the only place it's decided).
    """
    s = (raw or "").strip()
    if len(s) < 8:
        return (0, 0)
    try:
        count = int(s[0:4], 16)
        volume_ml = int(s[4:8], 16)
    except ValueError:
        return (0, 0)
    return (count, volume_ml)


class OilClearCode:
    """Tuya status/command codes for the OilClear AI Water Fountain (PS-120).

    Product ID: cwrqimudzkuuipcg
    Category: cwysj
    """

    SWITCH = "switch"
    WORK_MODE = "work_mode"  # "normal", "intelligent"
    FILTER_DAYS = "filter_days"  # filter days remaining (read-only)
    PUMP_TIME = "pump_time"  # pump cleaning days remaining (read-only)
    FILTER_RESET = "filter_reset"  # momentary button
    PUMP_RESET = "pump_reset"  # momentary button
    FILTER_LIFE = "filter_life"  # filter reminder period (0-30 days)
    HEATING = "heating"  # water heater on/off
    BATTERY_CHARGE_STATUS = "battery_charge_status"  # enum, e.g. "charge"
    WATER_TEMP = "water_temp"  # water temperature (°C)
    BATTERY_CAPACITY = "battery_capacity"  # battery charge (0-100 %)
    RESET_WEIGHT = "reset_weight"  # momentary button (tare/calibrate the scale)
    CURR_WEIGHT = "curr_weight"  # current water weight (grams)
    LIGHT = "light"  # indicator light on/off
    WATER_RECORD = "water_record"  # hex-encoded daily drink count + volume (ml)


@dataclass(frozen=True)
class OilClearState:
    """Parsed snapshot of OilClear fountain state."""

    switch: bool
    work_mode: str
    filter_days: int
    pump_time: int
    filter_life: int
    heating: bool
    battery_charge_status: str
    water_temp: int
    battery_capacity: int
    curr_weight: int
    light: bool
    drink_count_today: int
    water_consumed_ml: int
    raw: dict[str, Any]

    @classmethod
    def from_properties(cls, properties: list[dict[str, Any]]) -> OilClearState:
        """Build an OilClearState from a thing-shadow ``properties`` list.

        ``properties`` is the ``[{"code": ..., "value": ...}, ...]`` payload
        returned under ``result.properties`` by the shadow/properties endpoint.
        """
        values = {item["code"]: item["value"] for item in properties if "code" in item}
        return cls._from_code_map(values)

    @classmethod
    def _from_code_map(cls, values: dict[str, Any]) -> OilClearState:
        def _bool(code: str, default: bool = False) -> bool:
            v = values.get(code)
            return bool(v) if v is not None else default

        def _int(code: str, default: int = 0) -> int:
            v = values.get(code)
            return int(v) if v is not None else default

        def _str(code: str, default: str = "") -> str:
            v = values.get(code)
            return str(v) if v is not None else default

        drink_count, water_ml = _decode_water_record(_str(OilClearCode.WATER_RECORD))

        return cls(
            switch=_bool(OilClearCode.SWITCH),
            work_mode=_str(OilClearCode.WORK_MODE, DEFAULT_WORK_MODE),
            filter_days=_int(OilClearCode.FILTER_DAYS),
            pump_time=_int(OilClearCode.PUMP_TIME),
            filter_life=_int(OilClearCode.FILTER_LIFE),
            heating=_bool(OilClearCode.HEATING),
            battery_charge_status=_str(OilClearCode.BATTERY_CHARGE_STATUS),
            water_temp=_int(OilClearCode.WATER_TEMP),
            battery_capacity=_int(OilClearCode.BATTERY_CAPACITY),
            curr_weight=_int(OilClearCode.CURR_WEIGHT),
            light=_bool(OilClearCode.LIGHT),
            drink_count_today=drink_count,
            water_consumed_ml=water_ml,
            raw=dict(values),
        )


class OilClearCloudFountain:
    """Cloud-backed interface to an OilClear AI Water Fountain (PS-120).

    Exposes the same command/state surface as the other PetSnowy device classes
    so the coordinator and entities are unaware it polls the Tuya Cloud rather
    than the LAN.
    """

    def __init__(
        self,
        device_id: str,
        region: str,
        client_id: str,
        client_secret: str,
    ) -> None:
        self._device_id = device_id
        self._region = region
        self._client_id = client_id
        self._client_secret = client_secret
        self._cloud: tinytuya.Cloud | None = None
        self._properties_url = f"/v2.0/cloud/thing/{device_id}/shadow/properties"
        self._issue_url = f"/v2.0/cloud/thing/{device_id}/shadow/properties/issue"

    # -- Connection lifecycle --------------------------------------------------

    async def connect(self) -> None:
        """Authenticate with the Tuya Cloud and confirm the device is reachable."""
        cloud = await asyncio.to_thread(
            tinytuya.Cloud,
            apiRegion=self._region,
            apiKey=self._client_id,
            apiSecret=self._client_secret,
        )
        if not getattr(cloud, "token", None):
            err = getattr(cloud, "error", None)
            raise PetSnowyConnectionError(
                f"Tuya Cloud authentication failed: {err or 'no token returned'}"
            )
        self._cloud = cloud
        # Validate the device id / permission up front so config-flow surfaces a
        # clear error instead of a device that appears added but has no data.
        await self.get_state()
        _LOGGER.info("Connected to Tuya Cloud for OilClear %s", self._device_id)

    async def disconnect(self) -> None:
        """Drop the cached cloud client (no persistent socket to close)."""
        self._cloud = None

    def _ensure_connected(self) -> tinytuya.Cloud:
        if self._cloud is None:
            raise PetSnowyConnectionError("Not connected. Call connect() first.")
        return self._cloud

    # -- State reading ---------------------------------------------------------

    async def get_state(self) -> OilClearState:
        """Read and parse the device shadow properties from the Tuya Cloud."""
        cloud = self._ensure_connected()
        response = await asyncio.to_thread(cloud.cloudrequest, self._properties_url)
        if not response or not response.get("success"):
            msg = response.get("msg", "Unknown error") if response else "no response"
            raise PetSnowyConnectionError(f"Failed to read cloud properties: {msg}")
        properties = (response.get("result") or {}).get("properties", [])
        return OilClearState.from_properties(properties)

    # -- Internal command helper -----------------------------------------------

    async def _send(self, code: str, value: Any) -> None:
        """Issue a single code/value property via the Tuya Cloud thing model."""
        cloud = self._ensure_connected()
        body = {"properties": json.dumps({code: value})}
        response = await asyncio.to_thread(
            cloud.cloudrequest, self._issue_url, "POST", body
        )
        if not response or not response.get("success"):
            msg = response.get("msg", "Unknown error") if response else "no response"
            raise CommandError(f"Failed to send {code}={value!r}: {msg}")

    # -- Power -----------------------------------------------------------------

    async def turn_on(self) -> None:
        """Turn the fountain on."""
        await self._send(OilClearCode.SWITCH, True)

    async def turn_off(self) -> None:
        """Turn the fountain off."""
        await self._send(OilClearCode.SWITCH, False)

    # -- Commands (momentary buttons) ------------------------------------------

    async def reset_filter(self) -> None:
        """Reset the filter days counter."""
        await self._send(OilClearCode.FILTER_RESET, True)

    async def reset_pump(self) -> None:
        """Reset the pump cleaning counter."""
        await self._send(OilClearCode.PUMP_RESET, True)

    async def reset_weight(self) -> None:
        """Tare/calibrate the built-in scale."""
        await self._send(OilClearCode.RESET_WEIGHT, True)

    # -- Settings --------------------------------------------------------------

    async def set_work_mode(self, mode: str) -> None:
        """Set the fountain operating mode ('normal' or 'intelligent')."""
        if mode not in WORK_MODES:
            raise ValueError(f"work_mode must be one of {WORK_MODES}")
        await self._send(OilClearCode.WORK_MODE, mode)

    async def set_filter_reminder(self, days: int) -> None:
        """Set the filter replacement reminder period (0-30 days)."""
        if not (0 <= days <= 30):
            raise ValueError("filter_reminder must be between 0 and 30")
        await self._send(OilClearCode.FILTER_LIFE, days)

    async def set_light(self, enabled: bool) -> None:
        """Turn the indicator light on or off."""
        await self._send(OilClearCode.LIGHT, enabled)

    async def set_heating(self, enabled: bool) -> None:
        """Turn the water heater on or off."""
        await self._send(OilClearCode.HEATING, enabled)
