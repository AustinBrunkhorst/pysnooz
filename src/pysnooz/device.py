from __future__ import annotations

import asyncio
import logging
from asyncio import AbstractEventLoop, CancelledError, Event, Lock, Task
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from bleak.backends.device import BLEDevice
from bleak_retry_connector import (
    BleakAbortedError,
    BleakClientWithServiceCache,
    BleakConnectionError,
    BleakNotFoundError,
    establish_connection,
)
from events import Events
from transitions import EventData, Machine, State

from pysnooz.advertisement import get_snooz_display_name
from pysnooz.api import SnoozDeviceApi, SnoozDeviceState, UnknownSnoozState
from pysnooz.commands import (
    CommandProcessorState,
    SnoozCommandData,
    SnoozCommandProcessor,
    SnoozCommandResult,
    create_command_processor,
)
from pysnooz.const import UNEXPECTED_ERROR_LOG_MESSAGE

_LOGGER = logging.getLogger(__name__)

MAX_RECONNECTION_ATTEMPTS = 3
RECONNECTION_DELAY_SECONDS = 0.25
DEVICE_UNAVAILABLE_EXCEPTIONS = (
    BleakAbortedError,
    BleakConnectionError,
    BleakNotFoundError,
)


class SnoozConnectionStatus(Enum):
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2


class DisconnectionReason(Enum):
    # disconnection was initiated by the user
    USER = 0
    # the bluetooth connection was lost
    DEVICE = 1
    # a connection attempt failed with a known error
    # like a timeout or device not found
    DEVICE_UNAVAILABLE = 2
    # an exception was thrown during connection or
    # command execution that was uncaught
    UNEXPECTED_ERROR = 3


class SnoozDeviceDisconnectedError(Exception):
    pass


class SnoozDeviceUnavailableError(Exception):
    pass


class SnoozDevice:
    def __init__(
        self, device: BLEDevice, token: str, loop: AbstractEventLoop | None = None
    ) -> None:
        self.state: SnoozDeviceState = UnknownSnoozState
        self.events = Events(
            (
                # received state from bluetooth characteristic
                "on_state_change",
                # SnoozConnectionStatus
                "on_connection_status_change",
                # time it takes to create a bluetooth connection, authenticate
                # and subscribe to notifications
                "on_connection_load_time",
                # time between connection ready and disconnection
                "on_connection_duration",
            )
        )
        self._device = device
        self._token = token
        self._loop = loop if loop is not None else asyncio.get_running_loop()
        self._last_dispatched_connection_status: SnoozConnectionStatus | None = None
        self._connection_complete = Event()
        self._connections_exhausted = Event()
        self._connection_attempts: int = 0
        self._connection_start_time: datetime | None = None
        self._connection_ready_time: datetime | None = None
        self._api: SnoozDeviceApi | None = None
        self._connect_lock = Lock()
        self._command_lock = Lock()
        self._connection_task: Task[None] | None = None
        self._reconnection_task: Task[None] | None = None
        self._current_command: SnoozCommandProcessor | None = None
        self._is_manually_disconnecting: bool = False

        not_disconnected = [
            SnoozConnectionStatus.CONNECTING,
            SnoozConnectionStatus.CONNECTED,
        ]

        states = [
            State(
                SnoozConnectionStatus.DISCONNECTED,
                on_enter=self._on_device_disconnected,
            ),
            State(SnoozConnectionStatus.CONNECTING),
            State(SnoozConnectionStatus.CONNECTED, on_enter=self._on_connection_ready),
        ]

        self._machine = Machine(
            model_attribute="connection_status",
            states=states,
            initial=SnoozConnectionStatus.DISCONNECTED,
            after_state_change=self._on_connection_status_change,
            send_event=True,
            on_exception=self._on_machine_exception,
        )
        self._machine.add_transition(
            "connection_start",
            SnoozConnectionStatus.DISCONNECTED,
            SnoozConnectionStatus.CONNECTING,
            before=self._on_connection_start,
        )
        self._machine.add_transition(
            "connection_ready",
            SnoozConnectionStatus.CONNECTING,
            SnoozConnectionStatus.CONNECTED,
        )
        self._machine.add_transition(
            "device_disconnected",
            not_disconnected,
            SnoozConnectionStatus.DISCONNECTED,
            after=self._after_device_disconnected,
        )

        self.events.on_connection_load_time += lambda t: _LOGGER.debug(
            self._(f"Connection load time: {t}")
        )
        self.events.on_connection_duration += lambda t: _LOGGER.debug(
            self._(f"Connection duration: {t}")
        )

    @property
    def name(self) -> str:
        return self._device.name

    @property
    def address(self) -> str:
        return self._device.address

    @property
    def connection_status(self) -> SnoozConnectionStatus:
        return self._machine.connection_status

    @property
    def is_connected(self) -> bool:
        return self.connection_status == SnoozConnectionStatus.CONNECTED

    def subscribe_to_state_change(
        self, callback: Callable[[], None]
    ) -> Callable[[], None]:
        """
        Subscribe to device state and connection status change.
        Returns a callback to unsubscribe.
        """

        def wrapped_callback(*_: Any) -> None:
            callback()

        self.events.on_state_change += wrapped_callback
        self.events.on_connection_status_change += wrapped_callback

        def unsubscribe() -> None:
            self.events.on_state_change -= wrapped_callback
            self.events.on_connection_status_change -= wrapped_callback

        return unsubscribe

    async def async_disconnect(self) -> None:
        if self.connection_status == SnoozConnectionStatus.DISCONNECTED:
            return

        self._is_manually_disconnecting = True
        try:
            self._cancel_current_command()

            if (
                self._reconnection_task is not None
                and not self._reconnection_task.done()
            ):
                self._reconnection_task.cancel()

            if self._connection_task is not None and not self._connection_task.done():
                self._connection_task.cancel()

            if self._api is not None:
                await self._api.async_disconnect()

            self._machine.device_disconnected(reason=DisconnectionReason.USER)
        finally:
            self._is_manually_disconnecting = False

    async def async_execute_command(self, data: SnoozCommandData) -> SnoozCommandResult:
        self._cancel_current_command()

        start_time = datetime.now()
        command = create_command_processor(
            self._loop, start_time, data, format_log_message=self._
        )
        self._current_command = command

        await self._async_execute_current_command()

        result = await command.result

        self._current_command = None

        return result

    def _cancel_current_command(self) -> None:
        if self._current_command is None:
            return

        self._current_command.cancel()
        self._current_command = None

    async def _async_execute_current_command(self) -> None:
        command = self._current_command

        try:
            await self._async_wait_for_connection_complete()

            async with self._command_lock:
                if (
                    self._api is not None
                    and command is not None
                    and command.state != CommandProcessorState.COMPLETE
                ):
                    await command.async_execute(self._api)
        except CancelledError:
            # happens when async_disconnect() is called during a connection
            # we swallow it because we want to escape execution of the command
            pass
        except SnoozDeviceDisconnectedError:
            self._machine.device_disconnected(reason=DisconnectionReason.DEVICE)
        except SnoozDeviceUnavailableError:
            self._machine.device_disconnected(
                reason=DisconnectionReason.DEVICE_UNAVAILABLE
            )
        except Exception:
            self._machine.device_disconnected(
                reason=DisconnectionReason.UNEXPECTED_ERROR
            )

    async def _async_wait_for_connection_complete(self) -> None:
        if self.connection_status == SnoozConnectionStatus.DISCONNECTED:
            async with self._connect_lock:
                if self._connection_task is None or self._connection_task.done():
                    self._connection_task = self._loop.create_task(
                        self._async_connect(), name=f"[Connect] {self.display_name}"
                    )
            await self._connection_task

        await self._connection_complete.wait()

    async def _async_connect(self) -> None:
        self._machine.connection_start()

        try:
            api = await self._async_create_api()
            api.events.on_disconnect += lambda: self._machine.device_disconnected(
                reason=DisconnectionReason.DEVICE
            )
            api.events.on_state_change += lambda state: self._on_receive_device_state(
                state
            )
            self._before_device_connected()
            self._api = api
        except DEVICE_UNAVAILABLE_EXCEPTIONS as ex:
            raise SnoozDeviceUnavailableError() from ex

        # ensure each call with side effects checks the connection status
        # to prevent a cancellation race condition

        if self.connection_status == SnoozConnectionStatus.CONNECTING:
            await api.async_authenticate_connection(bytes.fromhex(self._token))

        if self.connection_status == SnoozConnectionStatus.CONNECTING:
            await api.async_listen_for_state_changes()

        if self.connection_status == SnoozConnectionStatus.CONNECTING:
            self._machine.connection_ready()

    async def _async_create_api(self) -> SnoozDeviceApi:
        api = SnoozDeviceApi(format_log_message=self._)

        def _on_disconnect(_: BleakClientWithServiceCache) -> None:
            # don't trigger a device disconnection event when a user
            # manually requests a disconnect
            if not self._is_manually_disconnecting:
                api.events.on_disconnect()

        client = await establish_connection(
            BleakClientWithServiceCache,
            self._device,
            self.display_name,
            _on_disconnect,
            use_services_cache=True,
        )

        api.set_client(client)

        return api

    async def _async_reconnect(self) -> None:
        await asyncio.sleep(RECONNECTION_DELAY_SECONDS)
        await self._async_execute_current_command()

    def _on_machine_exception(self, e: EventData) -> None:
        # make sure any pending commands are completed
        if (
            self._current_command is not None
            and self._current_command.state != CommandProcessorState.COMPLETE
        ):
            self._current_command.on_unhandled_exception()

        _LOGGER.exception(
            self._(
                "An exception occurred during a state transition.\n"
                + UNEXPECTED_ERROR_LOG_MESSAGE
            )
        )

    def _on_connection_start(self, e: EventData) -> None:
        message = "Start connection"
        if self._connection_attempts >= 1:
            message += f" (attempt {self._connection_attempts})"
        _LOGGER.debug(self._(message))

        self._connection_complete.clear()
        self._connections_exhausted.clear()
        self._connection_attempts += 1
        self._connection_start_time = datetime.now()

    def _before_device_connected(self) -> None:
        start_time = datetime.now()
        if self._connection_start_time is not None:
            start_time = self._connection_start_time
        message = f"Got connection in {datetime.now() - start_time}"
        if self._connection_attempts >= 1:
            message += f" (attempt {self._connection_attempts})"
        _LOGGER.debug(self._(message))

    def _on_connection_ready(self, e: EventData) -> None:
        self._connection_attempts = 0
        self._connection_ready_time = datetime.now()
        if self._connection_start_time is not None:
            self.events.on_connection_load_time(
                self._connection_ready_time - self._connection_start_time
            )
        self._connection_complete.set()
        self._connections_exhausted.clear()

    def _on_connection_status_change(self, e: EventData) -> None:
        new_status = self.connection_status

        if new_status == self._last_dispatched_connection_status:
            return

        _LOGGER.debug(self._(describe_connection_status(new_status)))

        self._last_dispatched_connection_status = new_status
        self.events.on_connection_status_change(new_status)

    def _on_receive_device_state(self, new_state: SnoozDeviceState) -> None:
        was_changed = self.state is UnknownSnoozState or new_state != self.state

        self.state = new_state

        if was_changed:
            self.events.on_state_change(self.state)

    def _after_device_disconnected(self, e: EventData) -> None:
        reason: DisconnectionReason = e.kwargs.get("reason")
        level = (
            logging.ERROR
            if reason == DisconnectionReason.DEVICE_UNAVAILABLE
            else logging.INFO
        )
        _LOGGER.log(
            level,
            self._(f"disconnected because {describe_disconnection_reason(reason)}"),
            exc_info=reason
            not in (DisconnectionReason.USER, DisconnectionReason.DEVICE),
        )

    def _on_device_disconnected(self, e: EventData) -> None:
        self._api = None

        last_event = self._connection_ready_time or self._connection_start_time
        if last_event is not None:
            self.events.on_connection_duration(datetime.now() - last_event)

        self._connection_start_time = None
        self._connection_ready_time = None
        self._connection_complete.set()

        disconnect_reason: DisconnectionReason = e.kwargs.get("reason")

        # if the disconnection was initiated from the user, don't attempt to reconnect
        if disconnect_reason == DisconnectionReason.USER:
            return

        if self._connection_attempts >= MAX_RECONNECTION_ATTEMPTS:
            _LOGGER.error(
                self._(
                    f"Unavailable after {self._connection_attempts}"
                    " connection attempts"
                )
            )

            if (
                self._current_command is not None
                and self._current_command.state != CommandProcessorState.COMPLETE
            ):
                self._current_command.on_device_unavailable()

            self._connections_exhausted.set()
            self._connection_attempts = 0

            return

        if self._current_command is not None:
            # don't reconnect on unexpected errors
            if disconnect_reason == DisconnectionReason.UNEXPECTED_ERROR:
                self._current_command.on_unhandled_exception()
                return

            self._current_command.on_disconnected()

        # attempt to reconnect automatically
        # we don't await the result since this is called from a sync state transition
        # we cleanup this task on disconnect
        reconnection_task = self._loop.create_task(
            self._async_reconnect(),
            name=f"[Reconnect] {self.display_name}",
        )

        # cancel previous tasks to avoid any zombies
        if self._reconnection_task is not None and not self._reconnection_task.done():
            self._reconnection_task.cancel()

        self._reconnection_task = reconnection_task

    def _(self, message: str) -> str:
        """Format a message for logging."""
        return f"[{self.display_name}] {message}"

    @property
    def display_name(self) -> str:
        return get_snooz_display_name(self.name, self.address)

    def __repr__(self) -> str:
        description = []

        if self.is_connected:
            state = self.state
            if state is None or state == UnknownSnoozState:
                description += ["Unknown state"]
            else:
                description += [
                    f"{'On' if state.on else 'Off'} at {state.volume}% volume"
                ]
        else:
            description += ["Disconnected"]

        return f"SnoozDevice({self.address} {' '.join(description)})"


def describe_connection_status(status: SnoozConnectionStatus) -> str:
    descriptions = {
        SnoozConnectionStatus.DISCONNECTED: "🔴 Disconnected",
        SnoozConnectionStatus.CONNECTING: "🟡 Connecting",
        SnoozConnectionStatus.CONNECTED: "🟢 Connected",
    }
    return descriptions[status] or status.name


def describe_disconnection_reason(reason: DisconnectionReason) -> str:
    descriptions = {
        DisconnectionReason.USER: (
            f"{SnoozDevice.async_disconnect.__qualname__}() was called"
        ),
        DisconnectionReason.DEVICE: "the bluetooth connection was lost",
        DisconnectionReason.UNEXPECTED_ERROR: (
            f"an uncaught exception occurred.\n{UNEXPECTED_ERROR_LOG_MESSAGE}"
        ),
        DisconnectionReason.DEVICE_UNAVAILABLE: (
            "the device couldn't establish a connection"
        ),
    }
    return descriptions[reason] or reason.name
