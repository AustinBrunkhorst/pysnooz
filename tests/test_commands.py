import time
from asyncio import AbstractEventLoop, CancelledError, gather, sleep
from datetime import datetime, timedelta
from typing import Awaitable, Callable, Coroutine
from unittest.mock import ANY, MagicMock, call

import pytest
from pytest_mock import MockerFixture

from pysnooz import get_device_info
from pysnooz.api import MIN_DEVICE_VOLUME, MIN_FAN_SPEED, SnoozDeviceApi
from pysnooz.commands import (
    CommandProcessorState,
    SnoozCommandData,
    SnoozCommandResultStatus,
    create_command_processor,
    disable_night_mode,
    enable_night_mode,
    set_auto_temp_enabled,
    set_fan_speed,
    set_light_brightness,
    set_temp_target,
    set_volume,
    turn_fan_off,
    turn_fan_on,
    turn_light_off,
    turn_light_on,
    turn_off,
    turn_on,
)
from pysnooz.model import SnoozDeviceState

AssertCommandTest = Callable[[MagicMock, SnoozCommandData], Awaitable[None]]


@pytest.fixture
def assert_command_success(
    event_loop: AbstractEventLoop,
) -> Callable[[MagicMock, SnoozCommandData], Awaitable[None]]:
    async def _factory(mock_api: MagicMock, data: SnoozCommandData) -> None:
        command = create_command_processor(event_loop, datetime.now(), data)
        assert command.state == CommandProcessorState.IDLE

        await command.async_execute(mock_api)

        result = await command.result
        assert result.status == SnoozCommandResultStatus.SUCCESSFUL

        assert command.state == CommandProcessorState.COMPLETE

    return _factory


@pytest.mark.asyncio
async def test_turn_on(
    mocker: MockerFixture, assert_command_success: AssertCommandTest
) -> None:
    mock_api = mocker.MagicMock(spec=SnoozDeviceApi)

    await assert_command_success(mock_api, turn_on())
    mock_api.async_set_power.assert_called_once_with(True)
    mock_api.async_set_volume.assert_not_called()

    mock_api.reset_mock()

    await assert_command_success(mock_api, turn_on(volume=30))
    mock_api.async_set_power.assert_called_once_with(True)
    mock_api.async_set_volume.assert_called_once_with(30)


@pytest.mark.asyncio
async def test_turn_off(
    mocker: MockerFixture,
    assert_command_success: AssertCommandTest,
) -> None:
    mock_api = mocker.MagicMock(spec=SnoozDeviceApi)

    await assert_command_success(mock_api, turn_off())
    mock_api.async_set_power.assert_called_once_with(False)
    mock_api.async_set_volume.assert_not_called()


@pytest.mark.asyncio
async def test_turn_light_on(
    mocker: MockerFixture, assert_command_success: AssertCommandTest
) -> None:
    mock_api = mocker.MagicMock(spec=SnoozDeviceApi)

    await assert_command_success(mock_api, turn_light_on())
    mock_api.async_set_light_brightness.assert_called_once_with(100)

    mock_api.reset_mock()

    await assert_command_success(mock_api, turn_light_on(brightness=30))
    mock_api.async_set_light_brightness.assert_called_once_with(30)


@pytest.mark.asyncio
async def test_set_light_brightness(
    mocker: MockerFixture, assert_command_success: AssertCommandTest
) -> None:
    mock_api = mocker.MagicMock(spec=SnoozDeviceApi)

    await assert_command_success(mock_api, set_light_brightness(5))
    mock_api.async_set_light_brightness.assert_called_once_with(5)


@pytest.mark.asyncio
async def test_turn_light_off(
    mocker: MockerFixture,
    assert_command_success: AssertCommandTest,
) -> None:
    mock_api = mocker.MagicMock(spec=SnoozDeviceApi)

    await assert_command_success(mock_api, turn_light_off())
    mock_api.async_set_light_brightness.assert_called_once_with(0)


@pytest.mark.asyncio
async def test_enable_night_mode(
    mocker: MockerFixture,
    assert_command_success: AssertCommandTest,
) -> None:
    mock_api = mocker.MagicMock(spec=SnoozDeviceApi)

    await assert_command_success(mock_api, enable_night_mode())
    mock_api.async_set_night_mode_enabled.assert_called_once_with(True, ANY)

    mock_api.reset_mock()
    await assert_command_success(mock_api, enable_night_mode(32))
    mock_api.async_set_night_mode_enabled.assert_called_once_with(True, 32)


@pytest.mark.asyncio
async def test_disable_night_mode(
    mocker: MockerFixture,
    assert_command_success: AssertCommandTest,
) -> None:
    mock_api = mocker.MagicMock(spec=SnoozDeviceApi)

    await assert_command_success(mock_api, disable_night_mode())
    mock_api.async_set_night_mode_enabled.assert_called_once_with(False, ANY)


@pytest.mark.asyncio
async def test_set_volume(
    mocker: MockerFixture,
    assert_command_success: AssertCommandTest,
) -> None:
    mock_api = mocker.MagicMock(spec=SnoozDeviceApi)

    await assert_command_success(mock_api, set_volume(volume=12))
    mock_api.async_set_volume.assert_called_once_with(12)
    mock_api.async_set_power.assert_not_called()


@pytest.mark.asyncio
async def test_turn_fan_on(
    mocker: MockerFixture, assert_command_success: AssertCommandTest
) -> None:
    mock_api = mocker.MagicMock(spec=SnoozDeviceApi)

    await assert_command_success(mock_api, turn_fan_on())
    mock_api.async_set_fan_power.assert_called_once_with(True)
    mock_api.async_set_fan_speed.assert_not_called()

    mock_api.reset_mock()

    await assert_command_success(mock_api, turn_fan_on(speed=30))
    mock_api.async_set_fan_power.assert_called_once_with(True)
    mock_api.async_set_fan_speed.assert_called_once_with(30)


@pytest.mark.asyncio
async def test_turn_fan_off(
    mocker: MockerFixture,
    assert_command_success: AssertCommandTest,
) -> None:
    mock_api = mocker.MagicMock(spec=SnoozDeviceApi)

    await assert_command_success(mock_api, turn_fan_off())
    mock_api.async_set_fan_power.assert_called_once_with(False)
    mock_api.async_set_fan_speed.assert_not_called()


@pytest.mark.asyncio
async def test_set_fan_speed(
    mocker: MockerFixture,
    assert_command_success: AssertCommandTest,
) -> None:
    mock_api = mocker.MagicMock(spec=SnoozDeviceApi)

    await assert_command_success(mock_api, set_fan_speed(speed=12))
    mock_api.async_set_fan_speed.assert_called_once_with(12)
    mock_api.async_set_fan_power.assert_not_called()


@pytest.mark.asyncio
async def test_set_auto_temp_enabled(
    mocker: MockerFixture,
    assert_command_success: AssertCommandTest,
) -> None:
    mock_api = mocker.MagicMock(spec=SnoozDeviceApi)

    await assert_command_success(mock_api, set_auto_temp_enabled(True))
    mock_api.async_set_auto_temp_enabled.assert_called_once_with(True)

    mock_api.reset_mock()

    await assert_command_success(mock_api, set_auto_temp_enabled(False))
    mock_api.async_set_auto_temp_enabled.assert_called_once_with(False)


@pytest.mark.asyncio
async def test_set_temp_target(
    mocker: MockerFixture,
    assert_command_success: AssertCommandTest,
) -> None:
    mock_api = mocker.MagicMock(spec=SnoozDeviceApi)

    await assert_command_success(mock_api, set_temp_target(55))
    mock_api.async_set_auto_temp_threshold.assert_called_once_with(55)


@pytest.mark.asyncio
async def test_get_info(
    mocker: MockerFixture,
    assert_command_success: AssertCommandTest,
) -> None:
    mock_api = mocker.MagicMock(spec=SnoozDeviceApi)

    await assert_command_success(mock_api, get_device_info())
    mock_api.async_get_info.assert_called_once()


@pytest.mark.asyncio
async def test_turn_on_transition(
    mocker: MockerFixture,
    assert_command_success: AssertCommandTest,
    mock_sleep: None,
) -> None:
    mock_api = mocker.MagicMock(spec=SnoozDeviceApi)

    min_volume = 10
    initial_volume = 100
    mock_api.async_read_state.side_effect = [
        SnoozDeviceState(on=False, volume=initial_volume)
    ]

    await assert_command_success(mock_api, turn_on(duration=timedelta(seconds=10)))

    mock_api.assert_has_calls(
        [
            # should set min volume before turning on
            call.async_set_volume(min_volume),
            # should turn on since it was off
            call.async_set_power(True),
        ]
    )
    # first call to set volume should be min volume
    assert mock_api.async_set_volume.mock_calls[0] == call(min_volume)
    # last call should set the volume to initial device state
    assert mock_api.mock_calls[-1] == call.async_set_volume(initial_volume)

    mock_api.reset_mock()

    mock_api.async_read_state.side_effect = [SnoozDeviceState(on=True, volume=30)]

    target_volume = 13
    await assert_command_success(
        mock_api,
        turn_on(volume=target_volume, duration=timedelta(seconds=1)),
    )

    # when the initial power state is the same as the target, avoid unnecessary calls
    mock_api.async_set_power.assert_not_called()

    # last call should set the volume to target state
    assert mock_api.mock_calls[-1] == call.async_set_volume(target_volume)


@pytest.mark.asyncio
async def test_turn_fan_on_transition(
    mocker: MockerFixture,
    assert_command_success: AssertCommandTest,
    mock_sleep: None,
) -> None:
    mock_api = mocker.MagicMock(spec=SnoozDeviceApi)

    min_fan_speed = 10
    initial_speed = 100
    mock_api.async_read_state.side_effect = [
        SnoozDeviceState(fan_on=False, fan_speed=initial_speed)
    ]

    await assert_command_success(mock_api, turn_fan_on(duration=timedelta(seconds=10)))

    mock_api.assert_has_calls(
        [
            # should set min speed before turning on
            call.async_set_fan_speed(min_fan_speed),
            # should turn on since it was off
            call.async_set_fan_power(True),
        ]
    )
    # first call to set speed should be min speed
    assert mock_api.async_set_fan_speed.mock_calls[0] == call(min_fan_speed)
    # last call should set the speed to initial device state
    assert mock_api.mock_calls[-1] == call.async_set_fan_speed(initial_speed)

    mock_api.reset_mock()

    mock_api.async_read_state.side_effect = [
        SnoozDeviceState(fan_on=True, fan_speed=30)
    ]

    target_speed = 13
    await assert_command_success(
        mock_api,
        turn_fan_on(speed=target_speed, duration=timedelta(seconds=1)),
    )

    # when the initial power state is the same as the target, avoid unnecessary calls
    mock_api.async_set_fan_power.assert_not_called()

    # last call should set the speed to target state
    assert mock_api.mock_calls[-1] == call.async_set_fan_speed(target_speed)


AssertCommandSuccess = Callable[[MagicMock, SnoozCommandData], Coroutine]


@pytest.mark.asyncio
async def test_turn_off_transition(
    mocker: MockerFixture,
    assert_command_success: AssertCommandTest,
    mock_sleep: None,
) -> None:
    mock_api = mocker.MagicMock(spec=SnoozDeviceApi)

    initial_volume = 36
    mock_api.async_read_state.side_effect = [
        SnoozDeviceState(on=True, volume=initial_volume)
    ]

    await assert_command_success(mock_api, turn_off(duration=timedelta(seconds=10)))

    mock_api.assert_has_calls(
        [
            # should set min volume before turning off
            call.async_set_volume(MIN_DEVICE_VOLUME),
            call.async_set_power(False),
            # reset the volume to initial state -
            # this supports the ability to transition off <-> on
            # without the need to supply a volume
            call.async_set_volume(initial_volume),
        ]
    )
    # last call should be setting initial volume
    assert mock_api.mock_calls[-1] == call.async_set_volume(initial_volume)


@pytest.mark.asyncio
async def test_turn_fan_off_transition(
    mocker: MockerFixture,
    assert_command_success: AssertCommandTest,
    mock_sleep: None,
) -> None:
    mock_api = mocker.MagicMock(spec=SnoozDeviceApi)

    initial_speed = 36
    mock_api.async_read_state.side_effect = [
        SnoozDeviceState(fan_on=True, fan_speed=initial_speed)
    ]

    await assert_command_success(mock_api, turn_fan_off(duration=timedelta(seconds=10)))

    mock_api.assert_has_calls(
        [
            # should set min speed before turning off
            call.async_set_fan_speed(MIN_FAN_SPEED),
            call.async_set_fan_power(False),
            # reset the speed to initial state -
            # this supports the ability to transition off <-> on
            # without the need to supply a speed
            call.async_set_fan_speed(initial_speed),
        ]
    )
    # last call should be setting initial speed
    assert mock_api.mock_calls[-1] == call.async_set_fan_speed(initial_speed)


@pytest.mark.asyncio
async def test_cancel_before_execution(
    mocker: MockerFixture, event_loop: AbstractEventLoop
) -> None:
    mock_api = mocker.MagicMock(spec=SnoozDeviceApi)

    command = create_command_processor(event_loop, datetime.now(), turn_on())
    command.cancel()

    result = await command.result
    assert command.state == CommandProcessorState.COMPLETE
    assert result.status == SnoozCommandResultStatus.CANCELLED

    assert mock_api.call_count == 0


@pytest.mark.asyncio
async def test_cancel_before_execution_awaited(
    mocker: MockerFixture, event_loop: AbstractEventLoop
) -> None:
    mock_api = mocker.MagicMock(spec=SnoozDeviceApi)

    command = create_command_processor(event_loop, datetime.now(), turn_on())

    execute_task = command.async_execute(mock_api)

    command.cancel()

    await execute_task

    result = await command.result
    assert command.state == CommandProcessorState.COMPLETE
    assert result.status == SnoozCommandResultStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_during_execution(
    mocker: MockerFixture, event_loop: AbstractEventLoop
) -> None:
    mock_api = mocker.MagicMock(spec=SnoozDeviceApi)

    command = create_command_processor(event_loop, datetime.now(), turn_on())

    async def cancel_soon():
        await sleep(0.1)
        command.cancel()

    async def takes_a_while(on):
        await sleep(0.5)

    mock_api.async_set_power.side_effect = takes_a_while

    # cancel command before it completes
    await gather(cancel_soon(), command.async_execute(mock_api))

    result = await command.result
    assert command.state == CommandProcessorState.COMPLETE
    assert result.status == SnoozCommandResultStatus.CANCELLED
    mock_api.async_set_power.assert_called_once_with(True)


@pytest.mark.asyncio
async def test_raise_on_cancel(
    mocker: MockerFixture, event_loop: AbstractEventLoop
) -> None:
    mock_api = mocker.MagicMock(spec=SnoozDeviceApi)

    command = create_command_processor(event_loop, datetime.now(), turn_on())

    async def cancel_soon():
        await sleep(0.1)
        command.cancel()

    async def takes_a_while(on):
        await sleep(0.5)

    mock_api.async_set_power.side_effect = takes_a_while

    # cancel command before it completes and raise on cancel
    with pytest.raises(CancelledError):
        await gather(
            cancel_soon(), command.async_execute(mock_api, raise_on_cancel=True)
        )

    result = await command.result
    assert command.state == CommandProcessorState.COMPLETE
    assert result.status == SnoozCommandResultStatus.CANCELLED
    mock_api.async_set_power.assert_called_once_with(True)


@pytest.mark.asyncio
async def test_cancel_during_transition(
    mocker: MockerFixture, event_loop: AbstractEventLoop, mock_sleep: None
) -> None:
    mock_api = mocker.MagicMock(spec=SnoozDeviceApi)

    target_volume = 100
    cancel_at_volume = target_volume / 2
    mock_api.async_read_state.side_effect = [
        SnoozDeviceState(on=False, volume=target_volume)
    ]

    command = create_command_processor(
        event_loop, datetime.now(), turn_on(duration=timedelta(seconds=10))
    )

    def cancels_midway_through(volume):
        if volume >= cancel_at_volume:
            command.cancel()

    mock_api.async_set_volume.side_effect = cancels_midway_through

    await command.async_execute(mock_api)

    result = await command.result
    assert command.state == CommandProcessorState.COMPLETE
    assert result.status == SnoozCommandResultStatus.CANCELLED

    # the target volume shouldn't be set
    assert call.async_set_volume(target_volume) not in mock_api.mock_calls


@pytest.mark.asyncio
async def test_device_unavailable(event_loop: AbstractEventLoop) -> None:
    command = create_command_processor(event_loop, datetime.now(), turn_on())
    command.on_device_unavailable()

    result = await command.result
    assert command.state == CommandProcessorState.COMPLETE
    assert result.status == SnoozCommandResultStatus.DEVICE_UNAVAILABLE


@pytest.mark.asyncio
async def test_device_unavailable_during_transition(
    mocker: MockerFixture, event_loop: AbstractEventLoop, mock_sleep: None
) -> None:
    mock_api = mocker.MagicMock(spec=SnoozDeviceApi)

    target_volume = 100
    unavailable_at_volume = target_volume / 2
    mock_api.async_read_state.side_effect = [
        SnoozDeviceState(on=False, volume=target_volume)
    ]

    command = create_command_processor(
        event_loop, datetime.now(), turn_on(duration=timedelta(seconds=10))
    )

    def becomes_unavailable(volume):
        if volume >= unavailable_at_volume:
            command.on_device_unavailable()

    mock_api.async_set_volume.side_effect = becomes_unavailable

    await command.async_execute(mock_api)

    result = await command.result
    assert command.state == CommandProcessorState.COMPLETE
    assert result.status == SnoozCommandResultStatus.DEVICE_UNAVAILABLE

    # the target volume shouldn't be set
    assert call.async_set_volume(target_volume) not in mock_api.mock_calls


@pytest.mark.asyncio
async def test_device_exception_during_transition(
    mocker: MockerFixture, event_loop: AbstractEventLoop, mock_sleep: None
) -> None:
    mock_api = mocker.MagicMock(spec=SnoozDeviceApi)

    target_volume = 100
    exception_at_volume = target_volume / 2
    mock_api.async_read_state.side_effect = [
        SnoozDeviceState(on=False, volume=target_volume)
    ]

    command = create_command_processor(
        event_loop, datetime.now(), turn_on(duration=timedelta(seconds=10))
    )

    def reaches_unhandled_exception(volume):
        if volume >= exception_at_volume:
            command.on_unhandled_exception()

    mock_api.async_set_volume.side_effect = reaches_unhandled_exception

    await command.async_execute(mock_api)

    result = await command.result
    assert command.state == CommandProcessorState.COMPLETE
    assert result.status == SnoozCommandResultStatus.UNEXPECTED_ERROR

    # the target volume shouldn't be set
    assert call.async_set_volume(target_volume) not in mock_api.mock_calls


@pytest.mark.asyncio
async def test_transition_on_resumes_after_disconnection(
    mocker: MockerFixture, event_loop: AbstractEventLoop, mock_sleep: None
) -> None:
    mock_api = mocker.MagicMock(spec=SnoozDeviceApi)

    target_volume = 100
    disconnect_every = 3
    mock_api.async_read_state.return_value = SnoozDeviceState(
        on=False, volume=target_volume
    )

    command = create_command_processor(
        event_loop,
        datetime.now(),
        turn_on(volume=target_volume, duration=timedelta(seconds=10)),
    )

    async def disconnects_periodically(volume):
        # make sure next call to read state reflects the latest volume
        mock_api.async_read_state.return_value = SnoozDeviceState(
            on=True, volume=volume
        )
        if mock_api.async_set_volume.call_count % disconnect_every == 0:
            command.on_disconnected()

    mock_api.async_set_volume.side_effect = disconnects_periodically

    async def reconnect_until_complete():
        while command.state != CommandProcessorState.COMPLETE:
            if command.state == CommandProcessorState.IDLE:
                await command.async_execute(mock_api)
            else:
                time.sleep(0.1)

    await reconnect_until_complete()

    result = await command.result
    assert command.state == CommandProcessorState.COMPLETE
    assert result.status == SnoozCommandResultStatus.SUCCESSFUL

    # the target volume should be set last
    assert mock_api.async_set_volume.mock_calls[-1] == call.async_set_volume(
        target_volume
    )


@pytest.mark.asyncio
async def test_transition_off_resumes_after_disconnection(
    mocker: MockerFixture, event_loop: AbstractEventLoop, mock_sleep: None
) -> None:
    mock_api = mocker.MagicMock(spec=SnoozDeviceApi)

    disconnect_every = 3
    initial_volume = 100
    mock_api.async_read_state.return_value = SnoozDeviceState(
        on=True, volume=initial_volume
    )

    command = create_command_processor(
        event_loop,
        datetime.now(),
        turn_off(duration=timedelta(seconds=10)),
    )

    async def disconnects_periodically(volume):
        # make sure next call to read state reflects the latest volume
        mock_api.async_read_state.return_value = SnoozDeviceState(
            on=True, volume=volume
        )
        if mock_api.async_set_volume.call_count % disconnect_every == 0:
            command.on_disconnected()

    mock_api.async_set_volume.side_effect = disconnects_periodically

    async def reconnect_until_complete():
        while command.state != CommandProcessorState.COMPLETE:
            if command.state == CommandProcessorState.IDLE:
                await command.async_execute(mock_api)
            else:
                time.sleep(0.1)

    await reconnect_until_complete()

    result = await command.result
    assert command.state == CommandProcessorState.COMPLETE
    assert result.status == SnoozCommandResultStatus.SUCCESSFUL

    mock_api.assert_has_calls(
        [
            call.async_set_volume(MIN_DEVICE_VOLUME),
            call.async_set_power(False),
            call.async_set_volume(initial_volume),
        ]
    )


@pytest.mark.asyncio
async def test_unhandled_exception(event_loop: AbstractEventLoop) -> None:
    command = create_command_processor(event_loop, datetime.now(), turn_on())
    command.on_unhandled_exception()

    result = await command.result
    assert command.state == CommandProcessorState.COMPLETE
    assert result.status == SnoozCommandResultStatus.UNEXPECTED_ERROR


@pytest.mark.asyncio
async def test_unhandled_exception_during_execution(
    mocker: MockerFixture,
    event_loop: AbstractEventLoop,
) -> None:
    mock_api = mocker.MagicMock(spec=SnoozDeviceApi)
    mock_api.async_set_power.side_effect = Exception("Testing unhandled exception")

    command = create_command_processor(event_loop, datetime.now(), turn_on())
    await command.async_execute(mock_api)
    result = await command.result
    assert command.state == CommandProcessorState.COMPLETE
    assert result.status == SnoozCommandResultStatus.UNEXPECTED_ERROR
