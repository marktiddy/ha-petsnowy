"""Unit tests for PetSnowy coordinator."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

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

    def test_coordinator_creates_correct_device_type(self) -> None:
        """Coordinator instantiates the correct device class."""
        hass = MagicMock()
        entry = self._make_entry()
        mock_cls = MagicMock()

        with patch(
            "custom_components.petsnowy.coordinator._DEVICE_CLASSES",
            {DEVICE_TYPE_LITTERBOX: mock_cls},
        ):
            coordinator = PetSnowyCoordinator(hass, entry)

        mock_cls.assert_called_once_with(
            "test_device_001",
            "192.168.1.100",
            "test_key",
            version=3.4,
        )
        assert coordinator.device_type == DEVICE_TYPE_LITTERBOX

    def test_coordinator_name_includes_device_id(self) -> None:
        """Coordinator name contains the device ID for logging."""
        hass = MagicMock()
        entry = self._make_entry()

        with patch(
            "custom_components.petsnowy.coordinator._DEVICE_CLASSES",
            {DEVICE_TYPE_LITTERBOX: MagicMock()},
        ):
            coordinator = PetSnowyCoordinator(hass, entry)

        assert "test_device_001" in coordinator.name

    def test_coordinator_starts_disconnected(self) -> None:
        """Coordinator starts in disconnected state."""
        hass = MagicMock()
        entry = self._make_entry()

        with patch(
            "custom_components.petsnowy.coordinator._DEVICE_CLASSES",
            {DEVICE_TYPE_LITTERBOX: MagicMock()},
        ):
            coordinator = PetSnowyCoordinator(hass, entry)

        assert coordinator._connected is False
