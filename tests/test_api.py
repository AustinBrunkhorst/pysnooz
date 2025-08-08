# mypy: warn_unreachable=False
import struct
from unittest.mock import DEFAULT, call

import pytest
from bleak.backends.client import BLEDevice
from bleak.exc import BleakDBusError
from pytest_mock import MockerFixture

from pysnooz.api import (
    RETRY_SLEEP_DURATIONS,
    MissingCharacteristicError,
    ResponseCommand,
    SnoozDeviceApi,
    unpack_response_command,
)
from pysnooz.model import SnoozDeviceModel, SnoozDeviceState
from pysnooz.testing import MockSnoozClient

DBUS_ERROR = BleakDBusError("org.bluez.Error", [])
DBUS_ERROR_IN_PROGRESS = BleakDBusError("org.bluez.Error.InProgress", [])
DBUS_ERROR_UNKNOWN = BleakDBusError("org.bluez.Error.SomethingNotHandled", [])


@pytest.fixture()
def mock_client() -> MockSnoozClient:
    return MockSnoozClient(
        BLEDevice("Snooz-ABCD", "00:00:00:00:12:34", []), SnoozDeviceModel.ORIGINAL
    )


@pytest.fixture()
def mock_api(mock_client: MockSnoozClient) -> SnoozDeviceApi:
    return SnoozDeviceApi(mock_client)


@pytest.mark.asyncio
async def test_properties(mock_api: SnoozDeviceApi) -> None:
    assert mock_api.is_connected is True
    await mock_api.async_disconnect()
    assert mock_api.is_connected is False


@pytest.mark.asyncio
async def test_client_assertions(
    mocker: MockerFixture, mock_client: MockSnoozClient
) -> None:
    api = SnoozDeviceApi()

    with pytest.raises(AssertionError):
        await api.async_disconnect()
    with pytest.raises(AssertionError):
        await api.async_authenticate_connection("12345678")
    with pytest.raises(AssertionError):
        await api.async_subscribe()
    with pytest.raises(AssertionError):
        await api.async_get_info()
    with pytest.raises(AssertionError):
        await api.async_read_state()
    with pytest.raises(AssertionError):
        await api.async_request_other_settings()
    with pytest.raises(AssertionError):
        await api.async_set_power(True)
    with pytest.raises(AssertionError):
        await api.async_set_volume(10)
    with pytest.raises(AssertionError):
        await api.async_set_fan_power(True)
    with pytest.raises(AssertionError):
        await api.async_set_fan_speed(10)
    with pytest.raises(AssertionError):
        await api.async_set_auto_temp_enabled(True)
    with pytest.raises(AssertionError):
        await api.async_set_auto_temp_threshold(60)

    mock_client.trigger_disconnect()
    api.load_client(mock_client)

    with pytest.raises(AssertionError):
        await api.async_read_state()

    assert await api.async_get_info() is None

    notify_spy = mocker.spy(mock_client, "start_notify")
    await api.async_subscribe()
    notify_spy.assert_not_called()


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
    mock_write_gatt_char.side_effect = [Exception("Test error"), DBUS_ERROR_UNKNOWN]
    api = SnoozDeviceApi(mock_client)
    with pytest.raises(Exception):
        await api.async_set_volume(30)
    with pytest.raises(BleakDBusError):
        await api.async_set_volume(30)
    assert mock_write_gatt_char.call_count == 2


@pytest.mark.asyncio
async def test_brightness_validation(mocker: MockerFixture) -> None:
    mock_client = mocker.MagicMock(autospec=MockSnoozClient)
    api = SnoozDeviceApi(mock_client)
    with pytest.raises(ValueError):
        await api.async_set_light_brightness(-10)
    with pytest.raises(ValueError):
        await api.async_set_light_brightness(110)
    mock_client.write_gatt_char.assert_not_called()


@pytest.mark.asyncio
async def test_volume_validation(mocker: MockerFixture) -> None:
    mock_client = mocker.MagicMock(autospec=MockSnoozClient)
    api = SnoozDeviceApi(mock_client)
    with pytest.raises(ValueError):
        await api.async_set_volume(-10)
    with pytest.raises(ValueError):
        await api.async_set_volume(110)
    mock_client.write_gatt_char.assert_not_called()


@pytest.mark.asyncio
async def test_fan_speed_validation(mocker: MockerFixture) -> None:
    mock_client = mocker.MagicMock(autospec=MockSnoozClient)
    api = SnoozDeviceApi(mock_client)
    with pytest.raises(ValueError):
        await api.async_set_fan_speed(-10)
    with pytest.raises(ValueError):
        await api.async_set_fan_speed(110)
    mock_client.write_gatt_char.assert_not_called()


@pytest.mark.asyncio
async def test_auto_temp_threshold_validation(mocker: MockerFixture) -> None:
    mock_client = mocker.MagicMock(autospec=MockSnoozClient)
    api = SnoozDeviceApi(mock_client)
    with pytest.raises(ValueError):
        await api.async_set_auto_temp_threshold(-10)
    with pytest.raises(ValueError):
        await api.async_set_auto_temp_threshold(110)
    mock_client.write_gatt_char.assert_not_called()


@pytest.mark.asyncio
async def test_missing_characteristics(mock_client: MockSnoozClient) -> None:
    api = SnoozDeviceApi()
    api.load_client(mock_client)

    mock_client._services.get_characteristic.side_effect = lambda _: None

    with pytest.raises(MissingCharacteristicError):
        api.load_client(mock_client)

    with pytest.raises(MissingCharacteristicError):
        await api.async_read_state()

    with pytest.raises(MissingCharacteristicError):
        await api.async_get_info()


def test_unpack_response_command() -> None:
    temp = 37.5
    state = unpack_response_command(
        ResponseCommand.TEMPERATURE, struct.pack("<f", temp)
    )
    assert state.temperature == temp

    target_temp = 44
    state = unpack_response_command(
        ResponseCommand.SEND_OTHER_SETTINGS,
        bytes([0x00] * 10) + bytes([0x01, target_temp]),
    )
    assert state.fan_auto_enabled is True
    assert state.target_temperature == target_temp

    assert unpack_response_command(99, bytes([])) == SnoozDeviceState()  # type: ignore
