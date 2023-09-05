# mypy: warn_unreachable=False
from typing import Generator
from unittest.mock import DEFAULT, call

import pytest
from bleak.backends.client import BLEDevice
from bleak.exc import BleakDBusError
from pytest_mock import MockerFixture

from pysnooz.const import UnknownSnoozState
from pysnooz.api import (
    RETRY_SLEEP_DURATIONS,
    SnoozDeviceApi,
    SnoozDeviceState,
)
from pysnooz.testing import MockSnoozClient

DBUS_ERROR = BleakDBusError("org.bluez.Error", [])
DBUS_ERROR_IN_PROGRESS = BleakDBusError("org.bluez.Error.InProgress", [])


@pytest.fixture()
def mock_client() -> Generator[MockSnoozClient, None, None]:
    yield MockSnoozClient(BLEDevice("Snooz-ABCD", "00:00:00:00:12:34", [], 0))


@pytest.fixture()
def mock_api(mock_client: MockSnoozClient) -> Generator[SnoozDeviceApi, None, None]:
    yield SnoozDeviceApi(mock_client)


@pytest.mark.smokey
def test_state_operators() -> None:
    assert SnoozDeviceState(on=True, volume=None) == SnoozDeviceState(
        on=True, volume=None
    )
    assert SnoozDeviceState(on=False, volume=None) == SnoozDeviceState(
        on=False, volume=None
    )
    assert SnoozDeviceState(on=True, volume=10) == SnoozDeviceState(on=True, volume=10)
    assert SnoozDeviceState(on=False, volume=13) == SnoozDeviceState(
        on=False, volume=13
    )
    assert SnoozDeviceState(on=False, volume=13) != SnoozDeviceState(
        on=False, volume=15
    )

    assert SnoozDeviceState(fan_on=True, fan_speed=None) == SnoozDeviceState(
        fan_on=True, fan_speed=None
    )
    assert SnoozDeviceState(fan_on=False, fan_speed=None) == SnoozDeviceState(
        fan_on=False, fan_speed=None
    )
    assert SnoozDeviceState(fan_on=True, fan_speed=10) == SnoozDeviceState(
        fan_on=True, fan_speed=10
    )
    assert SnoozDeviceState(fan_on=False, fan_speed=13) == SnoozDeviceState(
        fan_on=False, fan_speed=13
    )
    assert SnoozDeviceState(fan_on=False, fan_speed=13) != SnoozDeviceState(
        fan_on=False, fan_speed=15
    )


def test_repr() -> None:
    assert UnknownSnoozState.__repr__() == "Snooz(Unknown)"
    assert (
        SnoozDeviceState(on=True, volume=10).__repr__()
        == "Snooz(Noise On at 10% volume)"
    )
    assert (
        SnoozDeviceState(on=False, volume=15).__repr__()
        == "Snooz(Noise Off at 15% volume)"
    )


@pytest.mark.asyncio
async def test_properties(mock_api: SnoozDeviceApi) -> None:
    assert mock_api.is_connected is True
    await mock_api.async_disconnect()
    assert mock_api.is_connected is False


@pytest.mark.asyncio
async def test_retries_write_errors(
    mocker: MockerFixture, mock_client: MockSnoozClient
) -> None:
    mock_sleep = mocker.patch("asyncio.sleep")
    mock_write_gatt_char = mocker.patch.object(mock_client, "write_gatt_char")
    mock_write_gatt_char.side_effect = [
        DBUS_ERROR,
        DBUS_ERROR_IN_PROGRESS,
        DBUS_ERROR,
        DBUS_ERROR_IN_PROGRESS,
        DEFAULT,
    ]
    api = SnoozDeviceApi(mock_client)
    await api.async_set_volume(30)
    assert mock_write_gatt_char.call_count == 5
    assert mock_sleep.mock_calls == [call(d) for d in RETRY_SLEEP_DURATIONS[0:4]]


@pytest.mark.asyncio
async def test_raises_write_errors_after_retries_exhausted(
    mocker: MockerFixture, mock_client: MockSnoozClient
) -> None:
    mock_sleep = mocker.patch("asyncio.sleep")
    mock_write_gatt_char = mocker.patch.object(mock_client, "write_gatt_char")
    mock_write_gatt_char.side_effect = DBUS_ERROR
    api = SnoozDeviceApi(mock_client)
    with pytest.raises(Exception):
        await api.async_set_volume(30)
    assert mock_write_gatt_char.call_count == 6
    assert mock_sleep.mock_calls == [call(d) for d in RETRY_SLEEP_DURATIONS]


@pytest.mark.asyncio
async def test_raises_unknown_write_errors(
    mocker: MockerFixture, mock_client: MockSnoozClient
) -> None:
    mock_write_gatt_char = mocker.patch.object(mock_client, "write_gatt_char")
    mock_write_gatt_char.side_effect = Exception("Test error")
    api = SnoozDeviceApi(mock_client)
    with pytest.raises(Exception):
        await api.async_set_volume(30)
    assert mock_write_gatt_char.call_count == 1


@pytest.mark.asyncio
async def test_volume_validation(mocker: MockerFixture) -> None:
    mock_client = mocker.MagicMock(autospec=MockSnoozClient)
    api = SnoozDeviceApi(mock_client)
    with pytest.raises(ValueError):
        await api.async_set_volume(-10)
    with pytest.raises(ValueError):
        await api.async_set_volume(110)
    mock_client.write_gatt_char.assert_not_called()
