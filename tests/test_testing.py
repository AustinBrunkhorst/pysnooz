# mypy: warn_unreachable=False

import pytest
from bleak import BLEDevice
from pytest_mock import MockerFixture

from pysnooz.api import Command
from pysnooz.commands import SnoozCommandResultStatus, set_volume, turn_on
from pysnooz.const import (
    READ_COMMAND_CHARACTERISTIC,
    READ_STATE_CHARACTERISTIC,
    WRITE_STATE_CHARACTERISTIC,
)
from pysnooz.device import SnoozConnectionStatus
from pysnooz.model import (
    SnoozAdvertisementData,
    SnoozDeviceModel,
    SnoozDeviceState,
    SnoozFirmwareVersion,
)
from pysnooz.testing import MockSnoozClient, MockSnoozDevice

from . import SUPPORTED_MODELS

TEST_BLE_DEVICE = BLEDevice("00:00:00:00:AB:CD", "Snooz-ABCD", [], 0)


@pytest.mark.asyncio
@pytest.mark.parametrize("model", SUPPORTED_MODELS)
async def test_mock_client(mocker: MockerFixture, model: SnoozDeviceModel) -> None:
    on_disconnect = mocker.stub()
    client = MockSnoozClient(
        TEST_BLE_DEVICE,
        model,
        on_disconnect,
    )
    assert client.is_connected is True

    await client.disconnect()
    assert client.is_connected is False
    on_disconnect.assert_called_once()
    on_disconnect.reset_mock()

    await client.connect()
    assert client.is_connected is True

    read_state_char = client.services.get_characteristic(READ_STATE_CHARACTERISTIC)
    assert read_state_char is not None
    write_state_char = (await client.get_services()).get_characteristic(
        WRITE_STATE_CHARACTERISTIC
    )
    assert read_state_char is not None
    read_command_char = client.services.get_characteristic(READ_COMMAND_CHARACTERISTIC)
    assert read_command_char is not None

    # should raise on unknown characteristics
    with pytest.raises(Exception):
        client.services.get_characteristic("00000000-0000-0000-0000-00000000abcd")

    state_callback = mocker.stub()

    # should raise on unknown notification characteristics
    with pytest.raises(Exception):
        await client.start_notify(write_state_char, mocker.stub())

    await client.start_notify(read_state_char, state_callback)
    await client.write_gatt_char(write_state_char, bytes([Command.MOTOR_SPEED, 15]))

    state_callback.assert_called_once()
    # when not authenticated, the state shouldn't be updated
    assert 15 not in state_callback.call_args[0][1]
    state_callback.reset_mock()

    await client.write_gatt_char(
        write_state_char,
        bytes([Command.PASSWORD, 0x0A, 0x0B, 0x0A, 0x0B, 0x0A, 0x0B, 0x0A, 0x0B]),
    )

    # should raise on the wrong write characteristic
    with pytest.raises(Exception):
        await client.write_gatt_char(read_state_char, bytes([]))

    # should raise on unknown command
    with pytest.raises(Exception):
        await client.write_gatt_char(write_state_char, bytes([0xFF]))

    await client.write_gatt_char(write_state_char, bytes([Command.MOTOR_SPEED, 15]))
    state_callback.assert_called_once()
    assert 15 in state_callback.call_args[0][1]
    state_callback.reset_mock()

    await client.stop_notify(read_state_char)
    await client.write_gatt_char(write_state_char, bytes([Command.MOTOR_SPEED, 15]))
    state_callback.assert_not_called()

    if model == SnoozDeviceModel.BREEZ:
        on_command_response = mocker.stub()
        await client.start_notify(read_command_char, on_command_response)
        client.trigger_temperature(55.6)
        on_command_response.assert_called_once()
        on_command_response.reset_mock()
        await client.stop_notify(read_command_char)
        client.trigger_temperature(77)
        on_command_response.assert_not_called()

    client.trigger_disconnect()
    assert client.is_connected is False
    on_disconnect.assert_called_once()
    on_disconnect.reset_mock()

    # doesn't disconnect when already disconnected
    client.trigger_disconnect()
    on_disconnect.assert_not_called()

    client.reset_mock()
    assert client.is_connected is True

    client.reset_mock(initial_state=True)
    assert client.is_connected is True


@pytest.mark.asyncio
@pytest.mark.parametrize("model", SUPPORTED_MODELS)
async def test_mock_device(mocker: MockerFixture, model: SnoozDeviceModel) -> None:
    adv_data = SnoozAdvertisementData(
        model,
        SnoozFirmwareVersion.V2
        if model == SnoozDeviceModel.ORIGINAL
        else SnoozFirmwareVersion.V6,
        "deadbeefdeadbeef",
    )
    device = MockSnoozDevice(TEST_BLE_DEVICE, adv_data)

    assert device.is_connected is False

    # should do nothing
    device.trigger_disconnect()
    device.trigger_state(SnoozDeviceState(on=True, volume=32))
    device.trigger_temperature(72.5)

    on_state_change = mocker.stub()
    device.subscribe_to_state_change(on_state_change)

    result = await device.async_execute_command(turn_on())
    assert result.status == SnoozCommandResultStatus.SUCCESSFUL
    assert device.is_connected is True

    device.trigger_state(SnoozDeviceState(on=True, volume=32))

    on_state_change.assert_called()
    assert device.state.on is True
    assert device.state.volume == 32
    on_state_change.reset_mock()

    device.trigger_state(SnoozDeviceState(on=False, volume=45))
    on_state_change.assert_called()
    assert device.state.on is False
    assert device.state.volume == 45
    on_state_change.reset_mock()

    info = await device.async_get_info()
    assert info is not None
    on_state_change.assert_not_called()

    if model == SnoozDeviceModel.BREEZ:
        device.trigger_temperature(72.5)
        assert device.state.temperature == 72.5
        on_state_change.assert_called()

    await device.async_disconnect()
    assert device.is_connected is False

    result = await device.async_execute_command(set_volume(55))
    assert result.status == SnoozCommandResultStatus.SUCCESSFUL
    assert device.is_connected is True
    assert device.state.volume == 55

    device.trigger_disconnect()
    assert device.is_connected is False
    assert device.connection_status == SnoozConnectionStatus.DISCONNECTED
