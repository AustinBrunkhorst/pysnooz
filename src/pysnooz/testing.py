from __future__ import annotations

import uuid
from typing import Any, Callable

from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.client import BaseBleakClient
from bleak.backends.service import BleakGATTServiceCollection

from pysnooz.api import READ_STATE_UUID, WRITE_STATE_UUID, CommandId, SnoozDeviceState


class MockSnoozClient(BaseBleakClient):
    _is_connected = True
    _state = SnoozDeviceState(on=False, volume=10)
    _has_set_token = False
    _notify_callback: Callable[[int, bytearray], None] | None = None

    async def connect(self) -> bool:
        self._is_connected = True
        return True

    async def disconnect(self) -> bool:
        self.trigger_disconnect()

        return True

    def trigger_disconnect(self) -> None:
        if not self._is_connected:
            return

        self._is_connected = False

        if self._disconnected_callback is not None:
            self._disconnected_callback(self)

    def trigger_state(self, state: SnoozDeviceState) -> None:
        self._state = state
        self._on_state_update()

    def reset_mock(self, initial_state: bool = False) -> None:
        self._is_connected = True
        self._has_set_token = False
        self._notify_callback = None

        if initial_state:
            self._state = SnoozDeviceState(on=False, volume=10)

    async def pair(self) -> bool:
        raise NotImplementedError()

    async def unpair(self) -> bool:
        raise NotImplementedError()

    @property
    def mtu_size(self) -> int:
        raise NotImplementedError()

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    async def get_services(self) -> BleakGATTServiceCollection:
        raise NotImplementedError()

    async def read_gatt_char(
        self,
        char_specifier: BleakGATTCharacteristic | int | str | uuid.UUID,
        **kwargs: Any,
    ) -> bytearray:
        if char_specifier != READ_STATE_UUID:
            raise Exception(f"Unexpected char specifier: {char_specifier}")

        return self._get_state_char_data()

    async def read_gatt_descriptor(self, handle: int) -> bytearray:
        raise NotImplementedError()

    async def write_gatt_char(
        self,
        char_specifier: BleakGATTCharacteristic | int | str | uuid.UUID,
        data: bytes | bytearray | memoryview,
        response: bool = False,
    ) -> None:
        if char_specifier != WRITE_STATE_UUID:
            raise Exception(f"Unexpected char specifier: {char_specifier}")

        command_id = data[0]

        if command_id == CommandId.SET_TOKEN:
            self._has_set_token = True
            return

        if command_id == CommandId.SET_POWER:
            self._state.on = data[1] == 1
        elif command_id == CommandId.SET_VOLUME:
            self._state.volume = max(0, min(100, data[1]))
        else:
            raise Exception(f"Unexpected state data: {str(data)}")

        self._on_state_update()

    async def write_gatt_descriptor(
        self, handle: int, data: bytes | bytearray | memoryview
    ) -> None:
        raise NotImplementedError()

    async def start_notify(
        self,
        char_specifier: BleakGATTCharacteristic | int | str | uuid.UUID,
        callback: Callable[[int, bytearray], None],
    ) -> None:
        if char_specifier != READ_STATE_UUID:
            raise Exception(f"Unexpected char specifier: {char_specifier}")

        self._notify_callback = callback

    async def stop_notify(
        self, char_specifier: BleakGATTCharacteristic | int | str | uuid.UUID
    ) -> None:
        if char_specifier != READ_STATE_UUID:
            raise Exception(f"Unexpected char specifier: {char_specifier}")

        self._notify_callback = None

    def _on_state_update(self) -> None:
        if self._notify_callback is None:
            return

        self._notify_callback(0, self._get_state_char_data())

    def _get_state_char_data(self) -> bytearray:
        return char_data_from_state(self._state)


def char_data_from_state(state: SnoozDeviceState) -> bytearray:
    if state.volume is None:
        raise ValueError("Volume must be specified")

    return bytearray([state.volume, 0x01 if state.on else 0x00, *([0] * 18)])
