"""Unit tests for PetSnowy config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.petsnowy.config_flow import PetSnowyConfigFlow
from custom_components.petsnowy.const import (
    CONF_ADDRESS,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_LOCAL_KEY,
    CONF_REGION,
    CONF_VERSION,
    DEFAULT_VERSIONS,
    DEVICE_TYPE_FEEDER,
    DEVICE_TYPE_FOUNTAIN,
    DEVICE_TYPE_LITTERBOX,
    DEVICE_TYPE_OILCLEAR,
    DEVICE_TYPE_PURIFIER,
    DOMAIN,
)


class TestConfigConstants:
    """Tests for config flow constants and defaults."""

    def test_all_device_types_have_default_versions(self) -> None:
        """Every device type has a default protocol version."""
        for device_type in (
            DEVICE_TYPE_LITTERBOX,
            DEVICE_TYPE_FOUNTAIN,
            DEVICE_TYPE_OILCLEAR,
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

    def test_oilclear_default_version(self) -> None:
        """OilClear fountain defaults to Tuya protocol 3.3."""
        assert DEFAULT_VERSIONS[DEVICE_TYPE_OILCLEAR] == 3.3

    def test_purifier_default_version(self) -> None:
        """Purifier defaults to Tuya protocol 3.4."""
        assert DEFAULT_VERSIONS[DEVICE_TYPE_PURIFIER] == 3.4

    def test_feeder_default_version(self) -> None:
        """Feeder defaults to Tuya protocol 3.3."""
        assert DEFAULT_VERSIONS[DEVICE_TYPE_FEEDER] == 3.3


class TestConfigFlowUserStep:
    """Tests for the user step (device type selection)."""

    def _make_flow(self) -> PetSnowyConfigFlow:
        """Create a config flow instance with mocked hass."""
        flow = PetSnowyConfigFlow()
        flow.hass = MagicMock()
        return flow

    @pytest.mark.asyncio
    async def test_user_step_shows_form(self) -> None:
        """User step shows device type selection form."""
        flow = self._make_flow()
        result = await flow.async_step_user()
        assert result["type"] == "form"
        assert result["step_id"] == "user"

    @pytest.mark.asyncio
    async def test_user_step_advances_to_device(self) -> None:
        """Selecting a device type advances to device step."""
        flow = self._make_flow()
        flow.async_step_device = AsyncMock(
            return_value={"type": "form", "step_id": "device"}
        )
        await flow.async_step_user({CONF_DEVICE_TYPE: DEVICE_TYPE_LITTERBOX})
        assert flow._device_type == DEVICE_TYPE_LITTERBOX
        flow.async_step_device.assert_called_once()


class TestConfigFlowDeviceStep:
    """Tests for the device step (credentials entry)."""

    def _make_flow(
        self, device_type: str = DEVICE_TYPE_LITTERBOX
    ) -> PetSnowyConfigFlow:
        """Create a config flow ready for device step."""
        flow = PetSnowyConfigFlow()
        flow.hass = MagicMock()
        flow._device_type = device_type
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()
        flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
        return flow

    @pytest.mark.asyncio
    async def test_device_step_shows_form(self) -> None:
        """Device step shows credentials form when no input."""
        flow = self._make_flow()
        result = await flow.async_step_device()
        assert result["type"] == "form"
        assert result["step_id"] == "device"

    @pytest.mark.asyncio
    async def test_device_step_success(self) -> None:
        """Successful connection creates config entry."""
        flow = self._make_flow()
        mock_device = AsyncMock()
        mock_device.connect = AsyncMock()
        mock_device.disconnect = AsyncMock()

        with patch(
            "custom_components.petsnowy.config_flow.build_device",
            MagicMock(return_value=mock_device),
        ):
            result = await flow.async_step_device(
                {
                    CONF_DEVICE_ID: "abc123",
                    CONF_ADDRESS: "192.168.1.100",
                    CONF_LOCAL_KEY: "somekey",
                    CONF_VERSION: 3.4,
                }
            )

        flow.async_set_unique_id.assert_called_once_with("abc123")
        flow._abort_if_unique_id_configured.assert_called_once()
        mock_device.connect.assert_called_once()
        mock_device.disconnect.assert_called_once()
        flow.async_create_entry.assert_called_once()
        entry_data = flow.async_create_entry.call_args[1]["data"]
        assert entry_data[CONF_DEVICE_ID] == "abc123"
        assert entry_data[CONF_DEVICE_TYPE] == DEVICE_TYPE_LITTERBOX

    @pytest.mark.asyncio
    async def test_device_step_connection_error(self) -> None:
        """Connection failure shows error and allows retry."""
        flow = self._make_flow()
        mock_device = AsyncMock()
        mock_device.connect = AsyncMock(side_effect=Exception("timeout"))
        mock_device.disconnect = AsyncMock()

        with patch(
            "custom_components.petsnowy.config_flow.build_device",
            MagicMock(return_value=mock_device),
        ):
            result = await flow.async_step_device(
                {
                    CONF_DEVICE_ID: "abc123",
                    CONF_ADDRESS: "192.168.1.100",
                    CONF_LOCAL_KEY: "badkey",
                    CONF_VERSION: 3.4,
                }
            )

        assert result["type"] == "form"
        assert result["errors"]["base"] == "cannot_connect"

    @pytest.mark.asyncio
    async def test_device_step_error_recovery(self) -> None:
        """After a connection error, user can retry and succeed."""
        flow = self._make_flow()

        # First attempt: fail
        mock_device_bad = AsyncMock()
        mock_device_bad.connect = AsyncMock(side_effect=Exception("timeout"))
        mock_device_bad.disconnect = AsyncMock()

        with patch(
            "custom_components.petsnowy.config_flow.build_device",
            MagicMock(return_value=mock_device_bad),
        ):
            result = await flow.async_step_device(
                {
                    CONF_DEVICE_ID: "abc123",
                    CONF_ADDRESS: "192.168.1.100",
                    CONF_LOCAL_KEY: "badkey",
                    CONF_VERSION: 3.4,
                }
            )
        assert result["errors"]["base"] == "cannot_connect"

        # Second attempt: succeed
        mock_device_good = AsyncMock()
        mock_device_good.connect = AsyncMock()
        mock_device_good.disconnect = AsyncMock()

        with patch(
            "custom_components.petsnowy.config_flow.build_device",
            MagicMock(return_value=mock_device_good),
        ):
            await flow.async_step_device(
                {
                    CONF_DEVICE_ID: "abc123",
                    CONF_ADDRESS: "192.168.1.100",
                    CONF_LOCAL_KEY: "goodkey",
                    CONF_VERSION: 3.4,
                }
            )
        flow.async_create_entry.assert_called_once()

    @pytest.mark.asyncio
    async def test_device_step_duplicate_aborts(self) -> None:
        """Duplicate device ID aborts with already_configured."""
        flow = self._make_flow()
        from homeassistant.data_entry_flow import AbortFlow

        flow._abort_if_unique_id_configured = MagicMock(
            side_effect=AbortFlow("already_configured")
        )

        mock_device = AsyncMock()

        with (
            patch(
                "custom_components.petsnowy.config_flow.build_device",
                MagicMock(return_value=mock_device),
            ),
            pytest.raises(AbortFlow, match="already_configured"),
        ):
            await flow.async_step_device(
                {
                    CONF_DEVICE_ID: "already_exists",
                    CONF_ADDRESS: "192.168.1.100",
                    CONF_LOCAL_KEY: "somekey",
                    CONF_VERSION: 3.4,
                }
            )

    @pytest.mark.asyncio
    async def test_device_step_uses_default_version(self) -> None:
        """Version defaults correctly when not provided."""
        flow = self._make_flow(DEVICE_TYPE_FOUNTAIN)
        mock_device = AsyncMock()
        mock_device.connect = AsyncMock()
        mock_device.disconnect = AsyncMock()

        with patch(
            "custom_components.petsnowy.config_flow.build_device",
            MagicMock(return_value=mock_device),
        ):
            await flow.async_step_device(
                {
                    CONF_DEVICE_ID: "fountain_01",
                    CONF_ADDRESS: "192.168.1.101",
                    CONF_LOCAL_KEY: "key123",
                }
            )

        entry_data = flow.async_create_entry.call_args[1]["data"]
        assert entry_data[CONF_VERSION] == 3.3


class TestConfigFlowCloudStep:
    """Tests for the OilClear cloud credential step."""

    def _make_flow(self) -> PetSnowyConfigFlow:
        """Create a config flow ready for the cloud step."""
        flow = PetSnowyConfigFlow()
        flow.hass = MagicMock()
        flow._device_type = DEVICE_TYPE_OILCLEAR
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()
        flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})
        return flow

    @pytest.mark.asyncio
    async def test_user_step_routes_oilclear_to_cloud(self) -> None:
        """Selecting the OilClear advances to the cloud step, not device."""
        flow = PetSnowyConfigFlow()
        flow.hass = MagicMock()
        flow.async_step_cloud = AsyncMock(
            return_value={"type": "form", "step_id": "cloud"}
        )
        await flow.async_step_user({CONF_DEVICE_TYPE: DEVICE_TYPE_OILCLEAR})
        assert flow._device_type == DEVICE_TYPE_OILCLEAR
        flow.async_step_cloud.assert_called_once()

    @pytest.mark.asyncio
    async def test_cloud_step_shows_form(self) -> None:
        """Cloud step shows the credential form when no input."""
        flow = self._make_flow()
        result = await flow.async_step_cloud()
        assert result["type"] == "form"
        assert result["step_id"] == "cloud"

    @pytest.mark.asyncio
    async def test_cloud_step_success(self) -> None:
        """Valid cloud credentials create a config entry."""
        flow = self._make_flow()
        mock_device = AsyncMock()
        mock_device.connect = AsyncMock()
        mock_device.disconnect = AsyncMock()

        with patch(
            "custom_components.petsnowy.config_flow.build_device",
            MagicMock(return_value=mock_device),
        ):
            await flow.async_step_cloud(
                {
                    CONF_DEVICE_ID: "bf0715a9362035a7424efn",
                    CONF_REGION: "eu",
                    CONF_CLIENT_ID: "access_id",
                    CONF_CLIENT_SECRET: "access_secret",
                }
            )

        flow.async_create_entry.assert_called_once()
        entry_data = flow.async_create_entry.call_args[1]["data"]
        assert entry_data[CONF_DEVICE_TYPE] == DEVICE_TYPE_OILCLEAR
        assert entry_data[CONF_REGION] == "eu"
        assert entry_data[CONF_CLIENT_ID] == "access_id"
        assert CONF_ADDRESS not in entry_data

    @pytest.mark.asyncio
    async def test_cloud_step_connection_error(self) -> None:
        """Bad cloud credentials show a cannot_connect error."""
        flow = self._make_flow()
        mock_device = AsyncMock()
        mock_device.connect = AsyncMock(side_effect=Exception("auth failed"))
        mock_device.disconnect = AsyncMock()

        with patch(
            "custom_components.petsnowy.config_flow.build_device",
            MagicMock(return_value=mock_device),
        ):
            result = await flow.async_step_cloud(
                {
                    CONF_DEVICE_ID: "bf0715a9362035a7424efn",
                    CONF_REGION: "eu",
                    CONF_CLIENT_ID: "access_id",
                    CONF_CLIENT_SECRET: "bad_secret",
                }
            )

        assert result["type"] == "form"
        assert result["errors"]["base"] == "cannot_connect"
