# mypy: warn_unreachable=False
import asyncio
import re
from asyncio import AbstractEventLoop
from datetime import timedelta
from unittest.mock import MagicMock, call

import pytest
from bleak.backends.device import BLEDevice
from pytest_mock import MockerFixture

from pysnooz.api import SnoozDeviceApi
from pysnooz.commands import (
    SnoozCommandData,
    SnoozCommandResultStatus,
    set_volume,
    turn_off,
    turn_on,
)
from pysnooz.device import (
    DEVICE_UNAVAILABLE_EXCEPTIONS,
    MAX_RECONNECTION_ATTEMPTS,
    SnoozConnectionStatus,
    SnoozDevice,
    SnoozDeviceState,
)
from tests.mock import MockSnoozClient


class SnoozTestFixture:
    def __init__(
        self,
        ble_device: BLEDevice,
        token: str,
        loop: AbstractEventLoop,
        mock_client: MockSnoozClient,
        mock_connect: MagicMock,
    ):
        self.ble_device = ble_device
        self.token = token
        self.loop = loop
        self.mock_client = mock_client
        self.mock_connect = mock_connect

    def create_device(self) -> SnoozDevice:
        self.mock_client.reset_mock(initial_state=True)
        return SnoozDevice(self.ble_device, self.token, self.loop)

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
def snooz(mocker: MockerFixture, event_loop: AbstractEventLoop) -> SnoozTestFixture:
    device = BLEDevice("AA:BB:CC:DD:EE:FF", "Snooz-EEFF")
    token = "AABBCCDDEEFF"
    mock_client = MockSnoozClient(device)

    def get_connected_client(*args, **kwargs):
        mock_client.reset_mock()
        return mock_client

    mock_connect = mocker.patch("pysnooz.device.establish_connection", autospec=True)
    mock_connect.side_effect = get_connected_client

    return SnoozTestFixture(
        ble_device=device,
        token=token,
        loop=event_loop,
        mock_client=mock_client,
        mock_connect=mock_connect,
    )


def test_display_name(snooz: SnoozTestFixture) -> None:
    device = snooz.create_device()
    assert re.search(r"^Snooz [A-Z0-9]{4}$", device.display_name) is not None


@pytest.mark.asyncio
async def test_basic_commands(mocker: MockerFixture, snooz: SnoozTestFixture) -> None:
    on_connection_status_change = mocker.stub()
    on_state_change = mocker.stub()

    device = snooz.create_device()

    device.events.on_state_change += on_state_change
    device.events.on_connection_status_change += on_connection_status_change

    # events should not occur until the device is connected
    on_connection_status_change.assert_not_called()
    on_state_change.assert_not_called()

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

    await snooz.assert_command_success(device, turn_off())
    assert device.state.on is False
    on_state_change.assert_called_once_with(SnoozDeviceState(on=False, volume=25))
    on_state_change.reset_mock()

    await snooz.assert_command_success(device, set_volume(36))
    assert device.state.volume == 36
    on_state_change.assert_called_once_with(SnoozDeviceState(on=False, volume=36))
    on_state_change.reset_mock()

    # no other status changes should have occurred
    on_connection_status_change.assert_not_called()


@pytest.mark.asyncio
async def test_auto_reconnect(mocker: MockerFixture, snooz: SnoozTestFixture) -> None:
    on_connection_change = mocker.stub()

    device = snooz.create_device()

    device.events.on_connection_status_change += on_connection_change

    await snooz.assert_command_success(device, turn_on())
    assert device.is_connected

    snooz.mock_client.trigger_disconnect()
    assert not device.is_connected
    # wait for the reconnection task to complete
    await asyncio.sleep(0.1)

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

    snooz.mock_client.trigger_disconnect()
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

    device = snooz.create_device()

    await snooz.assert_command_success(device, turn_on())
    assert device.is_connected

    on_connection_change = mocker.stub()
    device.events.on_connection_status_change += on_connection_change

    await device.async_disconnect()
    assert not device.is_connected

    # shouldn't try to reconnect
    assert call(SnoozConnectionStatus.CONNECTING) not in on_connection_change.mock_calls
    assert call(SnoozConnectionStatus.CONNECTED) not in on_connection_change.mock_calls


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
async def test_disconnect_before_ready(
    mocker: MockerFixture, snooz: SnoozTestFixture
) -> None:
    async def disconnects(*args, **kwargs):
        snooz.mock_client.trigger_disconnect()

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
        snooz.mock_client.trigger_disconnect()
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
    on_state_change.assert_called_with(SnoozDeviceState(True, 26))


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
        snooz.mock_client.trigger_disconnect()

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
    on_state_change.assert_called_with(SnoozDeviceState(True, 26))


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
            snooz.mock_client.trigger_disconnect()
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
            snooz.mock_client.trigger_disconnect()
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
    await asyncio.sleep(0.1)
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
