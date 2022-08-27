from __future__ import annotations

from enum import IntEnum
from typing import Any

from bleak import BleakClient
from events import Events

# uuid of the characteristic that reads snooz state
READ_STATE_UUID = "80c37f00-cc16-11e4-8830-0800200c9a66"

# uuid of the characteristic that writes snooz state
WRITE_STATE_UUID = "90759319-1668-44da-9ef3-492d593bd1e5"

# values less than this have no effect
MIN_DEVICE_VOLUME = 10


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
    def __init__(self, client: BleakClient) -> None:
        self.events = Events(("on_disconnect", "on_state_change"))
        self._client = client
        self._client.set_disconnected_callback(lambda _: self.events.on_disconnect())

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    async def async_disconnect(self) -> None:
        self._client.set_disconnected_callback(None)
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
        data = await self._client.read_gatt_char(READ_STATE_UUID, use_cached=use_cached)
        return state_from_char_data(data)

    async def async_listen_for_state_changes(self) -> None:
        await self._client.start_notify(
            READ_STATE_UUID,
            lambda _, data: self.events.on_state_change(state_from_char_data(data)),
        )

    async def _async_write_command(self, command: CommandId, data: bytes) -> None:
        if not self._client.is_connected:
            return

        payload = bytes([command]) + data

        await self._client.write_gatt_char(WRITE_STATE_UUID, payload, False)


def state_from_char_data(data: bytes) -> SnoozDeviceState:
    volume = data[0]
    on = data[1] == 0x01
    return SnoozDeviceState(on, volume)


def char_data_from_state(state: SnoozDeviceState) -> bytearray:
    if state.volume is None:
        raise ValueError("Volume must be specified")

    return bytearray([state.volume, 0x01 if state.on else 0x00, *([0] * 18)])
