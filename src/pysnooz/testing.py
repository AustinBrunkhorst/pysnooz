"""Utilities for integration testing Snooz devices."""

from __future__ import annotations
import struct

from typing import Any, Awaitable, Callable
from unittest.mock import MagicMock

from bleak import BleakClient, BLEDevice
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.service import BleakGATTServiceCollection
from bleak_retry_connector import BleakClientWithServiceCache

from pysnooz.device import DisconnectionReason, SnoozDevice
from pysnooz.api import (
    READ_STATE_CHARACTERISTIC,
    WRITE_STATE_CHARACTERISTIC,
    READ_COMMAND_CHARACTERISTIC,
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
from pysnooz.model import SnoozAdvertisementData, SnoozDeviceModel, SnoozDeviceState


class MockSnoozDevice(SnoozDevice):
    """Used for testing integration with Bleak."""

    def __init__(
        self,
        address_or_ble_device: BLEDevice | str,
        adv_data: SnoozAdvertisementData,
        initial_state: SnoozDeviceState = SnoozDeviceState(),
    ) -> None:
        """Create a mock snooz device that does not make any bluetooth calls."""
        super().__init__(address_or_ble_device, "")

        def _on_disconnected(_: BleakClient) -> None:
            if self._api is not None:
                self._api.events.on_disconnect()

        self.state = initial_state
        self._mock_client = MockSnoozClient(
            address_or_ble_device, adv_data.model, _on_disconnected
        )
        self._mock_client.trigger_state(initial_state)

        async def _create_mock_api() -> SnoozDeviceApi:
            return SnoozDeviceApi(self._mock_client)

        self._async_create_api = _create_mock_api  # type: ignore

    def trigger_disconnect(self) -> None:
        """Trigger a disconnect."""
        self._mock_client.trigger_disconnect()

    def trigger_state(self, new_state: SnoozDeviceState) -> None:
        """Trigger a new state."""
        self._mock_client.trigger_state(new_state)

    def trigger_temperature(self, temp: float) -> None:
        """Trigger a new temperature update."""
        self._mock_client.trigger_temperature(temp)

    def _on_device_disconnected(self, e) -> None:
        if self._is_manually_disconnecting:
            e.kwargs.set("reason", DisconnectionReason.USER)
        return super()._on_device_disconnected(e)


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

        self._is_connected = False

        if self._disconnected_callback is not None:
            self._disconnected_callback(self)

    def trigger_state(self, state: SnoozDeviceState) -> None:
        """Set the current state and notify subscribers."""
        self._state = state
        self._send_state_update()

    def trigger_temperature(self, temp: float) -> None:
        """Trigger a temperature update and notify subscribers."""
        self._send_response_command(
            ResponseCommand.TEMPERATURE, struct.pack("<f", temp)
        )

    def reset_mock(self, initial_state: bool = False) -> None:
        """Reset the mock state."""
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

        if char_specifier.uuid not in mock_values:
            return bytearray([])

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

        match command:
            case Command.PASSWORD:
                self._has_set_password = True
                return
            case Command.REQUEST_OTHER_SETTINGS:
                self._send_response_command(
                    ResponseCommand.SEND_OTHER_SETTINGS,
                    pack_other_settings(self._state),
                )

                return
            case Command.MOTOR_ENABLED:
                self._state.on = unpack_bool(data[1])
            case Command.MOTOR_SPEED:
                self._state.volume = max(0, min(100, int(data[1])))
            case Command.FAN_ENABLED:
                self._state.fan_on = unpack_bool(data[1])
            case Command.FAN_SPEED:
                self._state.fan_speed = max(0, min(100, int(data[1])))
            case Command.AUTO_TEMP_ENABLED:
                self._state.fan_auto_enabled = unpack_bool(data[1])
            case Command.AUTO_TEMP_THRESHOLD:
                self._state.target_temperature = max(0, data[1])
            case _:
                raise Exception(f"Unexpected command ID: {command} in {data.hex('-')}")

        self._send_state_update()

    async def write_gatt_descriptor(
        self, handle: int, data: bytes | bytearray | memoryview
    ) -> None:
        raise NotImplementedError()

    async def start_notify(
        self,
        char_specifier: BleakGATTCharacteristic,
        callback: Callable[
            [BleakGATTCharacteristic, bytearray], None | Awaitable[None]
        ],
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
        self.start_notify(char_specifier, None)

    def _send_state_update(self) -> None:
        if self._state_char_callback is None:
            return

        # pass None since it's unused by SnoozDeviceApi
        self._state_char_callback(None, self._get_state_char_data())

    def _send_response_command(self, command: ResponseCommand, payload: bytes) -> None:
        if self._command_char_callback is None:
            return

        self._command_char_callback(None, bytes([command.value]) + payload)

    def _get_state_char_data(self) -> bytearray:
        return pack_state(self._state)


def pack_state(state: SnoozDeviceState) -> bytearray:
    """Converts device data to device state"""
    if state.volume is None:
        raise ValueError("Volume must be specified")

    return bytearray(
        [
            state.volume,
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
    return bytes([0] * 10) + bytes(
        [pack_bool(state.fan_auto_enabled), state.target_temperature or 0x00]
    )


def pack_bool(value: bool | None) -> int:
    return 0x01 if value else 0x00


def unpack_bool(value: int) -> bool:
    return value == 0x01
