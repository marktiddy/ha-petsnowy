"""Sensor platform for PetSnowy integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfMass, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from petsnowy import Notification  # type: ignore[attr-defined]

from . import PetSnowyConfigEntry
from .const import (
    DEVICE_TYPE_FEEDER,
    DEVICE_TYPE_FOUNTAIN,
    DEVICE_TYPE_LITTERBOX,
    DEVICE_TYPE_PURIFIER,
)
from .coordinator import PetSnowyCoordinator
from .entity import PetSnowyEntity


@dataclass(frozen=True, kw_only=True)
class PetSnowySensorDescription(SensorEntityDescription):
    """Describe a PetSnowy sensor entity."""

    value_fn: str | Callable[..., Any]
    restore_coordinator_attr: str | None = None
    restore_parser: Callable[[str], Any] | None = None


LITTERBOX_SENSORS: tuple[PetSnowySensorDescription, ...] = (
    PetSnowySensorDescription(
        key="cat_weight",
        translation_key="cat_weight",
        native_unit_of_measurement=UnitOfMass.GRAMS,
        device_class=SensorDeviceClass.WEIGHT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn="cat_weight",
    ),
    PetSnowySensorDescription(
        key="calibrated_weight",
        translation_key="calibrated_weight",
        native_unit_of_measurement=UnitOfMass.GRAMS,
        suggested_unit_of_measurement=UnitOfMass.GRAMS,
        device_class=SensorDeviceClass.WEIGHT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s, c: s.cat_weight + c.weight_offset,
    ),
    PetSnowySensorDescription(
        key="actual_excretions",
        translation_key="actual_excretions",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:counter",
        value_fn=lambda s, c: (
            c.actual_excretions_today
            if c.external_motion_sensor is not None
            else s.excretion_count_today
        ),
    ),
    PetSnowySensorDescription(
        key="excretion_count_today",
        translation_key="excretion_count_today",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:counter",
        value_fn="excretion_count_today",
    ),
    PetSnowySensorDescription(
        key="excretion_duration_today",
        translation_key="excretion_duration_today",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn="excretion_duration_today",
    ),
    PetSnowySensorDescription(
        key="filter_days_remaining",
        translation_key="filter_days_remaining",
        native_unit_of_measurement=UnitOfTime.DAYS,
        icon="mdi:air-filter",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn="filter_days_remaining",
    ),
    PetSnowySensorDescription(
        key="status",
        translation_key="litterbox_status",
        icon="mdi:state-machine",
        device_class=SensorDeviceClass.ENUM,
        options=[
            "standby",
            "cleaning",
            "deodorization",
            "sleep",
            "pet_into",
            "wait_clean",
        ],
        value_fn="status",
    ),
    PetSnowySensorDescription(
        key="last_notification",
        translation_key="last_notification",
        icon="mdi:bell",
        value_fn=lambda s, _c: ", ".join(
            n.name.replace("_", " ").title()
            for n in Notification
            if n and n in s.notifications
        )
        or "None",
    ),
    PetSnowySensorDescription(
        key="litter_age",
        translation_key="litter_age",
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda _s, c: c.last_empty_ts,
        restore_coordinator_attr="last_empty_ts",
        restore_parser=datetime.fromisoformat,
    ),
    PetSnowySensorDescription(
        key="last_use",
        translation_key="last_use",
        icon="mdi:cat",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda _s, c: c.last_use_ts,
        restore_coordinator_attr="last_use_ts",
        restore_parser=datetime.fromisoformat,
    ),
    PetSnowySensorDescription(
        key="actual_last_use",
        translation_key="actual_last_use",
        icon="mdi:cat",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda _s, c: (
            c.actual_last_use_ts
            if c.external_motion_sensor is not None
            else c.last_use_ts
        ),
        restore_coordinator_attr="actual_last_use_ts",
        restore_parser=datetime.fromisoformat,
    ),
    PetSnowySensorDescription(
        key="use_rate",
        translation_key="use_rate",
        icon="mdi:chart-line",
        native_unit_of_measurement="/h",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda _s, c: round(len(c.use_event_ts) / 24, 2),
    ),
    PetSnowySensorDescription(
        key="actual_use_rate",
        translation_key="actual_use_rate",
        icon="mdi:chart-line",
        native_unit_of_measurement="/h",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda _s, c: round(
            len(
                c.actual_use_event_ts
                if c.external_motion_sensor is not None
                else c.use_event_ts
            )
            / 24,
            2,
        ),
    ),
    PetSnowySensorDescription(
        key="weight_trend",
        translation_key="weight_trend",
        icon="mdi:trending-up",
        native_unit_of_measurement=UnitOfMass.GRAMS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda _s, c: (
            round(
                c.weight_samples[-1][1]
                - sum(w for _, w in c.weight_samples) / len(c.weight_samples)
            )
            if len(c.weight_samples) >= 2
            else None
        ),
    ),
    PetSnowySensorDescription(
        key="actual_weight_trend",
        translation_key="actual_weight_trend",
        icon="mdi:trending-up",
        native_unit_of_measurement=UnitOfMass.GRAMS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda _s, c: (
            (
                lambda samples: (
                    round(samples[-1][1] - sum(w for _, w in samples) / len(samples))
                    if len(samples) >= 2
                    else None
                )
            )(
                c.actual_weight_samples
                if c.external_motion_sensor is not None
                else c.weight_samples
            )
        ),
    ),
    PetSnowySensorDescription(
        key="last_filter_reset",
        translation_key="last_filter_reset",
        icon="mdi:air-filter",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda _s, c: c.last_filter_reset_ts,
        restore_coordinator_attr="last_filter_reset_ts",
        restore_parser=datetime.fromisoformat,
    ),
    PetSnowySensorDescription(
        key="last_clear",
        translation_key="last_clear",
        icon="mdi:broom",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda _s, c: c.last_clear_ts,
        restore_coordinator_attr="last_clear_ts",
        restore_parser=datetime.fromisoformat,
    ),
    PetSnowySensorDescription(
        key="last_litter_bag_change",
        translation_key="last_litter_bag_change",
        icon="mdi:delete-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda _s, c: c.last_litter_bag_change_ts,
        restore_coordinator_attr="last_litter_bag_change_ts",
        restore_parser=datetime.fromisoformat,
    ),
    PetSnowySensorDescription(
        key="short_stay_count",
        translation_key="short_stay_count",
        icon="mdi:timer-sand",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda _s, c: c.short_stay_count,
        restore_coordinator_attr="short_stay_count",
        restore_parser=int,
    ),
    PetSnowySensorDescription(
        key="actual_short_stay_count",
        translation_key="actual_short_stay_count",
        icon="mdi:timer-sand",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda _s, c: (
            c.actual_short_stay_count
            if c.external_motion_sensor is not None
            else c.short_stay_count
        ),
        restore_coordinator_attr="actual_short_stay_count",
        restore_parser=int,
    ),
    PetSnowySensorDescription(
        key="last_excretion_duration",
        translation_key="last_excretion_duration",
        icon="mdi:timer",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda _s, c: c.last_excretion_duration,
        restore_coordinator_attr="last_excretion_duration",
        restore_parser=int,
    ),
    PetSnowySensorDescription(
        key="actual_last_excretion_duration",
        translation_key="actual_last_excretion_duration",
        icon="mdi:timer",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda _s, c: (
            c.actual_last_excretion_duration
            if c.external_motion_sensor is not None
            else c.last_excretion_duration
        ),
        restore_coordinator_attr="actual_last_excretion_duration",
        restore_parser=int,
    ),
)

FOUNTAIN_SENSORS: tuple[PetSnowySensorDescription, ...] = (
    PetSnowySensorDescription(
        key="filter_days",
        translation_key="filter_days",
        native_unit_of_measurement=UnitOfTime.DAYS,
        icon="mdi:air-filter",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn="filter_days",
    ),
    PetSnowySensorDescription(
        key="pump_time",
        translation_key="pump_time",
        native_unit_of_measurement=UnitOfTime.DAYS,
        icon="mdi:pump",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn="pump_time",
    ),
)

PURIFIER_SENSORS: tuple[PetSnowySensorDescription, ...] = (
    PetSnowySensorDescription(
        key="tvoc",
        translation_key="tvoc",
        native_unit_of_measurement="µg/m³",
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn="tvoc",
    ),
    PetSnowySensorDescription(
        key="purifier_filter_days",
        translation_key="filter_days",
        native_unit_of_measurement=UnitOfTime.DAYS,
        icon="mdi:air-filter",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn="filter_days",
    ),
    PetSnowySensorDescription(
        key="countdown_left",
        translation_key="countdown_left",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn="countdown_left",
    ),
)

FEEDER_SENSORS: tuple[PetSnowySensorDescription, ...] = (
    PetSnowySensorDescription(
        key="food_status",
        translation_key="food_status",
        icon="mdi:food-drumstick",
        device_class=SensorDeviceClass.ENUM,
        options=["enough", "insufficient"],
        value_fn="food_status",
    ),
)

_SENSORS_BY_TYPE: dict[str, tuple[PetSnowySensorDescription, ...]] = {
    DEVICE_TYPE_LITTERBOX: LITTERBOX_SENSORS,
    DEVICE_TYPE_FOUNTAIN: FOUNTAIN_SENSORS,
    DEVICE_TYPE_PURIFIER: PURIFIER_SENSORS,
    DEVICE_TYPE_FEEDER: FEEDER_SENSORS,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PetSnowyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PetSnowy sensor entities."""
    coordinator = entry.runtime_data
    descriptions = _SENSORS_BY_TYPE.get(coordinator.device_type, ())
    async_add_entities(PetSnowySensor(coordinator, desc) for desc in descriptions)


class PetSnowySensor(PetSnowyEntity, RestoreEntity, SensorEntity):
    """Representation of a PetSnowy sensor."""

    entity_description: PetSnowySensorDescription

    def __init__(
        self,
        coordinator: PetSnowyCoordinator,
        description: PetSnowySensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_added_to_hass(self) -> None:
        """Restore persisted coordinator state from the last known sensor value."""
        await super().async_added_to_hass()
        desc = self.entity_description
        if desc.restore_coordinator_attr is None:
            return
        last_state = await self.async_get_last_state()
        if last_state is None or last_state.state in (None, "unknown", "unavailable"):
            return
        parser = desc.restore_parser or (lambda s: s)
        try:
            restored = parser(last_state.state)
        except (ValueError, TypeError):
            return
        if restored is not None:
            setattr(self.coordinator, desc.restore_coordinator_attr, restored)

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        state = self.coordinator.data
        if state is None:
            return None
        value_fn = self.entity_description.value_fn
        if callable(value_fn):
            value = value_fn(state, self.coordinator)
        else:
            value = getattr(state, value_fn, None)
        # StrEnum values need to be plain strings for HA enum sensors
        if isinstance(value, str):
            return str(value)
        return value
