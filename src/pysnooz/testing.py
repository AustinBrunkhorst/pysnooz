"""Utilities for integration testing Snooz devices."""

from __future__ import annotations

import dataclasses
import logging
import struct
from typing import Any, Awaitable, Callable
from unittest.mock import MagicMock

from bleak import BleakClient, BLEDevice
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.service import BleakGATTServiceCollection
from bleak_retry_connector import BleakClientWithServiceCache

from pysnooz.api import (
    READ_COMMAND_CHARACTERISTIC,
    READ_STATE_CHARACTERISTIC,
    WRITE_STATE_CHARACTERISTIC,
    Command,
    ResponseCommand,
    SnoozDeviceApi,
)
from pysnooz.const import (
    FIRMWARE_REVISION_CHARACTERISTIC,
    HARDWARE_REVISION_CHARACTERISTIC,
    MANUFACTURER_NAME_CHARACTERISTIC,
    MODEL_NUMBER_CHARACTERISTIC,
    SOFTWARE_REVISION_CHARACTERISTIC,
)
from pysnooz.device import SnoozDevice
from pysnooz.model import SnoozAdvertisementData, SnoozDeviceModel, SnoozDeviceState

_LOGGER = logging.getLogger(__name__)


class MockSnoozDevice(SnoozDevice):
    """Used for testing integration with Bleak."""

    def __init__(
        self,
        address_or_ble_device: BLEDevice | str,
        adv_data: SnoozAdvertisementData,
        initial_state: SnoozDeviceState = SnoozDeviceState(),
    ) -> None:
        """Create a mock snooz device that does not make any bluetooth calls."""
        super().__init__(address_or_ble_device, adv_data)

        def _on_disconnected(_: BleakClient) -> None:
            if self._api is not None and not self._expected_disconnect:
                self._api.events.on_disconnect()

        state_copy = dataclasses.replace(initial_state)
        self._store.current = state_copy
        self._mock_client = MockSnoozClient(
            address_or_ble_device, adv_data.model, _on_disconnected
        )
        self._mock_client.trigger_state(state_copy)

        async def _create_mock_api() -> SnoozDeviceApi:
            self._mock_client.reset_mock()
            return SnoozDeviceApi(self._mock_client)

        self._async_create_api = _create_mock_api  # type: ignore

    def trigger_disconnect(self) -> None:
        """Trigger a disconnect."""
        if self._api is not None:
            self._mock_client.trigger_disconnect()

    def trigger_state(self, new_state: SnoozDeviceState) -> None:
        """Trigger a new state."""
        if self._api is not None:
            self._mock_client.trigger_state(new_state)

    def trigger_temperature(self, temp: float) -> None:
        """Trigger a new temperature update."""
        if self._api is not None:
            self._mock_client.trigger_temperature(temp)


CharNotifyCallback = Callable[
    [BleakGATTCharacteristic, bytearray], None | Awaitable[None]
]


class MockSnoozClient(BleakClientWithServiceCache):
    """Used for testing integration with Bleak."""

    def __init__(  # pylint: disable=super-init-not-called
        self,
        address_or_ble_device: BLEDevice | str,
        model: SnoozDeviceModel,
        disconnected_callback: Callable[[BleakClient], None] | None = None,
        **kwargs: Any,
    ):
        self._is_connected = True
        self._state = SnoozDeviceState(on=False, volume=10)
        if model == SnoozDeviceModel.BREEZ:
            self._state.fan_on = False
            self._state.fan_speed = 10
        self._disconnected_callback = disconnected_callback
        self._model = model

        self._has_set_password = False
        self._state_char_callback: CharNotifyCallback | None = None
        self._command_char_callback: CharNotifyCallback | None = None
        self._services = MagicMock(spec=BleakGATTServiceCollection)

        def mock_char(uuid: str) -> BleakGATTCharacteristic:
            if uuid not in [
                MODEL_NUMBER_CHARACTERISTIC,
                FIRMWARE_REVISION_CHARACTERISTIC,
                HARDWARE_REVISION_CHARACTERISTIC,
                SOFTWARE_REVISION_CHARACTERISTIC,
                MANUFACTURER_NAME_CHARACTERISTIC,
                READ_STATE_CHARACTERISTIC,
                WRITE_STATE_CHARACTERISTIC,
                READ_COMMAND_CHARACTERISTIC,
            ]:
                raise Exception(f"Unexpected char uuid: {uuid}")

            if (
                uuid == SOFTWARE_REVISION_CHARACTERISTIC
                and self._model == SnoozDeviceModel.ORIGINAL
            ):
                return None

            return MagicMock(spec=BleakGATTCharacteristic, uuid=uuid)

        self._services.get_characteristic.side_effect = mock_char

    @property
    def services(self) -> BleakGATTServiceCollection:
        return self._services

    async def connect(self, **kwargs: Any) -> bool:
        self._is_connected = True
        return True

    async def disconnect(self) -> bool:
        self.trigger_disconnect()

        return True

    def trigger_disconnect(self) -> None:
        """Set the device as disconnected and trigger callbacks."""
        if not self._is_connected:
            return

        _LOGGER.debug("Triggering device disconnect")

        self._is_connected = False

        if self._disconnected_callback is not None:
            self._disconnected_callback(self)

    def trigger_state(self, state: SnoozDeviceState) -> None:
        """Set the current state and notify subscribers."""
        _LOGGER.debug(f"Triggering state update {state}")

        self._state = dataclasses.replace(state)
        self._send_state_update()

    def trigger_temperature(self, temp: float) -> None:
        """Trigger a temperature update and notify subscribers."""
        _LOGGER.debug("Triggering temperature update {temp}")

        self._send_response_command(
            ResponseCommand.TEMPERATURE, struct.pack("<f", temp)
        )

    def reset_mock(self, initial_state: bool = False) -> None:
        """Reset the mock state."""
        _LOGGER.debug("Resetting mock client")
        self._is_connected = True
        self._has_set_password = False
        self._state_char_callback = None
        self._command_char_callback = None
        self._services.reset_mock()

        if initial_state:
            self._state = SnoozDeviceState(on=False, volume=10)

            if self._model == SnoozDeviceModel.BREEZ:
                self._state.fan_on = False
                self._state.fan_speed = 10

    async def pair(self, *args: Any, **kwargs: Any) -> bool:
        raise NotImplementedError()

    async def unpair(self) -> bool:
        raise NotImplementedError()

    @property
    def mtu_size(self) -> int:
        raise NotImplementedError()

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    async def get_services(self, **kwargs: Any) -> BleakGATTServiceCollection:
        return self._services

    async def read_gatt_char(
        self,
        char_specifier: BleakGATTCharacteristic,
        **kwargs: Any,
    ) -> bytearray:
        if char_specifier.uuid == READ_STATE_CHARACTERISTIC:
            return self._get_state_char_data()

        mock_values = {
            **CHAR_VALUES_BY_MODEL[self._model],
            MANUFACTURER_NAME_CHARACTERISTIC: "Snooz",
        }

        return bytearray(mock_values[char_specifier.uuid], "utf-8")

    async def read_gatt_descriptor(self, handle: int, **kwargs: Any) -> bytearray:
        raise NotImplementedError()

    async def write_gatt_char(
        self,
        char_specifier: BleakGATTCharacteristic,
        data: bytes | bytearray | memoryview,
        response: bool = False,
    ) -> None:
        if char_specifier.uuid != WRITE_STATE_CHARACTERISTIC:
            raise Exception(f"Unexpected char specifier: {char_specifier.uuid}")

        command = data[0]

        if command == Command.PASSWORD:
            self._has_set_password = True
            _LOGGER.debug(f"Received password: {data[1:].hex()}")
            return

        if self._has_set_password:
            if command == Command.REQUEST_OTHER_SETTINGS:
                self._send_response_command(
                    ResponseCommand.SEND_OTHER_SETTINGS,
                    pack_other_settings(self._state),
                )

                return
            elif command == Command.MOTOR_ENABLED:
                self._state.on = unpack_bool(data[1])
            elif command == Command.MOTOR_SPEED:
                self._state.volume = max(0, min(100, int(data[1])))
            elif command == Command.FAN_ENABLED:
                self._state.fan_on = unpack_bool(data[1])
            elif command == Command.FAN_SPEED:
                self._state.fan_speed = max(0, min(100, int(data[1])))
            elif command == Command.AUTO_TEMP_ENABLED:
                self._state.fan_auto_enabled = unpack_bool(data[1])
            elif command == Command.AUTO_TEMP_THRESHOLD:
                self._state.target_temperature = max(0, data[1])
            else:
                raise Exception(f"Unexpected command ID: {command} in {data.hex('-')}")
        else:
            _LOGGER.warning(
                f"Received command before password was set: {data.hex('-')}"
            )

        self._send_state_update()

    async def write_gatt_descriptor(
        self, handle: int, data: bytes | bytearray | memoryview
    ) -> None:
        raise NotImplementedError()

    async def start_notify(
        self,
        char_specifier: BleakGATTCharacteristic,
        callback: CharNotifyCallback | None,
        **kwargs: Any,
    ) -> None:
        uuid = char_specifier.uuid

        if uuid == READ_STATE_CHARACTERISTIC:
            self._state_char_callback = callback
        elif uuid == READ_COMMAND_CHARACTERISTIC:
            self._command_char_callback = callback
        else:
            raise Exception(f"Unexpected notification characteristic: {uuid}")

    async def stop_notify(self, char_specifier: BleakGATTCharacteristic) -> None:
        await self.start_notify(char_specifier, None)

    def _send_state_update(self) -> None:
        if self._state_char_callback is None:
            return

        # pass None since it's unused by SnoozDeviceApi
        self._state_char_callback(
            None,
            self._get_state_char_data() if self._has_set_password
            # when a password isn't set, the device sends a zeroed out state
            else bytearray([0] * 20),
        )

    def _send_response_command(self, command: ResponseCommand, payload: bytes) -> None:
        if self._command_char_callback is None:
            return

        self._command_char_callback(None, bytearray([command.value]) + payload)

    def _get_state_char_data(self) -> bytearray:
        return pack_state(self._state)


def pack_state(state: SnoozDeviceState) -> bytearray:
    """Converts device data to device state"""
    return bytearray(
        [
            state.volume or 0x00,
            pack_bool(state.on),
            0x00,
            state.fan_speed or 0x00,
            pack_bool(state.fan_on),
            *([0] * 15),
        ]
    )


CHAR_VALUES_BY_MODEL = {
    SnoozDeviceModel.ORIGINAL: {
        MODEL_NUMBER_CHARACTERISTIC: "V2",
        FIRMWARE_REVISION_CHARACTERISTIC: "3",
        HARDWARE_REVISION_CHARACTERISTIC: "2",
    },
    SnoozDeviceModel.PRO: {
        MODEL_NUMBER_CHARACTERISTIC: "V4",
        FIRMWARE_REVISION_CHARACTERISTIC: "4.0",
        HARDWARE_REVISION_CHARACTERISTIC: "2",
        SOFTWARE_REVISION_CHARACTERISTIC: "v4.0-7-g4ba90ad2e",
    },
    SnoozDeviceModel.BREEZ: {
        MODEL_NUMBER_CHARACTERISTIC: "V4",
        FIRMWARE_REVISION_CHARACTERISTIC: "4.0",
        HARDWARE_REVISION_CHARACTERISTIC: "0",
        SOFTWARE_REVISION_CHARACTERISTIC: "v4.0-7-g4ba90ad2e",
    },
}


def pack_other_settings(state: SnoozDeviceState) -> bytearray:
    return bytearray([0] * 10) + bytearray(
        [pack_bool(state.fan_auto_enabled), state.target_temperature or 0x00]
    )


def pack_bool(value: bool | None) -> int:
    return 0x01 if value else 0x00


def unpack_bool(value: int) -> bool:
    return value == 0x01
