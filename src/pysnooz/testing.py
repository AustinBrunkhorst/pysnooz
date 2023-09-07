"""Utilities for integration testing Snooz devices."""

from __future__ import annotations

from typing import Any, Awaitable, Callable
from unittest.mock import MagicMock

from bleak import BleakClient, BLEDevice
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.service import BleakGATTServiceCollection

from pysnooz import SnoozDevice, SnoozDeviceState, UnknownSnoozState
from pysnooz.api import (
    READ_STATE_CHARACTERISTIC,
    WRITE_STATE_CHARACTERISTIC,
    READ_COMMAND_CHARACTERISTIC,
    Command,
    SnoozDeviceApi,
)
from pysnooz.const import (
    FIRMWARE_REVISION_CHARACTERISTIC,
    HARDWARE_REVISION_CHARACTERISTIC,
    MANUFACTURER_NAME_CHARACTERISTIC,
    MODEL_NUMBER_CHARACTERISTIC,
    SOFTWARE_REVISION_CHARACTERISTIC,
    WRITE_OTA_CHARACTERISTIC,
    SnoozDeviceModel,
)


class MockSnoozDevice(SnoozDevice):
    """Used for testing integration with Bleak."""

    def __init__(
        self,
        address_or_ble_device: BLEDevice | str,
        initial_state: SnoozDeviceState = SnoozDeviceState(),
    ) -> None:
        """Create a mock snooz device that does not make any bluetooth calls."""
        super().__init__(address_or_ble_device, "")

        def _on_disconnected(_: BleakClient) -> None:
            if self._api is not None:
                self._api.events.on_disconnect()

        self.state = initial_state
        self._mock_client = MockSnoozClient(address_or_ble_device, _on_disconnected)
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


class MockSnoozClient(BleakClient):
    """Used for testing integration with Bleak."""

    def __init__(  # pylint: disable=super-init-not-called
        self,
        address_or_ble_device: BLEDevice | str,
        disconnected_callback: Callable[[BleakClient], None] | None = None,
        model=SnoozDeviceModel.ORIGINAL,
        **kwargs: Any,
    ):
        self._is_connected = True
        self._state = SnoozDeviceState(on=False, volume=10)
        self._disconnected_callback = disconnected_callback
        self._model = model

        self._has_set_token = False
        self._notify_callback: dict[
            str,
            Callable[[BleakGATTCharacteristic, bytearray], None | Awaitable[None]]
            | None,
        ] = {}
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
                WRITE_OTA_CHARACTERISTIC,
            ]:
                raise Exception(f"Unexpected char uuid: {uuid}")
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
        self._on_state_update()

    def reset_mock(self, initial_state: bool = False) -> None:
        """Reset the mock state."""
        self._is_connected = True
        self._has_set_token = False
        self._notify_callback = {}
        self._services.reset_mock()

        if initial_state:
            self._state = SnoozDeviceState(on=False, volume=10)

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

        model_chars = {
            SnoozDeviceModel.ORIGINAL: {
                MODEL_NUMBER_CHARACTERISTIC: "V2",
                FIRMWARE_REVISION_CHARACTERISTIC: "3",
                HARDWARE_REVISION_CHARACTERISTIC: "2",
                SOFTWARE_REVISION_CHARACTERISTIC: "",
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
        mock_values = {
            **model_chars[self._model],
            MANUFACTURER_NAME_CHARACTERISTIC: "Snooz",
        }
        return bytearray(mock_values[char_specifier.uuid] or "", "utf-8")

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

        command_id = data[0]

        if command_id == Command.PASSWORD:
            self._has_set_token = True
            return

        if command_id == Command.MOTOR_ENABLED:
            self._state.on = data[1] == 1
        elif command_id == Command.MOTOR_SPEED:
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
        char_specifier: BleakGATTCharacteristic,
        callback: Callable[
            [BleakGATTCharacteristic, bytearray], None | Awaitable[None]
        ],
        **kwargs: Any,
    ) -> None:
        verify_notify_char(char_specifier)

        self._notify_callback[char_specifier.uuid] = callback

    async def stop_notify(self, char_specifier: BleakGATTCharacteristic) -> None:
        verify_notify_char(char_specifier)

        self._notify_callback[char_specifier.uuid] = None

    def _on_state_update(self) -> None:
        if self._notify_callback[READ_STATE_CHARACTERISTIC] is None:
            return

        # pass None since it's unused by SnoozDeviceApi
        self._notify_callback[READ_STATE_CHARACTERISTIC](
            None, self._get_state_char_data()
        )

    def _get_state_char_data(self) -> bytearray:
        return pack_state(self._state)


def verify_notify_char(char_specifier: BleakGATTCharacteristic):
    if char_specifier.uuid not in [
        READ_STATE_CHARACTERISTIC,
        READ_COMMAND_CHARACTERISTIC,
    ]:
        raise Exception(f"Unexpected char uuid: {char_specifier}")


def pack_state(state: SnoozDeviceState) -> bytearray:
    """Converts device data to device state"""
    if state.volume is None:
        raise ValueError("Volume must be specified")

    return bytearray(
        [
            state.volume,
            0x01 if state.on else 0x00,
            state.fan_speed or 0x00,
            0x01 if state.fan_on else 0x00,
            *([0] * 16),
        ]
    )
