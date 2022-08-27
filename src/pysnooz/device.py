from __future__ import annotations

import logging
from asyncio import AbstractEventLoop, Event, Lock, Task
from datetime import datetime
from enum import Enum

from bleak.backends.device import BLEDevice
from bleak_retry_connector import (
    BleakAbortedError,
    BleakClient,
    BleakConnectionError,
    BleakNotFoundError,
    establish_connection,
)
from events import Events
from transitions import Machine, State

from pysnooz.api import SnoozDeviceApi, SnoozDeviceState, UnknownSnoozState
from pysnooz.commands import (
    SnoozCommandData,
    SnoozCommandProcessor,
    SnoozCommandResult,
    create_command_processor,
)

_LOGGER = logging.getLogger(__name__)

MAX_RECONNECTION_ATTEMPTS = 3


class SnoozConnectionStatus(Enum):
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2


class SnoozDeviceUnavailableError(Exception):
    pass


class SnoozDevice:
    def __init__(self, device: BLEDevice, token: str, loop: AbstractEventLoop) -> None:
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
        self._loop = loop
        self._connection_ready = Event()
        self._last_dispatched_connection_status = None
        self._connection_attempts: int = 0
        self._connection_start_time: datetime | None = None
        self._connection_ready_time: datetime | None = None
        self._api: SnoozDeviceApi | None = None
        self._connect_lock = Lock()
        self._connection_task: Task[None] | None = None
        self._current_command: SnoozCommandProcessor | None = None

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
        )
        self._machine.add_transition(
            "connection_start",
            SnoozConnectionStatus.DISCONNECTED,
            SnoozConnectionStatus.CONNECTING,
            before=self._on_connection_start,
        )
        self._machine.add_transition(
            "device_connected",
            SnoozConnectionStatus.CONNECTING,
            "=",
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
        )

    @property
    def name(self) -> str:
        return self._device.name

    @property
    def address(self) -> str:
        return self._device.address

    @property
    def is_connected(self) -> bool:
        return self._machine.connection_status == SnoozConnectionStatus.CONNECTED

    async def async_disconnect(self) -> None:
        if not self.is_connected:
            return

        if self._connection_task is not None:
            self._connection_task.cancel()

        self._cancel_current_command()

        if self._api is not None:
            await self._api.async_disconnect()

        self._machine.device_disconnected()

    async def async_execute_command(self, data: SnoozCommandData) -> SnoozCommandResult:
        self._cancel_current_command()

        start_time = datetime.now()
        command = create_command_processor(self._loop, start_time, data)
        self._current_command = command

        try:
            await self._async_wait_for_connection()

            # this shouldn't happen
            if self._api is None:
                raise Exception("API is not initialized")

            await command.async_execute(self._api)
        except SnoozDeviceUnavailableError:
            command.on_device_unavailable()
        except Exception:
            _LOGGER.exception(f"Exception while processing command {command}")
            command.on_unhandled_exception()

        result = await command.result

        self._current_command = None

        return result

    def _cancel_current_command(self) -> None:
        if self._current_command is None:
            return

        self._current_command.cancel()
        self._current_command = None

    async def _async_wait_for_connection(self) -> None:
        if self._machine.connection_status == SnoozConnectionStatus.DISCONNECTED:
            async with self._connect_lock:
                if self._connection_task is None or self._connection_task.done():
                    self._connection_task = self._loop.create_task(
                        self._async_connect(), name=f"Connect to SNOOZ {self.address}"
                    )
            await self._connection_task

        await self._connection_ready.wait()

        # if we reach this state, it means connection attempts are exhausted
        if self._machine.connection_status != SnoozConnectionStatus.CONNECTED:
            raise SnoozDeviceUnavailableError()

    async def _async_connect(self) -> None:
        self._machine.connection_start()

        try:
            client = await establish_connection(
                BleakClient,
                self._device,
                self._device.name,
            )
        except (BleakConnectionError, BleakNotFoundError, BleakAbortedError):
            _LOGGER.exception("Device unavailable")
            raise SnoozDeviceUnavailableError()

        api = SnoozDeviceApi(client)
        api.events.on_disconnect += lambda: self._machine.device_disconnected()
        api.events.on_state_change += lambda state: self._on_receive_device_state(state)
        self._api = api

        self._machine.device_connected()

        await api.async_authenticate_connection(bytes.fromhex(self._token))

        # has to be called after authenticated
        await api.async_listen_for_state_changes()

        # device could disconnect in the previous api call
        if self._machine.connection_status != SnoozConnectionStatus.CONNECTING:
            return

        self._machine.connection_ready()

    async def _async_reconnect(self) -> None:
        try:
            await self._async_connect()

            # retry executing the current command
            if self._current_command is not None:
                # this shouldn't happen
                if self._api is None:
                    raise Exception("API is not initialized")

                await self._current_command.async_execute(self._api)
        except Exception:
            _LOGGER.exception(f"Exception while reconnecting to {self.address}")
            self._machine.device_disconnected()

    def _on_connection_start(self) -> None:
        self._connection_attempts += 1
        self._connection_start_time = datetime.now()

    def _on_connection_ready(self) -> None:
        self._connection_attempts = 0
        self._connection_ready_time = datetime.now()
        self.events.on_connection_load_time(
            datetime.now() - self._connection_ready_time
        )
        self._connection_ready.set()

    def _on_connection_status_change(self) -> None:
        new_status = self._machine.connection_status

        if new_status == self._last_dispatched_connection_status:
            return

        self._last_dispatched_connection_status = new_status
        self.events.on_connection_status_change(new_status)

    def _on_receive_device_state(self, new_state: SnoozDeviceState) -> None:
        was_changed = self.state is UnknownSnoozState or new_state != self.state

        self.state = new_state

        if was_changed:
            self.events.on_state_change(self.state)

    def _on_device_disconnected(self) -> None:
        last_event = self._connection_ready_time or self._connection_start_time
        if last_event is not None:
            self.events.on_connection_duration(datetime.now() - last_event)

        self._connection_start_time = None
        self._connection_ready_time = None
        self._connection_ready.clear()

        if self._current_command is not None:
            self._current_command.on_disconnected()

        if self._connection_attempts >= MAX_RECONNECTION_ATTEMPTS:
            # unblock the current command from waiting for a connection
            if self._current_command is not None:
                self._connection_ready.set()

            _LOGGER.error(
                f"Device {self.address} unavailable after"
                f" {self._connection_attempts} attempts"
            )

            return

        # attempt to reconnect automatically
        # we don't await the result since this is called from a sync state transition
        # we cleanup this task on disconnect
        self._connection_task = self._loop.create_task(
            self._async_reconnect(), name=f"Reconnect to SNOOZ {self.address}"
        )

    def display_name(self) -> str:
        return ""

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
