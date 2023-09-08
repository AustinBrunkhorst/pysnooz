from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from asyncio import AbstractEventLoop, CancelledError, Future, Lock, Task
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, IntEnum
from typing import Any, Callable

from transitions import Machine, State

from pysnooz.api import MIN_DEVICE_VOLUME, MIN_FAN_SPEED, SnoozDeviceApi
from pysnooz.const import UNEXPECTED_ERROR_LOG_MESSAGE
from pysnooz.model import SnoozDeviceCharacteristicData, SnoozDeviceState
from pysnooz.transition import Transition

_LOGGER = logging.getLogger(__name__)


class SnoozDeviceAction(IntEnum):
    GET_DEVICE_INFO = 0


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
    auto_temp_enabled: bool | None = None

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

        if self.auto_temp_enabled is not None:
            operations += [
                f"{'Enable' if self.auto_temp_enabled else 'Disable'}AutoTemp"
            ]

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


def set_auto_temp_enabled(enabled: bool) -> SnoozCommandData:
    return SnoozCommandData(auto_temp_enabled=enabled)


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
    response: SnoozDeviceCharacteristicData | None = None


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

    def _before_execution_start(self, **kwargs: Any) -> None:
        _LOGGER.debug(self._(f"Executing {self.command}"))

    @abstractmethod
    async def _async_execute(
        self, api: SnoozDeviceApi
    ) -> SnoozDeviceCharacteristicData | None:
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

    def _on_disconnect(self, **kwargs: Any) -> None:
        self.last_disconnect_time = datetime.now()
        self._total_disconnects += 1
        self._cancel_active_tasks()

    def _on_complete(self, **kwargs: Any) -> None:
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

    result = loop.create_future()

    return cls(
        loop, format_log_message or default_log_formatter, data, start_time, result
    )


class DeviceActionCommand(SnoozCommandProcessor):
    async def _async_execute(
        self, api: SnoozDeviceApi
    ) -> SnoozDeviceCharacteristicData | None:
        if self.command.action == SnoozDeviceAction.GET_DEVICE_INFO:
            return await api.async_get_info()

        return None


class WriteDeviceStateCommand(SnoozCommandProcessor):
    async def _async_execute(self, api: SnoozDeviceApi) -> None:
        if self.command.volume is not None:
            await api.async_set_volume(self.command.volume)
        if self.command.on is not None:
            await api.async_set_power(self.command.on)
        if self.command.fan_speed is not None:
            await api.async_set_fan_speed(self.command.fan_speed)
        if self.command.fan_on is not None:
            await api.async_set_fan_power(self.command.fan_on)
        if self.command.auto_temp_enabled is not None:
            await api.async_set_auto_temp_enabled(self.command.auto_temp_enabled)
        if self.command.temp_target is not None:
            await api.async_set_auto_temp_enabled(True)
            await api.async_set_auto_temp_threshold(self.command.temp_target)


class DeviceFeatureControls(ABC):
    @property
    @abstractmethod
    def min_percent(self) -> int:
        pass

    @abstractmethod
    def get_command_power(self, command: SnoozCommandData) -> bool | None:
        pass

    @abstractmethod
    def get_command_percent(self, command: SnoozCommandData) -> int | None:
        pass

    @abstractmethod
    def get_power(self, state: SnoozDeviceState) -> bool | None:
        pass

    @abstractmethod
    def get_percent(self, state: SnoozDeviceState) -> int | None:
        pass

    @abstractmethod
    async def async_set_power(self, api: SnoozDeviceApi, on: bool) -> None:
        pass

    @abstractmethod
    async def async_set_percent(self, api: SnoozDeviceApi, volume: int) -> None:
        pass


class SoundControls(DeviceFeatureControls):
    @property
    def min_percent(self) -> int:
        return MIN_DEVICE_VOLUME

    def get_command_power(self, command: SnoozCommandData) -> bool | None:
        return command.on

    def get_command_percent(self, command: SnoozCommandData) -> int | None:
        return command.volume

    def get_power(self, state: SnoozDeviceState) -> bool | None:
        return state.on

    def get_percent(self, state: SnoozDeviceState) -> int | None:
        return state.volume

    async def async_set_power(self, api: SnoozDeviceApi, on: bool) -> None:
        await api.async_set_power(on)

    async def async_set_percent(self, api: SnoozDeviceApi, volume: int) -> None:
        await api.async_set_volume(volume)


class FanControls(DeviceFeatureControls):
    @property
    def min_percent(self) -> int:
        return MIN_FAN_SPEED

    def get_command_power(self, command: SnoozCommandData) -> bool | None:
        return command.fan_on

    def get_command_percent(self, command: SnoozCommandData) -> int | None:
        return command.fan_speed

    def get_power(self, state: SnoozDeviceState) -> bool | None:
        return state.fan_on

    def get_percent(self, state: SnoozDeviceState) -> int | None:
        return state.fan_speed

    async def async_set_power(self, api: SnoozDeviceApi, on: bool) -> None:
        await api.async_set_fan_power(on)

    async def async_set_percent(self, api: SnoozDeviceApi, speed: int) -> None:
        await api.async_set_fan_speed(speed)


@dataclass
class ControlsTransition:
    feature: DeviceFeatureControls
    turning_on: bool | None
    start_percent: int
    end_percent: int

    @property
    def name(self) -> str:
        return self.feature.__class__.__name__.replace("Controls", "")


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
        self._features: list[DeviceFeatureControls] = []

        if data.on is not None or data.volume is not None:
            self._features.append(SoundControls())
        if data.fan_on is not None or data.fan_speed is not None:
            self._features.append(FanControls())

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
            for feature in self._features:
                command_power = feature.get_command_power(self.command)
                command_percent = feature.get_command_percent(self.command)

                if command_power is not None and command_power != feature.get_power(
                    current_state
                ):
                    await feature.async_set_power(api, command_power)

                if (
                    command_percent is not None
                    and command_percent != feature.get_percent(current_state)
                ):
                    await feature.async_set_percent(api, command_percent)
                elif command_percent is None and not command_power:
                    starting_percent = feature.get_percent(self._starting_state)

                    if starting_percent is not None:
                        await feature.async_set_percent(api, starting_percent)

            return

        transitions: list[ControlsTransition] = []

        for feature in self._features:
            current_power = feature.get_power(current_state)
            current_percent = feature.get_percent(current_state)
            command_percent = feature.get_command_percent(self.command)
            command_power = feature.get_command_power(self.command)

            # To prevent a delay in the transition, set it to the minimum instead of 0
            start_percent = (
                (current_percent if current_power else feature.min_percent)
                if command_power
                else current_percent
            )
            end_percent = (
                (command_percent or current_percent)
                if command_power
                else feature.min_percent
            )

            if start_percent is None:
                raise ValueError("Start percent was None")

            if end_percent is None:
                raise ValueError("End percent was None")

            # turn on the feature if necessary
            if command_power and not current_power:
                # set percent before turning on to prevent a moment with
                # the original value
                await feature.async_set_percent(api, start_percent)
                await feature.async_set_power(api, True)

            transitions.append(
                ControlsTransition(feature, command_power, start_percent, end_percent)
            )

        await self._async_transition_controls(
            api,
            transitions,
            self._remaining_duration,
        )

    async def _async_transition_controls(
        self,
        api: SnoozDeviceApi,
        controls: list[ControlsTransition],
        duration: timedelta,
    ) -> None:
        # if the device is already at the target states, avoid the transition
        if all(c.start_percent == c.end_percent for c in controls):
            return

        action = "resume" if self.is_resuming else "start"

        last_percent: dict[str, int] = {}

        for transition in controls:
            _LOGGER.debug(
                self._(
                    f"[{action}] {transition.name} {transition.start_percent}%"
                    f" to {transition.end_percent}%"
                    f"{'' if transition.turning_on else ' then turn off'} in {duration}"
                )
            )
            last_percent[transition.name] = transition.start_percent

        async def on_update(progress: float) -> None:
            nonlocal last_percent, controls

            for transition in controls:
                next_percent = int(
                    round(
                        transition.start_percent
                        + (transition.end_percent - transition.start_percent) * progress
                    )
                )

                if next_percent != last_percent.get(transition.name, None):
                    await transition.feature.async_set_percent(api, next_percent)
                    last_percent[transition.name] = next_percent

        async def on_complete() -> None:
            for transition in controls:
                if transition.turning_on:
                    continue

                nonlocal last_percent

                initial_percent: int | None = (
                    transition.feature.get_percent(self._starting_state)
                    if self._starting_state is not None
                    else None
                )

                if initial_percent is not None:
                    _LOGGER.debug(
                        self._(
                            f"[{action}] {transition.name} power off and reset to "
                            f"{initial_percent}%"
                        )
                    )
                else:
                    _LOGGER.debug(self._(f"[{action}] {transition.name} power off"))

                await transition.feature.async_set_power(api, False)

                # if we want to turn on again, make sure we reset
                # the value before starting the transition
                if initial_percent is not None:
                    await transition.feature.async_set_percent(api, initial_percent)

        await self._transition.async_run(
            self.loop, 0.0, 1.0, duration, on_update, on_complete
        )

    def _cancel_active_tasks(self) -> None:
        super()._cancel_active_tasks()
        self._transition.cancel()
