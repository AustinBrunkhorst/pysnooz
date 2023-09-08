# mypy: warn_unreachable=False
from __future__ import annotations

import asyncio
import re
from asyncio import AbstractEventLoop
from datetime import timedelta
from typing import Any, Callable
from unittest.mock import MagicMock, call

import pytest
from bleak import BleakClient, BleakGATTServiceCollection
from bleak.backends.device import BLEDevice
from pytest_mock import MockerFixture

from pysnooz.api import (
    CharacteristicReference,
    MissingCharacteristicError,
    SnoozDeviceApi,
)
from pysnooz.commands import (
    SnoozCommandData,
    SnoozCommandResultStatus,
    set_auto_temp_enabled,
    set_fan_speed,
    set_temp_target,
    set_volume,
    turn_fan_off,
    turn_fan_on,
    turn_off,
    turn_on,
)
from pysnooz.const import MODEL_NAME_BREEZ, MODEL_NAME_SNOOZ
from pysnooz.device import (
    DEVICE_UNAVAILABLE_EXCEPTIONS,
    MAX_RECONNECTION_ATTEMPTS,
    SnoozConnectionStatus,
    SnoozDevice,
)
from pysnooz.model import (
    SnoozAdvertisementData,
    SnoozDeviceModel,
    SnoozFirmwareVersion,
    SnoozDeviceState,
)
from pysnooz.testing import MockSnoozClient


class SnoozTestFixture:
    def __init__(
        self,
        model: SnoozDeviceModel,
        ble_device: BLEDevice,
        adv_data: SnoozAdvertisementData,
        loop: AbstractEventLoop,
        mock_connect: MagicMock,
        trigger_disconnect: Callable[[SnoozDevice], None],
        trigger_temperature: Callable[[SnoozDevice, float], None],
    ):
        self.model = model
        self.ble_device = ble_device
        self.adv_data = adv_data
        self.loop = loop
        self.mock_connect = mock_connect
        self.trigger_disconnect = trigger_disconnect
        self.trigger_temperature = trigger_temperature

    def create_device(self) -> SnoozDevice:
        return SnoozDevice(self.ble_device, self.adv_data, self.loop)

    def mock_connection_fails(self) -> None:
        self.mock_connect.side_effect = DEVICE_UNAVAILABLE_EXCEPTIONS[0](
            "Connection error for testing device unavailable"
        )

    async def assert_command_success(
        self, device: SnoozDevice, data: SnoozCommandData
    ) -> None:
        await self._assert_command_status(
            device, data, SnoozCommandResultStatus.SUCCESSFUL
        )

    async def assert_command_cancelled(
        self, device: SnoozDevice, data: SnoozCommandData
    ) -> None:
        await self._assert_command_status(
            device, data, SnoozCommandResultStatus.CANCELLED
        )

    async def assert_command_device_unavailable(
        self, device: SnoozDevice, data: SnoozCommandData
    ) -> None:
        await self._assert_command_status(
            device, data, SnoozCommandResultStatus.DEVICE_UNAVAILABLE
        )

    async def assert_command_unexpected_error(
        self, device: SnoozDevice, data: SnoozCommandData
    ) -> None:
        await self._assert_command_status(
            device, data, SnoozCommandResultStatus.UNEXPECTED_ERROR
        )

    async def _assert_command_status(
        self,
        device: SnoozDevice,
        data: SnoozCommandData,
        status: SnoozCommandResultStatus,
    ) -> None:
        result = await device.async_execute_command(data)
        assert result.status == status


@pytest.fixture(scope="function")
def snooz(
    request: pytest.FixtureRequest, mocker: MockerFixture, event_loop: AbstractEventLoop
) -> SnoozTestFixture:
    model = SnoozDeviceModel.ORIGINAL

    model_marker = request.node.get_closest_marker("model")
    if model_marker is not None:
        model = model_marker.args[0]

    model_name = (
        MODEL_NAME_BREEZ if model == SnoozDeviceModel.BREEZ else MODEL_NAME_SNOOZ
    )
    device = BLEDevice("AA:BB:CC:DD:EE:FF", f"{model_name}-EEFF", [], 0)
    password = "AABBCCDDEEFF"
    adv_data = SnoozAdvertisementData(
        model,
        SnoozFirmwareVersion.V2
        if model == SnoozDeviceModel.ORIGINAL
        else SnoozFirmwareVersion.V6,
        password,
    )

    def get_connected_client(
        client_class: type[BleakClient],
        device: BLEDevice,
        name: str,
        disconnected_callback: Callable[[BleakClient], None] | None,
        max_attempts: int = 0,
        cached_services: BleakGATTServiceCollection | None = None,
        ble_device_callback: Callable[[], BLEDevice] | None = None,
        use_services_cache: bool = False,
        **kwargs: Any,
    ) -> MockSnoozClient:
        return MockSnoozClient(device, model, disconnected_callback)

    mock_connect = mocker.patch("pysnooz.device.establish_connection", autospec=True)
    mock_connect.side_effect = get_connected_client

    def trigger_disconnect(target: SnoozDevice) -> None:
        assert isinstance(target._api._client, MockSnoozClient)
        target._api._client.trigger_disconnect()

    def trigger_temperature(target: SnoozDevice, temp: float) -> None:
        assert isinstance(target._api._client, MockSnoozClient)
        target._api._client.trigger_temperature(temp)

    return SnoozTestFixture(
        model=model,
        ble_device=device,
        adv_data=adv_data,
        loop=event_loop,
        mock_connect=mock_connect,
        trigger_disconnect=trigger_disconnect,
        trigger_temperature=trigger_temperature,
    )


def breez() -> SnoozTestFixture:
    return snooz(SnoozDeviceModel.BREEZ)


def test_display_name(snooz: SnoozTestFixture) -> None:
    device = snooz.create_device()
    assert re.search(r"^(Snooz|Breez) [A-Z0-9]{4}$", device.display_name) is not None


@pytest.mark.asyncio
async def test_basic_commands(mocker: MockerFixture, snooz: SnoozTestFixture) -> None:
    on_connection_status_change = mocker.stub()
    on_state_change = mocker.stub()
    subscription_callback = mocker.stub()

    device = snooz.create_device()

    device.events.on_state_change += on_state_change
    device.events.on_connection_status_change += on_connection_status_change

    unsubscribe = device.subscribe_to_state_change(subscription_callback)

    # events should not occur until the device is connected
    on_connection_status_change.assert_not_called()
    on_state_change.assert_not_called()
    subscription_callback.assert_not_called()

    await snooz.assert_command_success(device, turn_on(volume=25))
    assert device.state.on is True
    assert device.state.volume == 25
    assert on_connection_status_change.mock_calls == (
        [call(SnoozConnectionStatus.CONNECTING), call(SnoozConnectionStatus.CONNECTED)]
    )
    on_connection_status_change.reset_mock()

    # for api simplicity, you can set the volume and power state in one command, but it
    # translates to two ble char writes
    assert on_state_change.call_count == 2
    on_state_change.assert_has_calls([call(SnoozDeviceState(on=True, volume=25))])
    on_state_change.reset_mock()

    # two connection status changes, two state changes
    assert subscription_callback.call_count == 4
    subscription_callback.reset_mock()

    await snooz.assert_command_success(device, turn_off())
    assert device.state.on is False
    on_state_change.assert_called_once_with(SnoozDeviceState(on=False, volume=25))
    on_state_change.reset_mock()
    subscription_callback.assert_called_once()
    subscription_callback.reset_mock()

    await snooz.assert_command_success(device, set_volume(36))
    assert device.state.volume == 36
    on_state_change.assert_called_once_with(SnoozDeviceState(on=False, volume=36))
    on_state_change.reset_mock()
    subscription_callback.assert_called_once()
    subscription_callback.reset_mock()

    # no other status changes should have occurred
    on_connection_status_change.assert_not_called()

    # when unsubscribe is called, the callback should stop being called
    unsubscribe()

    await snooz.assert_command_success(device, turn_on(99))
    subscription_callback.assert_not_called()

    await snooz.assert_command_success(device, turn_off())
    subscription_callback.assert_not_called()

    await snooz.assert_command_success(device, set_volume(15))
    subscription_callback.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.model(SnoozDeviceModel.BREEZ)
async def test_breez_commands(mocker: MockerFixture, snooz: SnoozTestFixture) -> None:
    on_connection_status_change = mocker.stub()
    on_state_change = mocker.stub()
    subscription_callback = mocker.stub()

    device = snooz.create_device()

    device.events.on_state_change += on_state_change
    device.events.on_connection_status_change += on_connection_status_change

    unsubscribe = device.subscribe_to_state_change(subscription_callback)

    # events should not occur until the device is connected
    on_connection_status_change.assert_not_called()
    on_state_change.assert_not_called()
    subscription_callback.assert_not_called()

    await snooz.assert_command_success(device, turn_fan_on(speed=25))
    assert device.state.fan_on is True
    assert device.state.fan_speed == 25
    assert on_connection_status_change.mock_calls == (
        [call(SnoozConnectionStatus.CONNECTING), call(SnoozConnectionStatus.CONNECTED)]
    )
    on_connection_status_change.reset_mock()

    # for api simplicity, you can set the fan speed and power state in one command,
    # but it translates to two ble char writes
    assert on_state_change.call_count == 2
    on_state_change.assert_has_calls(
        [call(SnoozDeviceState(on=False, volume=10, fan_on=True, fan_speed=25))]
    )
    on_state_change.reset_mock()

    # two connection status changes, two state changes
    assert subscription_callback.call_count == 4
    subscription_callback.reset_mock()

    await snooz.assert_command_success(device, turn_fan_off())
    assert device.state.fan_on is False
    on_state_change.assert_called_once_with(
        SnoozDeviceState(on=False, volume=10, fan_on=False, fan_speed=25)
    )
    on_state_change.reset_mock()
    subscription_callback.assert_called_once()
    subscription_callback.reset_mock()

    await snooz.assert_command_success(device, set_fan_speed(36))
    assert device.state.fan_speed == 36
    on_state_change.assert_called_once_with(
        SnoozDeviceState(on=False, volume=10, fan_on=False, fan_speed=36)
    )
    on_state_change.reset_mock()
    subscription_callback.assert_called_once()
    subscription_callback.reset_mock()

    await snooz.assert_command_success(device, set_auto_temp_enabled(True))
    assert device.state.fan_auto_enabled is True
    on_state_change.assert_called_once_with(
        SnoozDeviceState(
            on=False,
            volume=10,
            fan_on=False,
            fan_speed=36,
            fan_auto_enabled=True,
            target_temperature=0,
        )
    )
    on_state_change.reset_mock()
    subscription_callback.assert_called_once()
    subscription_callback.reset_mock()

    await snooz.assert_command_success(device, set_temp_target(46))
    assert device.state.target_temperature == 46
    on_state_change.assert_called_once_with(
        SnoozDeviceState(
            on=False,
            volume=10,
            fan_on=False,
            fan_speed=36,
            fan_auto_enabled=True,
            target_temperature=46,
        )
    )
    on_state_change.reset_mock()
    subscription_callback.assert_called_once()
    subscription_callback.reset_mock()

    snooz.trigger_temperature(device, 75)
    assert device.state.temperature == 75
    on_state_change.assert_called_once_with(
        SnoozDeviceState(
            on=False,
            volume=10,
            fan_on=False,
            fan_speed=36,
            fan_auto_enabled=True,
            target_temperature=46,
            temperature=75,
        )
    )
    on_state_change.reset_mock()
    subscription_callback.assert_called_once()
    subscription_callback.reset_mock()

    # no other status changes should have occurred
    on_connection_status_change.assert_not_called()

    # when unsubscribe is called, the callback should stop being called
    unsubscribe()

    await snooz.assert_command_success(device, turn_fan_on(99))
    subscription_callback.assert_not_called()

    await snooz.assert_command_success(device, turn_fan_off())
    subscription_callback.assert_not_called()

    await snooz.assert_command_success(device, set_fan_speed(15))
    subscription_callback.assert_not_called()

    await snooz.assert_command_success(device, set_auto_temp_enabled(True))
    subscription_callback.assert_not_called()

    await snooz.assert_command_success(device, set_temp_target(64))
    subscription_callback.assert_not_called()


@pytest.mark.asyncio
async def test_device_info(mocker: MockerFixture, snooz: SnoozTestFixture) -> None:
    device = snooz.create_device()

    info = await device.async_get_info()
    assert info.firmware is not None
    assert info.hardware is not None
    assert info.manufacturer is not None
    assert info.model is not None
    assert info.software is None


@pytest.mark.asyncio
@pytest.mark.model(SnoozDeviceModel.BREEZ)
async def test_device_info_breez(
    mocker: MockerFixture, snooz: SnoozTestFixture
) -> None:
    device = snooz.create_device()

    info = await device.async_get_info()
    assert info.firmware is not None
    assert info.hardware is not None
    assert info.manufacturer is not None
    assert info.model is not None
    assert info.software is not None


@pytest.mark.asyncio
async def test_auto_reconnect(mocker: MockerFixture, snooz: SnoozTestFixture) -> None:
    on_connection_change = mocker.stub()

    device = snooz.create_device()

    device.events.on_connection_status_change += on_connection_change

    await snooz.assert_command_success(device, turn_on())
    assert device.is_connected

    snooz.trigger_disconnect(device)
    assert not device.is_connected

    # wait for the reconnection task to complete
    await asyncio.wait_for(device._reconnection_task, timeout=1)

    assert on_connection_change.mock_calls == (
        [
            call(SnoozConnectionStatus.CONNECTING),
            call(SnoozConnectionStatus.CONNECTED),
            call(SnoozConnectionStatus.DISCONNECTED),
            call(SnoozConnectionStatus.CONNECTING),
            call(SnoozConnectionStatus.CONNECTED),
        ]
    )
    assert device.is_connected
    on_connection_change.reset_mock()

    await snooz.assert_command_success(device, set_volume(39))
    assert device.state.volume == 39

    # should reuse existing connections
    on_connection_change.assert_not_called()


@pytest.mark.asyncio
async def test_auto_reconnect_device_unavailable(
    mocker: MockerFixture, snooz: SnoozTestFixture
) -> None:
    on_connection_change = mocker.stub()

    device = snooz.create_device()

    device.events.on_connection_status_change += on_connection_change

    await snooz.assert_command_success(device, turn_on())
    assert device.is_connected

    snooz.mock_connection_fails()

    snooz.trigger_disconnect(device)
    assert not device.is_connected

    await asyncio.wait_for(device._connections_exhausted.wait(), timeout=3)

    assert on_connection_change.mock_calls == (
        [
            call(SnoozConnectionStatus.CONNECTING),
            call(SnoozConnectionStatus.CONNECTED),
            call(SnoozConnectionStatus.DISCONNECTED),
            *[
                call(SnoozConnectionStatus.CONNECTING),
                call(SnoozConnectionStatus.DISCONNECTED),
            ]
            * MAX_RECONNECTION_ATTEMPTS,
        ]
    )
    assert not device.is_connected


@pytest.mark.asyncio
async def test_manual_disconnect(
    mocker: MockerFixture, snooz: SnoozTestFixture
) -> None:
    on_connection_change = mocker.stub()

    device = snooz.create_device()
    device.events.on_connection_status_change += on_connection_change

    # should be noop when not connected
    await device.async_disconnect()

    on_connection_change.assert_not_called()
    on_connection_change.reset_mock()

    await snooz.assert_command_success(device, turn_on())
    assert device.is_connected

    await device.async_disconnect()
    assert not device.is_connected
    await asyncio.sleep(0.1)

    assert device._reconnection_task is None

    assert on_connection_change.mock_calls == (
        [
            call(SnoozConnectionStatus.CONNECTING),
            call(SnoozConnectionStatus.CONNECTED),
            call(SnoozConnectionStatus.DISCONNECTED),
        ]
    )


@pytest.mark.asyncio
async def test_establish_connection_exceptions(
    mocker: MockerFixture, snooz: SnoozTestFixture
) -> None:
    for ex in DEVICE_UNAVAILABLE_EXCEPTIONS:
        await _test_connection_exception(mocker, snooz, ex)


async def _test_connection_exception(
    mocker: MockerFixture, snooz: SnoozTestFixture, connection_exception: type
) -> None:
    snooz.mock_connect.side_effect = connection_exception()

    on_connection_change = mocker.stub()
    on_state_change = mocker.stub()

    device = snooz.create_device()
    device.events.on_connection_status_change += on_connection_change
    device.events.on_state_change += on_state_change

    await snooz.assert_command_device_unavailable(device, turn_on(volume=26))
    await asyncio.sleep(0.1)
    assert (
        on_connection_change.mock_calls
        == [
            call(SnoozConnectionStatus.CONNECTING),
            call(SnoozConnectionStatus.DISCONNECTED),
        ]
        * MAX_RECONNECTION_ATTEMPTS
    )
    assert not device.is_connected
    assert device.state.volume != 26
    on_state_change.assert_not_called()


@pytest.mark.asyncio
async def test_write_exception_during_reconnection(
    mocker: MockerFixture, snooz: SnoozTestFixture
) -> None:
    mock_authenticate = mocker.patch(
        "pysnooz.device.SnoozDeviceApi.async_authenticate_connection",
        autospec=True,
    )

    def trigger_disconnect_then_raises(*args, **kwargs):
        if mock_authenticate.call_count == 1:
            snooz.trigger_disconnect(device)
        else:
            raise Exception("Testing an unexpected exception")

    mock_authenticate.side_effect = trigger_disconnect_then_raises

    on_connection_change = mocker.stub()
    on_state_change = mocker.stub()

    device = snooz.create_device()
    device.events.on_connection_status_change += on_connection_change
    device.events.on_state_change += on_state_change

    await snooz.assert_command_unexpected_error(device, turn_on(volume=26))
    assert on_connection_change.mock_calls == (
        [
            call(SnoozConnectionStatus.CONNECTING),
            call(SnoozConnectionStatus.DISCONNECTED),
            call(SnoozConnectionStatus.CONNECTING),
            call(SnoozConnectionStatus.DISCONNECTED),
        ]
    )
    on_state_change.assert_not_called()


@pytest.mark.asyncio
async def test_manual_disconnect_during_reconnect(
    mocker: MockerFixture, snooz: SnoozTestFixture
) -> None:
    mock_authenticate = mocker.patch(
        "pysnooz.device.SnoozDeviceApi.async_authenticate_connection",
        autospec=True,
    )

    async def manual_disconnect_before_last_call(*args, **kwargs):
        if mock_authenticate.call_count == MAX_RECONNECTION_ATTEMPTS:
            await device.async_disconnect()
        else:
            snooz.trigger_disconnect(device)

    mock_authenticate.side_effect = manual_disconnect_before_last_call

    on_connection_change = mocker.stub()
    on_state_change = mocker.stub()

    device = snooz.create_device()
    device.events.on_connection_status_change += on_connection_change
    device.events.on_state_change += on_state_change

    await snooz.assert_command_cancelled(device, turn_on(volume=26))
    assert on_connection_change.mock_calls == (
        [
            *[
                call(SnoozConnectionStatus.CONNECTING),
                call(SnoozConnectionStatus.DISCONNECTED),
            ]
            * MAX_RECONNECTION_ATTEMPTS
        ]
    )
    on_state_change.assert_not_called()


@pytest.mark.asyncio
async def test_disconnect_before_ready(
    mocker: MockerFixture, snooz: SnoozTestFixture
) -> None:
    async def disconnects(*args, **kwargs):
        snooz.trigger_disconnect(device)

    mocker.patch(
        "pysnooz.device.SnoozDeviceApi.async_authenticate_connection", new=disconnects
    )

    on_connection_change = mocker.stub()
    on_state_change = mocker.stub()

    device = snooz.create_device()
    device.events.on_connection_status_change += on_connection_change
    device.events.on_state_change += on_state_change

    await snooz.assert_command_device_unavailable(device, turn_on(volume=26))
    assert on_connection_change.mock_calls == (
        [
            *[
                call(SnoozConnectionStatus.CONNECTING),
                call(SnoozConnectionStatus.DISCONNECTED),
            ]
            * MAX_RECONNECTION_ATTEMPTS
        ]
    )
    assert not device.is_connected
    assert device.state.volume != 26
    on_state_change.assert_not_called()


@pytest.mark.asyncio
async def test_device_disconnect_callback_after_disconnected(
    snooz: SnoozTestFixture,
) -> None:
    device = snooz.create_device()

    await snooz.assert_command_success(device, turn_on(volume=26))

    original_api = device._api

    await device.async_disconnect()
    await asyncio.sleep(0.1)

    # should be a noop
    original_api.events.on_disconnect()  # type: ignore

    await snooz.assert_command_success(device, turn_on(volume=27))

    # should be a noop
    original_api.events.on_disconnect()  # type: ignore

    assert device.is_connected
    assert device.state.volume == 27


@pytest.mark.asyncio
async def test_unexpected_error_before_ready(
    mocker: MockerFixture, snooz: SnoozTestFixture
) -> None:
    mock_authenticate = mocker.patch(
        "pysnooz.device.SnoozDeviceApi.async_authenticate_connection"
    )
    mock_authenticate.side_effect = Exception(
        "Expected unhandled exception for testing"
    )

    on_connection_change = mocker.stub()
    on_state_change = mocker.stub()

    device = snooz.create_device()
    device.events.on_connection_status_change += on_connection_change
    device.events.on_state_change += on_state_change

    await snooz.assert_command_unexpected_error(device, turn_on(volume=26))
    assert on_connection_change.mock_calls == [
        call(SnoozConnectionStatus.CONNECTING),
        call(SnoozConnectionStatus.DISCONNECTED),
    ]
    assert not device.is_connected
    assert device.state.volume != 26
    on_state_change.assert_not_called()


@pytest.mark.asyncio
async def test_unexpected_error_during_execution(
    mocker: MockerFixture, snooz: SnoozTestFixture, mock_sleep: None
) -> None:
    mock_set_volume = mocker.patch(
        "pysnooz.device.SnoozDeviceApi.async_set_volume",
        autospec=True,
    )
    mock_set_volume.side_effect = Exception("Expected unhandled exception for testing")

    on_connection_change = mocker.stub()
    on_state_change = mocker.stub()

    device = snooz.create_device()
    device.events.on_connection_status_change += on_connection_change
    device.events.on_state_change += on_state_change

    await snooz.assert_command_unexpected_error(device, turn_on(volume=26))
    assert device.is_connected
    assert device.state.volume != 26
    on_state_change.assert_not_called()
    await snooz.assert_command_unexpected_error(
        device, turn_on(volume=33, duration=timedelta(seconds=13))
    )
    assert device.is_connected
    assert device.state.volume != 33

    # shouldn't trigger a disconnect
    assert on_connection_change.mock_calls == [
        call(SnoozConnectionStatus.CONNECTING),
        call(SnoozConnectionStatus.CONNECTED),
    ]


@pytest.mark.asyncio
async def test_disconnect_before_ready_then_reconnects(
    mocker: MockerFixture, snooz: SnoozTestFixture
) -> None:
    mock_authenticate = mocker.patch(
        "pysnooz.device.SnoozDeviceApi.async_authenticate_connection",
        autospec=True,
    )

    def trigger_disconnect_once(*args, **kwargs):
        snooz.trigger_disconnect(device)
        mock_authenticate.side_effect = None

    mock_authenticate.side_effect = trigger_disconnect_once

    on_connection_change = mocker.stub()
    on_state_change = mocker.stub()

    device = snooz.create_device()
    device.events.on_connection_status_change += on_connection_change
    device.events.on_state_change += on_state_change

    await snooz.assert_command_success(device, turn_on(volume=26))
    assert on_connection_change.mock_calls == (
        [
            call(SnoozConnectionStatus.CONNECTING),
            call(SnoozConnectionStatus.DISCONNECTED),
            call(SnoozConnectionStatus.CONNECTING),
            call(SnoozConnectionStatus.CONNECTED),
        ]
    )
    assert device.is_connected
    assert device.state.on
    assert device.state.volume == 26
    on_state_change.assert_called_with(SnoozDeviceState(on=True, volume=26))


@pytest.mark.asyncio
async def test_missing_characteristic_during_connection(
    mocker: MockerFixture, snooz: SnoozTestFixture
) -> None:
    original_get_char = CharacteristicReference.get
    mock_get_char = mocker.patch(
        "pysnooz.api.CharacteristicReference.get",
        autospec=True,
    )
    mock_clear_cache = mocker.patch(
        "pysnooz.testing.MockSnoozClient.clear_cache", autospec=True
    )
    mock_discconect = mocker.patch(
        "pysnooz.testing.MockSnoozClient.disconnect", autospec=True
    )

    missing_count = 0
    times_to_be_missing = 2

    def get_missing_char(ref: CharacteristicReference, client: BleakClient) -> None:
        nonlocal missing_count, times_to_be_missing
        if not ref.required or missing_count >= times_to_be_missing:
            return original_get_char(ref, client)
        missing_count = missing_count + 1
        raise MissingCharacteristicError(ref.uuid)

    mock_get_char.side_effect = get_missing_char

    on_connection_change = mocker.stub()
    on_state_change = mocker.stub()

    device = snooz.create_device()

    device.events.on_connection_status_change += on_connection_change
    device.events.on_state_change += on_state_change

    await snooz.assert_command_success(device, turn_on(volume=26))
    assert on_connection_change.mock_calls == (
        [
            call(SnoozConnectionStatus.CONNECTING),
            *[
                call(SnoozConnectionStatus.DISCONNECTED),
                call(SnoozConnectionStatus.CONNECTING),
            ]
            * times_to_be_missing,
            call(SnoozConnectionStatus.CONNECTED),
        ]
    )
    assert mock_clear_cache.call_count == times_to_be_missing
    assert mock_discconect.call_count == times_to_be_missing
    assert device.is_connected
    assert device.state.on
    assert device.state.volume == 26
    on_state_change.assert_called_with(SnoozDeviceState(on=True, volume=26))


@pytest.mark.asyncio
async def test_manual_disconnect_before_ready(
    mocker: MockerFixture, snooz: SnoozTestFixture
) -> None:
    mock_authenticate = mocker.patch(
        "pysnooz.device.SnoozDeviceApi.async_authenticate_connection",
        autospec=True,
    )

    on_connection_change = mocker.stub()
    on_state_change = mocker.stub()

    device = snooz.create_device()
    device.events.on_connection_status_change += on_connection_change
    device.events.on_state_change += on_state_change

    async def trigger_manual_disconnect(*args, **kwargs):
        await device.async_disconnect()

    mock_authenticate.side_effect = trigger_manual_disconnect

    await snooz.assert_command_cancelled(device, turn_on(volume=26))

    # the device should be disconnected without any reconnection attempts
    assert on_connection_change.mock_calls == [
        call(SnoozConnectionStatus.CONNECTING),
        call(SnoozConnectionStatus.DISCONNECTED),
    ]

    await asyncio.sleep(0.1)
    assert not device.is_connected
    on_state_change.assert_not_called()


@pytest.mark.asyncio
async def test_disconnect_while_reconnecting_before_ready(
    mocker: MockerFixture, snooz: SnoozTestFixture
) -> None:
    mock_authenticate = mocker.patch(
        "pysnooz.device.SnoozDeviceApi.async_authenticate_connection",
        autospec=True,
    )

    def trigger_disconnect_twice(*args, **kwargs):
        snooz.trigger_disconnect(device)

        if mock_authenticate.call_count >= 2:
            mock_authenticate.side_effect = None

    mock_authenticate.side_effect = trigger_disconnect_twice

    on_connection_change = mocker.stub()
    on_state_change = mocker.stub()

    device = snooz.create_device()
    device.events.on_connection_status_change += on_connection_change
    device.events.on_state_change += on_state_change

    await snooz.assert_command_success(device, turn_on(volume=26))
    assert on_connection_change.mock_calls == (
        [
            *[
                call(SnoozConnectionStatus.CONNECTING),
                call(SnoozConnectionStatus.DISCONNECTED),
            ]
            * 2,
            call(SnoozConnectionStatus.CONNECTING),
            call(SnoozConnectionStatus.CONNECTED),
        ]
    )
    await asyncio.sleep(0.1)
    assert device.is_connected
    assert device.state.on
    assert device.state.volume == 26
    on_state_change.assert_called_with(SnoozDeviceState(on=True, volume=26))


@pytest.mark.asyncio
async def test_device_disconnects_during_transition(
    mocker: MockerFixture, snooz: SnoozTestFixture, mock_sleep: None
) -> None:
    device = snooz.create_device()

    disconnect_every = 3
    total_set_volume_calls = 0

    real_async_set_volume = SnoozDeviceApi.async_set_volume

    async def disconnect_occasionally(api: SnoozDeviceApi, volume: int) -> None:
        nonlocal total_set_volume_calls
        if total_set_volume_calls % disconnect_every == 0:
            snooz.trigger_disconnect(device)
        else:
            await real_async_set_volume(api, volume)

        total_set_volume_calls += 1

    mocker.patch.object(SnoozDeviceApi, "async_set_volume", new=disconnect_occasionally)

    await snooz.assert_command_success(
        device, turn_on(volume=56, duration=timedelta(seconds=30))
    )
    await asyncio.sleep(0.1)
    assert device.is_connected
    assert device.state.on
    assert device.state.volume == 56


@pytest.mark.asyncio
async def test_user_disconnects_during_transition(
    mocker: MockerFixture, snooz: SnoozTestFixture, mock_sleep: None
) -> None:
    device = snooz.create_device()

    disconnect_after = 6
    total_set_volume_calls = 0

    real_async_set_volume = SnoozDeviceApi.async_set_volume

    async def user_disconnects_eventually(api: SnoozDeviceApi, volume: int) -> None:
        nonlocal total_set_volume_calls
        if total_set_volume_calls == disconnect_after:
            await device.async_disconnect()
        else:
            await real_async_set_volume(api, volume)

        total_set_volume_calls += 1

    mocker.patch.object(
        SnoozDeviceApi, "async_set_volume", new=user_disconnects_eventually
    )

    await snooz.assert_command_cancelled(
        device, turn_on(volume=56, duration=timedelta(seconds=30))
    )
    await asyncio.sleep(0.1)
    assert not device.is_connected
    assert device.state.volume != 56


@pytest.mark.asyncio
async def test_device_unavailable_during_transition(
    mocker: MockerFixture, snooz: SnoozTestFixture, mock_sleep: None
) -> None:
    device = snooz.create_device()

    disconnect_after = 4
    total_set_volume_calls = 0

    real_async_set_volume = SnoozDeviceApi.async_set_volume

    async def device_becomes_unavailable(api: SnoozDeviceApi, volume: int) -> None:
        nonlocal total_set_volume_calls
        if total_set_volume_calls == disconnect_after:
            snooz.mock_connection_fails()
            snooz.trigger_disconnect(device)
        else:
            await real_async_set_volume(api, volume)

        total_set_volume_calls += 1

    mocker.patch.object(SnoozDeviceApi, "async_set_volume", device_becomes_unavailable)

    await snooz.assert_command_device_unavailable(
        device, turn_on(volume=68, duration=timedelta(seconds=30))
    )
    await asyncio.sleep(0.1)
    assert not device.is_connected
    assert device.state.volume != 68


@pytest.mark.asyncio
async def test_manual_disconnect_during_transition(
    mocker: MockerFixture, snooz: SnoozTestFixture, mock_sleep: None
) -> None:
    on_connection_change = mocker.stub()

    device = snooz.create_device()
    device.events.on_connection_status_change += on_connection_change

    disconnect_after = 4
    total_set_volume_calls = 0

    real_async_set_volume = SnoozDeviceApi.async_set_volume

    async def disconnects_manually(api: SnoozDeviceApi, volume: int) -> None:
        nonlocal total_set_volume_calls
        if total_set_volume_calls == disconnect_after:
            await device.async_disconnect()
        else:
            await real_async_set_volume(api, volume)

        total_set_volume_calls += 1

    mocker.patch.object(SnoozDeviceApi, "async_set_volume", disconnects_manually)

    await snooz.assert_command_cancelled(
        device, turn_on(volume=68, duration=timedelta(seconds=30))
    )
    assert not device.is_connected
    assert device.state.volume != 68

    # the device should be disconnected without any reconnection attempts
    assert on_connection_change.mock_calls == [
        call(SnoozConnectionStatus.CONNECTING),
        call(SnoozConnectionStatus.CONNECTED),
        call(SnoozConnectionStatus.DISCONNECTED),
    ]


@pytest.mark.asyncio
async def test_new_commands_cancel_existing(snooz: SnoozTestFixture) -> None:
    device = snooz.create_device()

    await asyncio.gather(
        snooz.assert_command_cancelled(device, turn_on()),
        snooz.assert_command_success(device, set_volume(99)),
    )

    await asyncio.sleep(0.1)
    assert device.state.volume == 99
