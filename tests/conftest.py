"""Shared test fixtures for PetSnowy integration tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.petsnowy.const import (
    CONF_ADDRESS,
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_LOCAL_KEY,
    CONF_VERSION,
    DEVICE_TYPE_FEEDER,
    DEVICE_TYPE_FOUNTAIN,
    DEVICE_TYPE_LITTERBOX,
    DEVICE_TYPE_PURIFIER,
)

MOCK_LITTERBOX_CONFIG: dict[str, Any] = {
    CONF_DEVICE_TYPE: DEVICE_TYPE_LITTERBOX,
    CONF_DEVICE_ID: "test_litterbox_001",
    CONF_ADDRESS: "192.168.1.100",
    CONF_LOCAL_KEY: "test_local_key_abc",
    CONF_VERSION: 3.4,
}

MOCK_FOUNTAIN_CONFIG: dict[str, Any] = {
    CONF_DEVICE_TYPE: DEVICE_TYPE_FOUNTAIN,
    CONF_DEVICE_ID: "test_fountain_001",
    CONF_ADDRESS: "192.168.1.101",
    CONF_LOCAL_KEY: "test_local_key_def",
    CONF_VERSION: 3.3,
}

MOCK_PURIFIER_CONFIG: dict[str, Any] = {
    CONF_DEVICE_TYPE: DEVICE_TYPE_PURIFIER,
    CONF_DEVICE_ID: "test_purifier_001",
    CONF_ADDRESS: "192.168.1.102",
    CONF_LOCAL_KEY: "test_local_key_ghi",
    CONF_VERSION: 3.4,
}

MOCK_FEEDER_CONFIG: dict[str, Any] = {
    CONF_DEVICE_TYPE: DEVICE_TYPE_FEEDER,
    CONF_DEVICE_ID: "test_feeder_001",
    CONF_ADDRESS: "192.168.1.103",
    CONF_LOCAL_KEY: "test_local_key_jkl",
    CONF_VERSION: 3.3,
}


MOCK_LITTERBOX_DPS: dict[str, Any] = {
    "1": True,
    "4": True,
    "5": 10,
    "6": 4500,
    "7": 3,
    "8": 120,
    "9": False,
    "10": False,
    "16": True,
    "17": False,
    "21": 0,
    "22": 0,
    "24": "standby",
    "102": 25,
    "104": True,
    "107": True,
}

MOCK_FOUNTAIN_DPS: dict[str, Any] = {
    "1": True,
    "2": "normal",
    "3": 15,
    "4": 5,
    "7": 30,
    "102": True,
}

MOCK_PURIFIER_DPS: dict[str, Any] = {
    "1": True,
    "3": "auto",
    "4": "3",
    "6": True,
    "14": 150,
    "16": 45,
    "18": "cancel",
    "19": 0,
    "22": 0,
}

MOCK_FEEDER_DPS: dict[str, Any] = {
    "6": "enough",
    "13": 0,
}


@pytest.fixture
def mock_litterbox_device() -> AsyncMock:
    """Return a mocked PetSnowy litterbox device."""
    from petsnowy import DeviceState

    device = AsyncMock()
    device.get_state = AsyncMock(
        return_value=DeviceState.from_dps(MOCK_LITTERBOX_DPS)
    )
    device.connect = AsyncMock()
    device.disconnect = AsyncMock()
    return device


@pytest.fixture
def mock_fountain_device() -> AsyncMock:
    """Return a mocked Fountain device."""
    from petsnowy import FountainState

    device = AsyncMock()
    device.get_state = AsyncMock(
        return_value=FountainState.from_dps(MOCK_FOUNTAIN_DPS)
    )
    device.connect = AsyncMock()
    device.disconnect = AsyncMock()
    return device


@pytest.fixture
def mock_purifier_device() -> AsyncMock:
    """Return a mocked Purifier device."""
    from petsnowy import PurifierState

    device = AsyncMock()
    device.get_state = AsyncMock(
        return_value=PurifierState.from_dps(MOCK_PURIFIER_DPS)
    )
    device.connect = AsyncMock()
    device.disconnect = AsyncMock()
    return device


@pytest.fixture
def mock_feeder_device() -> AsyncMock:
    """Return a mocked Feeder device."""
    from petsnowy import FeederState

    device = AsyncMock()
    device.get_state = AsyncMock(
        return_value=FeederState.from_dps(MOCK_FEEDER_DPS)
    )
    device.connect = AsyncMock()
    device.disconnect = AsyncMock()
    return device
