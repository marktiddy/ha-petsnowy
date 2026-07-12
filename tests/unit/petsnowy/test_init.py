"""Unit tests for integration setup helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from custom_components.petsnowy import _ORPHANED_ENTITIES, _cleanup_orphaned_entities
from custom_components.petsnowy.const import (
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    DEVICE_TYPE_FOUNTAIN,
    DEVICE_TYPE_OILCLEAR,
)


def _entry(device_type: str) -> MagicMock:
    entry = MagicMock()
    entry.data = {CONF_DEVICE_TYPE: device_type, CONF_DEVICE_ID: "dev123"}
    return entry


def test_removes_oilclear_orphans() -> None:
    """Every stale OilClear entity found in the registry is removed."""
    registry = MagicMock()
    registry.async_get_entity_id.side_effect = (
        lambda platform, domain, uid: f"{platform}.{uid}"
    )
    with patch("custom_components.petsnowy.er.async_get", return_value=registry):
        _cleanup_orphaned_entities(MagicMock(), _entry(DEVICE_TYPE_OILCLEAR))

    assert registry.async_remove.call_count == len(
        _ORPHANED_ENTITIES[DEVICE_TYPE_OILCLEAR]
    )


def test_noop_for_device_without_orphans() -> None:
    """A device type with no orphan list never touches the registry."""
    with patch("custom_components.petsnowy.er.async_get") as async_get:
        _cleanup_orphaned_entities(MagicMock(), _entry(DEVICE_TYPE_FOUNTAIN))
    async_get.assert_not_called()
