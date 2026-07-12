"""Data update coordinator for PetSnowy devices."""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import Callable, Mapping
from datetime import date, datetime, timedelta, timezone
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from petsnowy import (  # type: ignore[attr-defined]
    Fault,
    Feeder,
    Fountain,
    Notification,
    PetSnowy,
    Purifier,
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
    CONF_VOLUME_UNIT,
    CONF_WEIGHT_OFFSET,
    DEFAULT_PIR_GRACE_MINUTES,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VOLUME_UNIT,
    DEVICE_TYPE_FEEDER,
    DEVICE_TYPE_FOUNTAIN,
    DEVICE_TYPE_LITTERBOX,
    DEVICE_TYPE_OILCLEAR,
    DEVICE_TYPE_PURIFIER,
    DOMAIN,
)
from .oilclear import OilClearCloudFountain

_LOGGER = logging.getLogger(__name__)

# Local-polling device classes, keyed by device type. The OilClear is handled
# separately in build_device() because it polls the Tuya Cloud instead.
_DEVICE_CLASSES: dict[str, type] = {
    DEVICE_TYPE_LITTERBOX: PetSnowy,
    DEVICE_TYPE_FOUNTAIN: Fountain,
    DEVICE_TYPE_PURIFIER: Purifier,
    DEVICE_TYPE_FEEDER: Feeder,
}

PetSnowyDevice = PetSnowy | Fountain | Purifier | Feeder | OilClearCloudFountain


def build_device(device_type: str, data: Mapping[str, Any]) -> PetSnowyDevice:
    """Construct the driver for a config entry's device.

    The OilClear (PS-120) is power-managed and drops its local Tuya listener
    between cloud syncs, so it uses a cloud-polling driver with Tuya IoT
    credentials rather than the LAN address / local key the other devices use.
    """
    device_id = data[CONF_DEVICE_ID]
    if device_type == DEVICE_TYPE_OILCLEAR:
        return OilClearCloudFountain(
            device_id,
            data[CONF_REGION],
            data[CONF_CLIENT_ID],
            data[CONF_CLIENT_SECRET],
        )
    cls = _DEVICE_CLASSES[device_type]
    return cls(  # type: ignore[no-any-return]
        device_id,
        data[CONF_ADDRESS],
        data[CONF_LOCAL_KEY],
        version=data[CONF_VERSION],
    )


class PetSnowyCoordinator(DataUpdateCoordinator[Any]):
    """Coordinator that polls a PetSnowy device for state updates."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.device_type: str = entry.data[CONF_DEVICE_TYPE]

        self.device: PetSnowyDevice = build_device(self.device_type, entry.data)
        self._connected = False

        # === User-configurable options ===
        self.weight_offset: int = int(entry.options.get(CONF_WEIGHT_OFFSET, 0) or 0)
        self.external_motion_sensor: str | None = (
            entry.options.get(CONF_EXTERNAL_MOTION_SENSOR) or None
        )
        self.pir_grace: timedelta = timedelta(
            minutes=int(
                entry.options.get(CONF_PIR_GRACE_MINUTES, DEFAULT_PIR_GRACE_MINUTES)
            )
        )
        self.volume_unit: str = entry.options.get(CONF_VOLUME_UNIT, DEFAULT_VOLUME_UNIT)

        # PIR gate: all cat-behavior meta updates require a PIR-confirmed window.
        # The actual_excretions counter is incremented only for PIR-validated events.
        self.actual_excretions_today: int = 0
        self._pir_last_state: str | None = None
        self._pir_last_active_end: datetime | None = None
        self._pir_date: date | None = None
        self._pir_unsub: Callable[[], None] | None = None

        # === Litterbox meta state (persisted via sensor RestoreEntity) ===
        self.last_empty_ts: datetime | None = None
        self.last_use_ts: datetime | None = None
        self.last_filter_reset_ts: datetime | None = None
        self.last_clear_ts: datetime | None = None
        self.last_litter_bag_change_ts: datetime | None = None
        self.last_excretion_duration: int = 0
        self.short_stay_count: int = 0

        # PIR-validated parallels: same semantics but only advance on events
        # that coincide with a confirmed cat-inside window.
        self.actual_last_use_ts: datetime | None = None
        self.actual_last_excretion_duration: int = 0
        self.actual_short_stay_count: int = 0

        # Rolling windows (not persisted; rebuild after restart)
        self.use_event_ts: deque[datetime] = deque()
        self.weight_samples: deque[tuple[datetime, int]] = deque()
        self.actual_use_event_ts: deque[datetime] = deque()
        self.actual_weight_samples: deque[tuple[datetime, int]] = deque()

        # Previous-poll state for edge detection (not persisted)
        self._initialized: bool = False
        self._prev_notifications: Notification = Notification.NONE
        self._prev_excretion_count: int = 0
        self._prev_excretion_duration: int = 0
        self._prev_filter_days: int = 0
        self._top_cover_removed_since: datetime | None = None
        self._drawer_open_since: datetime | None = None

        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{entry.data[CONF_DEVICE_ID]}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

        if (
            self.device_type == DEVICE_TYPE_LITTERBOX
            and self.external_motion_sensor is not None
        ):
            initial = hass.states.get(self.external_motion_sensor)
            if initial is not None and initial.state not in ("unknown", "unavailable"):
                self._pir_last_state = initial.state
            self._pir_unsub = async_track_state_change_event(
                hass,
                [self.external_motion_sensor],
                self._handle_pir_state_change,
            )

    @callback  # type: ignore[untyped-decorator]
    def _handle_pir_state_change(self, event: Event) -> None:
        """Track PIR transitions so device events can be gated on confirmed presence."""
        new_state = event.data.get("new_state")
        if new_state is None or new_state.state in ("unknown", "unavailable"):
            return
        prev = self._pir_last_state
        curr = new_state.state
        self._pir_last_state = curr
        if prev == "on" and curr == "off":
            self._pir_last_active_end = dt_util.utcnow()

    def _is_pir_valid(self, now: datetime) -> bool:
        """True when a device event at `now` coincides with the PIR presence window.

        Falls back to True (accept-all) when no PIR is configured or the sensor
        is missing / unavailable — that matches the documented fallback rule.
        """
        if self.external_motion_sensor is None:
            return True
        pir_state = self.hass.states.get(self.external_motion_sensor)
        if pir_state is None or pir_state.state in ("unknown", "unavailable"):
            return True
        if self._pir_last_state == "on":
            return True
        if self._pir_last_active_end is not None:
            return (now - self._pir_last_active_end) <= self.pir_grace
        return False

    def _roll_pir_day_if_needed(self) -> None:
        """Reset daily counters (actual_excretions_today) at local midnight."""
        today = dt_util.now().date()
        if self._pir_date is None:
            self._pir_date = today
        elif self._pir_date != today:
            self.actual_excretions_today = 0
            self._pir_date = today

    async def _async_update_data(self) -> Any:
        """Fetch state from the device."""
        try:
            if not self._connected:
                await self.device.connect()
                self._connected = True
            state = await self.device.get_state()
        except Exception as err:
            self._connected = False
            try:
                await self.device.disconnect()
            except Exception:  # noqa: BLE001
                pass
            raise UpdateFailed(f"Error communicating with device: {err}") from err

        if self.device_type == DEVICE_TYPE_LITTERBOX:
            self._process_litterbox_meta(state)

        return state

    def _process_litterbox_meta(self, state: Any) -> None:
        """Derive meta sensors (last use, rates, trends, etc.) from a fresh state."""
        now = datetime.now(timezone.utc)
        self._roll_pir_day_if_needed()

        if not self._initialized:
            self._seed_first_poll_baselines(state, now)
            return

        self._detect_empty_litter_event(state, now)
        self._process_new_uses(state, now)
        self._prune_rolling_windows(now)
        self._detect_filter_reset(state, now)
        self._detect_cover_removal(state, now)
        self._detect_drawer_open(state, now)

    def _seed_first_poll_baselines(self, state: Any, now: datetime) -> None:
        """Seed edge-detection baselines on the first successful poll."""
        self._prev_notifications = state.notifications
        self._prev_excretion_count = state.excretion_count_today
        self._prev_excretion_duration = state.excretion_duration_today
        self._prev_filter_days = state.filter_days_remaining
        if Fault.TOP_COVER in state.faults:
            self._top_cover_removed_since = now
        if Fault.DRAWER in state.faults:
            self._drawer_open_since = now
        self._initialized = True

    def _detect_empty_litter_event(self, state: Any, now: datetime) -> None:
        """Edge-detect EMPTY_LITTER_DONE in the notification bitmask."""
        if (
            Notification.EMPTY_LITTER_DONE in state.notifications
            and Notification.EMPTY_LITTER_DONE not in self._prev_notifications
        ):
            self.last_empty_ts = now
        self._prev_notifications = state.notifications

    def _process_new_uses(self, state: Any, now: datetime) -> None:
        """Detect new excretion events and update raw + PIR-validated meta state."""
        if state.excretion_count_today < self._prev_excretion_count:
            # Midnight reset on the device — treat whatever is currently showing
            # as net-new uses rather than losing the events.
            self._prev_excretion_count = 0
            self._prev_excretion_duration = 0
        new_uses = state.excretion_count_today - self._prev_excretion_count
        if new_uses > 0:
            delta_dur = state.excretion_duration_today - self._prev_excretion_duration
            per_use = delta_dur // new_uses if delta_dur > 0 else 0
            self._record_raw_use(state, now, new_uses, per_use)
            if self._is_pir_valid(now):
                self._record_actual_use(state, now, new_uses, per_use)
            else:
                _LOGGER.debug(
                    "Ignoring %d device excretion event(s) for PIR-validated "
                    "meta sensors (no confirmed PIR window)",
                    new_uses,
                )
        self._prev_excretion_count = state.excretion_count_today
        self._prev_excretion_duration = state.excretion_duration_today

    def _record_raw_use(
        self, state: Any, now: datetime, new_uses: int, per_use: int
    ) -> None:
        """Update device-driven meta sensors for a fresh use event."""
        self.last_use_ts = now
        for _ in range(new_uses):
            self.use_event_ts.append(now)
        if per_use > 0:
            self.last_excretion_duration = per_use
            if per_use < 30:
                self.short_stay_count += new_uses
        if state.cat_weight > 0:
            self.weight_samples.append((now, state.cat_weight))

    def _record_actual_use(
        self, state: Any, now: datetime, new_uses: int, per_use: int
    ) -> None:
        """Update PIR-validated parallel meta sensors for a fresh use event."""
        self.actual_last_use_ts = now
        if self.external_motion_sensor is not None:
            self.actual_excretions_today += new_uses
        for _ in range(new_uses):
            self.actual_use_event_ts.append(now)
        if per_use > 0:
            self.actual_last_excretion_duration = per_use
            if per_use < 30:
                self.actual_short_stay_count += new_uses
        if state.cat_weight > 0:
            self.actual_weight_samples.append((now, state.cat_weight))
        # Consume the PIR confirmation: later events need their own fresh PIR
        # activity, so the grace window can't leak false positives shortly
        # after a real use.
        self._pir_last_active_end = None

    def _prune_rolling_windows(self, now: datetime) -> None:
        """Drop stale entries from the use-rate (24h) and weight-trend (7d) windows."""
        cutoff_24h = now - timedelta(hours=24)
        while self.use_event_ts and self.use_event_ts[0] < cutoff_24h:
            self.use_event_ts.popleft()
        while self.actual_use_event_ts and self.actual_use_event_ts[0] < cutoff_24h:
            self.actual_use_event_ts.popleft()
        cutoff_7d = now - timedelta(days=7)
        while self.weight_samples and self.weight_samples[0][0] < cutoff_7d:
            self.weight_samples.popleft()
        while (
            self.actual_weight_samples and self.actual_weight_samples[0][0] < cutoff_7d
        ):
            self.actual_weight_samples.popleft()

    def _detect_filter_reset(self, state: Any, now: datetime) -> None:
        """Detect a filter reset when filter_days_remaining increases."""
        if state.filter_days_remaining > self._prev_filter_days:
            self.last_filter_reset_ts = now
        self._prev_filter_days = state.filter_days_remaining

    def _detect_cover_removal(self, state: Any, now: datetime) -> None:
        """Record a clear event when the top cover stays removed ≥ 5 min."""
        if Fault.TOP_COVER in state.faults:
            if self._top_cover_removed_since is None:
                self._top_cover_removed_since = now
            elif (now - self._top_cover_removed_since) >= timedelta(minutes=5) and (
                self.last_clear_ts is None
                or self.last_clear_ts < self._top_cover_removed_since
            ):
                self.last_clear_ts = now
        else:
            self._top_cover_removed_since = None

    def _detect_drawer_open(self, state: Any, now: datetime) -> None:
        """Record a litter-bag change when the drawer stays open ≥ 1 min."""
        if Fault.DRAWER in state.faults:
            if self._drawer_open_since is None:
                self._drawer_open_since = now
            elif (now - self._drawer_open_since) >= timedelta(minutes=1) and (
                self.last_litter_bag_change_ts is None
                or self.last_litter_bag_change_ts < self._drawer_open_since
            ):
                self.last_litter_bag_change_ts = now
        else:
            self._drawer_open_since = None

    def mark_litter_changed(self) -> None:
        """Reset the litter-age timestamp to now (used by the manual reset button)."""
        self.last_empty_ts = datetime.now(timezone.utc)

    async def async_shutdown(self) -> None:
        """Disconnect from the device on shutdown."""
        await super().async_shutdown()
        if self._pir_unsub is not None:
            self._pir_unsub()
            self._pir_unsub = None
        if self._connected:
            await self.device.disconnect()
            self._connected = False
