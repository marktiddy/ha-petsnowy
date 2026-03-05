"""Unit tests for PetSnowy coordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.petsnowy.const import (
    CONF_ADDRESS,
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_LOCAL_KEY,
    CONF_VERSION,
    DEVICE_TYPE_LITTERBOX,
    DOMAIN,
)
from custom_components.petsnowy.coordinator import PetSnowyCoordinator


class TestPetSnowyCoordinator:
    """Tests for PetSnowyCoordinator."""

    def _make_entry(self) -> MagicMock:
        """Create a mock config entry."""
        entry = MagicMock()
        entry.data = {
            CONF_DEVICE_TYPE: DEVICE_TYPE_LITTERBOX,
            CONF_DEVICE_ID: "test_device_001",
            CONF_ADDRESS: "192.168.1.100",
            CONF_LOCAL_KEY: "test_key",
            CONF_VERSION: 3.4,
        }
        return entry

    @patch(
        "custom_components.petsnowy.coordinator.PetSnowy",
        autospec=True,
    )
    def test_coordinator_creates_correct_device_type(self, mock_cls: MagicMock) -> None:
        """Coordinator instantiates the correct device class."""
        hass = MagicMock()
        entry = self._make_entry()

        coordinator = PetSnowyCoordinator(hass, entry)

        mock_cls.assert_called_once_with(
            "test_device_001",
            "192.168.1.100",
            "test_key",
            version=3.4,
        )
        assert coordinator.device_type == DEVICE_TYPE_LITTERBOX

    @patch(
        "custom_components.petsnowy.coordinator.PetSnowy",
        autospec=True,
    )
    def test_coordinator_name_includes_device_id(self, mock_cls: MagicMock) -> None:
        """Coordinator name contains the device ID for logging."""
        hass = MagicMock()
        entry = self._make_entry()

        coordinator = PetSnowyCoordinator(hass, entry)

        assert "test_device_001" in coordinator.name

    @patch(
        "custom_components.petsnowy.coordinator.PetSnowy",
        autospec=True,
    )
    def test_coordinator_starts_disconnected(self, mock_cls: MagicMock) -> None:
        """Coordinator starts in disconnected state."""
        hass = MagicMock()
        entry = self._make_entry()

        coordinator = PetSnowyCoordinator(hass, entry)

        assert coordinator._connected is False
