from __future__ import annotations

import asyncio
import logging
from asyncio import Lock
from enum import IntEnum
from typing import Any, Callable

from bleak import BleakClient
from bleak.exc import BleakDBusError
from events import Events

# uuid of the characteristic that reads snooz state
READ_STATE_UUID = "80c37f00-cc16-11e4-8830-0800200c9a66"

# uuid of the characteristic that writes snooz state
WRITE_STATE_UUID = "90759319-1668-44da-9ef3-492d593bd1e5"

# values less than this have no effect
MIN_DEVICE_VOLUME = 10

# number of times to retry a transient command failure before giving up
RETRY_WRITE_FAILURE_COUNT = 5
RETRY_SLEEP_DURATIONS = [0, 0.5, 1, 1, 2]
DBUS_ERRORS_TO_RETRY = (
    "org.bluez.Error",
    "org.bluez.Error.Failed",
    "org.bluez.Error.InProgress",
)

_LOGGER = logging.getLogger(__name__)


class SnoozDeviceState:
    def __init__(self, on: bool | None, volume: int | None) -> None:
        self.on = on
        self.volume = volume

    def __eq__(self, other: Any) -> bool:
        return self.on == other.on and self.volume == other.volume

    def __repr__(self) -> str:
        if self.on is None and self.volume is None:
            return "Snooz(Unknown)"

        return f"Snooz({'On' if self.on else 'Off'} at {self.volume}% volume)"


UnknownSnoozState = SnoozDeviceState(on=None, volume=None)


class CommandId(IntEnum):
    SET_VOLUME = 1
    SET_POWER = 2
    SET_TOKEN = 6


class SnoozDeviceApi:
    def __init__(
        self,
        client: BleakClient | None = None,
        format_log_message: Callable[[str], str] | None = None,
    ) -> None:
        self.events = Events(("on_disconnect", "on_state_change"))
        self._client = client
        self._write_lock = Lock()
        self._ = format_log_message or (lambda msg: msg)

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    def set_client(self, client: BleakClient) -> None:
        self._client = client

    async def async_disconnect(self) -> None:
        if self._client is None:
            raise Exception("Called async_disconnect with no client")

        await self._client.disconnect()

    async def async_authenticate_connection(self, token: bytes) -> None:
        await self._async_write_command(CommandId.SET_TOKEN, token)

    async def async_set_power(self, on: bool) -> None:
        await self._async_write_command(CommandId.SET_POWER, b"\x01" if on else b"\x00")

    async def async_set_volume(self, volume: int) -> None:
        if volume < 0 or volume > 100:
            raise ValueError(f"Volume must be between 0 and 100 - got {volume}")

        await self._async_write_command(CommandId.SET_VOLUME, bytes([volume]))

    async def async_read_state(self, use_cached: bool = False) -> SnoozDeviceState:
        if self._client is None:
            raise Exception("Called async_read_state with no client")

        data = await self._client.read_gatt_char(READ_STATE_UUID, use_cached=use_cached)
        return state_from_char_data(data)

    async def async_listen_for_state_changes(self) -> None:
        if self._client is None:
            raise Exception("Called async_listen_for_state_changes with no client")

        if not self._client.is_connected:
            return

        await self._client.start_notify(
            READ_STATE_UUID,
            lambda _, data: self.events.on_state_change(state_from_char_data(data)),
        )

    async def _async_write_command(self, command: CommandId, data: bytes) -> None:
        if self._client is None:
            raise Exception("Called _async_write_command with no client")

        attempts = 0
        payload = bytes([command]) + data

        async with self._write_lock:
            last_ex: BleakDBusError | None = None

            while self._client.is_connected and attempts <= RETRY_WRITE_FAILURE_COUNT:
                try:
                    message = f"write {payload.hex()}"
                    if attempts > 0 and last_ex is not None:
                        message += f" (attempt {attempts+1}, last error: {last_ex})"
                    _LOGGER.debug(self._(message))
                    await self._client.write_gatt_char(
                        WRITE_STATE_UUID, payload, response=True
                    )
                    return
                except BleakDBusError as ex:
                    last_ex = ex
                    if ex.dbus_error in DBUS_ERRORS_TO_RETRY:
                        sleep_duration = RETRY_SLEEP_DURATIONS[
                            attempts % len(RETRY_SLEEP_DURATIONS)
                        ]
                        attempts += 1

                        if attempts > RETRY_WRITE_FAILURE_COUNT:
                            raise Exception(
                                f"Got transient error {attempts} times"
                            ) from ex

                        await asyncio.sleep(sleep_duration)
                    else:
                        raise


def state_from_char_data(data: bytes) -> SnoozDeviceState:
    volume = data[0]
    on = data[1] == 0x01
    return SnoozDeviceState(on, volume)
