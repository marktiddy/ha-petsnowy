"""Unit tests for PetSnowy config flow."""

from __future__ import annotations

import pytest

from custom_components.petsnowy.const import (
    CONF_ADDRESS,
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_LOCAL_KEY,
    CONF_VERSION,
    DEFAULT_VERSIONS,
    DEVICE_TYPE_FEEDER,
    DEVICE_TYPE_FOUNTAIN,
    DEVICE_TYPE_LITTERBOX,
    DEVICE_TYPE_PURIFIER,
)


class TestConfigConstants:
    """Tests for config flow constants and defaults."""

    def test_all_device_types_have_default_versions(self) -> None:
        """Every device type has a default protocol version."""
        for device_type in (
            DEVICE_TYPE_LITTERBOX,
            DEVICE_TYPE_FOUNTAIN,
            DEVICE_TYPE_PURIFIER,
            DEVICE_TYPE_FEEDER,
        ):
            assert device_type in DEFAULT_VERSIONS
            assert isinstance(DEFAULT_VERSIONS[device_type], float)

    def test_litterbox_default_version(self) -> None:
        """Litterbox defaults to Tuya protocol 3.4."""
        assert DEFAULT_VERSIONS[DEVICE_TYPE_LITTERBOX] == 3.4

    def test_fountain_default_version(self) -> None:
        """Fountain defaults to Tuya protocol 3.3."""
        assert DEFAULT_VERSIONS[DEVICE_TYPE_FOUNTAIN] == 3.3

    def test_purifier_default_version(self) -> None:
        """Purifier defaults to Tuya protocol 3.4."""
        assert DEFAULT_VERSIONS[DEVICE_TYPE_PURIFIER] == 3.4

    def test_feeder_default_version(self) -> None:
        """Feeder defaults to Tuya protocol 3.3."""
        assert DEFAULT_VERSIONS[DEVICE_TYPE_FEEDER] == 3.3
