from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from asyncio import AbstractEventLoop, CancelledError, Future, Lock, Task
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, IntEnum
from typing import Callable

from transitions import Machine, State

from pysnooz.api import MIN_DEVICE_VOLUME, SnoozDeviceApi
from pysnooz.const import (
    UNEXPECTED_ERROR_LOG_MESSAGE,
    SnoozDeviceInfo,
    SnoozDeviceState,
)
from pysnooz.transition import Transition

_LOGGER = logging.getLogger(__name__)


class SnoozDeviceAction(IntEnum):
    GET_DEVICE_INFO = (0,)
    ENABLE_AUTO_TEMP = 1


@dataclass
class SnoozCommandData:
    # Noise sound properties
    on: bool | None = None
    volume: int | None = None

    # duration to transition target values
    duration: timedelta | None = None

    # Breez only properties
    fan_on: bool | None = None
    fan_speed: int | None = None
    temp_target: int | None = None

    action: SnoozDeviceAction | None = None

    def __repr__(self) -> str:
        operations: list[str] = []

        if self.on is not None:
            operations += ["TurnOn"] if self.on else ["TurnOff"]

        if self.fan_on is not None:
            operations += ["TurnOnFan"] if self.fan_on else ["TurnOffFan"]

        if self.volume is not None:
            operations += [f"SetVolume({self.volume}%)"]

        if self.fan_speed is not None:
            operations += [f"SetFanSpeed({self.fan_speed}%)"]

        if self.temp_target is not None:
            operations += [f"SetTargetTemperature({self.temp_target})"]

        if self.duration is not None:
            operations += [f"transition {self.duration}"]

        if self.action is SnoozDeviceAction.GET_DEVICE_INFO:
            operations += ["GetDeviceInfo"]

        if self.action is SnoozDeviceAction.ENABLE_AUTO_TEMP:
            operations += ["EnableAutoTemp"]

        return ", ".join(operations)


def turn_on(
    volume: int | None = None, duration: timedelta | None = None
) -> SnoozCommandData:
    return SnoozCommandData(on=True, volume=volume, duration=duration)


def turn_off(duration: timedelta | None = None) -> SnoozCommandData:
    return SnoozCommandData(on=False, duration=duration)


def set_volume(volume: int) -> SnoozCommandData:
    return SnoozCommandData(volume=volume)


def get_device_info() -> SnoozCommandData:
    return SnoozCommandData(action=SnoozDeviceAction.GET_DEVICE_INFO)


# Breez only commands


def turn_fan_on(
    speed: int | None = None, duration: timedelta | None = None
) -> SnoozCommandData:
    return SnoozCommandData(fan_on=True, fan_speed=speed, duration=duration)


def turn_fan_off(duration: timedelta | None = None) -> SnoozCommandData:
    return SnoozCommandData(fan_on=False, duration=duration)


def set_fan_speed(speed: int) -> SnoozCommandData:
    return SnoozCommandData(fan_speed=speed)


def enable_auto_temp() -> SnoozCommandData:
    return SnoozCommandData(action=SnoozDeviceAction.ENABLE_AUTO_TEMP)


def set_temp_target(temp: int) -> SnoozCommandData:
    return SnoozCommandData(temp_target=temp)


class SnoozCommandResultStatus(Enum):
    SUCCESSFUL = 0
    CANCELLED = 1
    DEVICE_UNAVAILABLE = 2
    UNEXPECTED_ERROR = 3


@dataclass
class SnoozCommandResult:
    status: SnoozCommandResultStatus
    duration: timedelta
    response: SnoozDeviceInfo | None = None


class CommandProcessorState(Enum):
    IDLE = 0
    EXECUTING = 1
    COMPLETE = 2


class SnoozCommandProcessor(ABC):
    def __init__(
        self,
        loop: AbstractEventLoop,
        _: Callable[[str], str],
        command: SnoozCommandData,
        start_time: datetime,
        result: Future[SnoozCommandResult],
    ) -> None:
        self.loop = loop
        self._ = _
        self.command = command
        self.start_time = start_time
        self.last_disconnect_time: datetime | None = None
        self.result = result
        self._execute_lock = Lock()
        self._result_status = SnoozCommandResultStatus.SUCCESSFUL
        self._execution_task: Task[None] | None = None
        self._total_disconnects: int = 0

        states = [
            State(CommandProcessorState.IDLE),
            State(CommandProcessorState.EXECUTING),
            State(CommandProcessorState.COMPLETE, on_enter=self._on_complete),
        ]

        not_complete = [CommandProcessorState.IDLE, CommandProcessorState.EXECUTING]

        self._machine = Machine(states=states, initial=CommandProcessorState.IDLE)

        self._machine.add_transition(
            "start_execution",
            CommandProcessorState.IDLE,
            CommandProcessorState.EXECUTING,
            before=self._before_execution_start,
        )
        self._machine.add_transition(
            "disconnected",
            not_complete,
            CommandProcessorState.IDLE,
            before=self._on_disconnect,
        )
        self._machine.add_transition(
            "cancelled",
            not_complete,
            CommandProcessorState.COMPLETE,
            before=lambda: self._abort_with_status(SnoozCommandResultStatus.CANCELLED),
        )
        self._machine.add_transition(
            "device_unavailable",
            not_complete,
            CommandProcessorState.COMPLETE,
            before=lambda: self._abort_with_status(
                SnoozCommandResultStatus.DEVICE_UNAVAILABLE
            ),
        ),
        self._machine.add_transition(
            "unhandled_exception",
            not_complete,
            CommandProcessorState.COMPLETE,
            before=lambda: self._abort_with_status(
                SnoozCommandResultStatus.UNEXPECTED_ERROR
            ),
        )
        self._machine.add_transition(
            "execution_complete",
            CommandProcessorState.EXECUTING,
            CommandProcessorState.COMPLETE,
        )

    @property
    def state(self) -> CommandProcessorState:
        return self._machine.state

    async def async_execute(self, api: SnoozDeviceApi) -> None:
        async with self._execute_lock:
            self._execution_task = self.loop.create_task(
                self._async_execute_wrapper(api), name=f"Execute {self.command}"
            )

        try:
            await self._execution_task
        except CancelledError:
            pass

    async def _async_execute_wrapper(self, api: SnoozDeviceApi) -> None:
        try:
            # happens when a command is cancelled before execution is awaited
            if self.state == CommandProcessorState.COMPLETE:
                return

            self._machine.start_execution()

            response = await self._async_execute(api)

            # happens when a command is cancelled during execution
            if self.state != CommandProcessorState.EXECUTING:
                return

            self._machine.execution_complete(response=response)
        except Exception:
            _LOGGER.exception(
                self._(
                    f"Unexpected error while executing {self.command}\n"
                    + UNEXPECTED_ERROR_LOG_MESSAGE
                )
            )
            self.on_unhandled_exception()

    def _before_execution_start(self, **kwargs) -> None:
        _LOGGER.debug(self._(f"Executing {self.command}"))

    @abstractmethod
    async def _async_execute(self, api: SnoozDeviceApi) -> SnoozDeviceInfo | None:
        pass

    def cancel(self) -> None:
        # nothing to do if the command is already complete
        if self.state == CommandProcessorState.COMPLETE:
            return

        self._machine.cancelled()

    def on_disconnected(self) -> None:
        self._machine.disconnected()

    def on_device_unavailable(self) -> None:
        self._machine.device_unavailable()

    def on_unhandled_exception(self) -> None:
        self._machine.unhandled_exception()

    def _cancel_active_tasks(self) -> None:
        if self._execution_task is None or self._execution_task.done():
            return

        self._execution_task.cancel()
        self._execution_task = None

    def _abort_with_status(self, status: SnoozCommandResultStatus) -> None:
        self._result_status = status
        self._cancel_active_tasks()

    def _on_disconnect(self, **kwargs) -> None:
        self.last_disconnect_time = datetime.now()
        self._total_disconnects += 1
        self._cancel_active_tasks()

    def _on_complete(self, **kwargs) -> None:
        duration = datetime.now() - self.start_time

        message = f"Completed {self.command} ({self._result_status.name}) in {duration}"
        if self._total_disconnects > 0:
            message += f" with {self._total_disconnects} disconnects."

        response = kwargs.get("response", None)
        if response is not None:
            message += f" Response was {response}"

        _LOGGER.debug(self._(message))
        result = SnoozCommandResult(self._result_status, duration, response)
        self.result.set_result(result)


def default_log_formatter(message: str) -> str:
    return message


def create_command_processor(
    loop: AbstractEventLoop,
    start_time: datetime,
    data: SnoozCommandData,
    format_log_message: Callable[[str], str] | None = None,
) -> SnoozCommandProcessor:
    cls: type[SnoozCommandProcessor] | None = None

    if data.action is not None:
        cls = DeviceActionCommand
    elif data.duration:
        cls = TransitionedCommand
    else:
        cls = WriteDeviceStateCommand

    assert cls is not None
    result = loop.create_future()

    return cls(
        loop, format_log_message or default_log_formatter, data, start_time, result
    )


class DeviceActionCommand(SnoozCommandProcessor):
    async def _async_execute(self, api: SnoozDeviceApi) -> SnoozDeviceInfo | None:
        if self.command.action == SnoozDeviceAction.GET_DEVICE_INFO:
            return await api.async_get_info()
        if self.command.action == SnoozDeviceAction.ENABLE_AUTO_TEMP:
            await api.async_set_auto_temp_enabled(True)

        return None


class WriteDeviceStateCommand(SnoozCommandProcessor):
    async def _async_execute(self, api: SnoozDeviceApi) -> None:
        if self.command.volume is not None:
            await api.async_set_volume(self.command.volume)
        if self.command.on is not None:
            await api.async_set_power(self.command.on)
        if self.command.fan_speed is not None:
            await api.async_set_auto_temp_enabled(False)
            await api.async_set_fan_speed(self.command.fan_speed)
        if self.command.fan_on is not None:
            await api.async_set_auto_temp_enabled(False)
            await api.async_set_fan_enabled(self.command.fan_on)
        if self.command.temp_target is not None:
            await api.async_set_auto_temp_enabled(True)
            await api.async_set_auto_temp_threshold(self.command.temp_target)


class TransitionedCommand(SnoozCommandProcessor):
    @property
    def is_resuming(self) -> bool:
        return self.last_disconnect_time is not None

    def __init__(
        self,
        loop: AbstractEventLoop,
        _: Callable[[str], str],
        data: SnoozCommandData,
        start_time: datetime,
        result: Future[SnoozCommandResult],
    ) -> None:
        if data.duration is None:
            raise ValueError("Duration must be set for transitioned commands")

        super().__init__(loop, _, data, start_time, result)
        self._transition = Transition()
        self._starting_state: SnoozDeviceState | None = None
        self._remaining_duration = data.duration

    async def _async_execute(self, api: SnoozDeviceApi) -> None:
        # when resuming the transition, decrease the overall duration
        # by the time disconnected to make a best effort to complete in time
        if self.last_disconnect_time is not None:
            time_since_disconnect = datetime.now() - self.last_disconnect_time
            if time_since_disconnect > self._remaining_duration:
                self._remaining_duration = timedelta(seconds=0)
            else:
                self._remaining_duration -= time_since_disconnect

        current_state = await api.async_read_state()

        if self._starting_state is None:
            self._starting_state = current_state

        # when there's no remaining duration, it means the transition
        # resumed after being disconnected for longer than the original transition,
        # so we just immediately set the target state
        if self._remaining_duration.seconds <= 0:
            if self.command.on is not None and self.command.on != current_state.on:
                await api.async_set_power(self.command.on)

            if (
                self.command.volume is not None
                and self.command.volume != current_state.volume
            ):
                await api.async_set_volume(self.command.volume)
            elif (
                self.command.volume is None
                and not self.command.on
                and self._starting_state.volume is not None
            ):
                await api.async_set_volume(self._starting_state.volume)

            return

        # SNOOZ supports values < MIN_DEVICE_VOLUME, but they don't effect the volume.
        # To prevent a delay in the transition, set it to the minimum instead of 0
        start_volume = (
            (current_state.volume if current_state.on else MIN_DEVICE_VOLUME)
            if self.command.on
            else current_state.volume
        )
        end_volume = (
            (self.command.volume or current_state.volume)
            if self.command.on
            else MIN_DEVICE_VOLUME
        )

        if start_volume is None:
            raise ValueError("Start volume was None")

        if end_volume is None:
            raise ValueError("End volume was None")

        # turn on the device if necessary
        if self.command.on and not current_state.on:
            # set volume before turning on to prevent a moment with the original volume
            await api.async_set_volume(start_volume)
            await api.async_set_power(True)

        await self._async_transition_volume(
            api,
            self.command.on,
            start_volume,
            end_volume,
            self._remaining_duration,
        )

    async def _async_transition_volume(
        self,
        api: SnoozDeviceApi,
        turning_on: bool | None,
        start_volume: int,
        end_volume: int,
        duration: timedelta,
    ) -> None:
        # if the device is already at the target volume, avoid the transition
        if start_volume == end_volume:
            return

        action = "resume" if self.is_resuming else "start"
        _LOGGER.debug(
            self._(
                f"[{action}] volume {start_volume}% to {end_volume}%"
                f"{'' if turning_on else ' then turn off'} in {duration}"
            )
        )

        last_volume = start_volume

        async def on_update(volume: float) -> None:
            nonlocal last_volume

            next_volume = int(round(volume))

            if next_volume != last_volume:
                _LOGGER.debug(self._(f"[{action}] set volume {next_volume}%"))
                await api.async_set_volume(next_volume)
                last_volume = next_volume

        async def on_complete() -> None:
            if not turning_on:
                nonlocal last_volume

                initial_volume: int | None = None

                if (
                    self._starting_state is not None
                    and self._starting_state.volume is not None
                    and self._starting_state.volume != last_volume
                ):
                    initial_volume = self._starting_state.volume
                    _LOGGER.debug(
                        self._(
                            f"[{action}] power off and reset to "
                            f"{self._starting_state.volume}% volume"
                        )
                    )
                else:
                    _LOGGER.debug(self._(f"[{action}] power off"))

                await api.async_set_power(False)

                # if we want to turn on again, make sure we reset
                # the volume before starting the transition
                if initial_volume is not None:
                    await api.async_set_volume(initial_volume)

        await self._transition.async_run(
            self.loop, start_volume, end_volume, duration, on_update, on_complete
        )

    def _cancel_active_tasks(self) -> None:
        super()._cancel_active_tasks()
        self._transition.cancel()
