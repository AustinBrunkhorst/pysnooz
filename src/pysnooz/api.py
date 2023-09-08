from __future__ import annotations

import asyncio
import logging
import struct
from asyncio import Lock
from dataclasses import dataclass
from enum import IntEnum
from typing import Callable

from bleak import BleakClient, BleakGATTCharacteristic
from bleak.exc import BleakDBusError
from events import Events

from .const import (
    FIRMWARE_REVISION_CHARACTERISTIC,
    HARDWARE_REVISION_CHARACTERISTIC,
    MANUFACTURER_NAME_CHARACTERISTIC,
    MODEL_NUMBER_CHARACTERISTIC,
    READ_COMMAND_CHARACTERISTIC,
    READ_STATE_CHARACTERISTIC,
    SOFTWARE_REVISION_CHARACTERISTIC,
    WRITE_STATE_CHARACTERISTIC,
)
from .model import SnoozDeviceCharacteristicData, SnoozDeviceState

# values less than this have no effect
MIN_DEVICE_VOLUME = 10
MIN_FAN_SPEED = 10

# When auto fan is enabled, the device will poll for fan power state updates since
# the device doesn't push them. This is the interval of temperature updates to
# wait for before requesting the current state of the device.
AUTO_FAN_TEMP_POLL_INTERVAL = 5

# number of times to retry a transient command failure before giving up
RETRY_WRITE_FAILURE_COUNT = 5
RETRY_SLEEP_DURATIONS = [0, 0.5, 1, 1, 2]
DBUS_ERRORS_TO_RETRY = (
    "org.bluez.Error",
    "org.bluez.Error.Failed",
    "org.bluez.Error.InProgress",
)

_LOGGER = logging.getLogger(__name__)


class Command(IntEnum):
    MOTOR_SPEED = 1
    MOTOR_ENABLED = 2
    TOP_LED = 3
    BOTTOM_LED = 4
    TURN_OFF_TIMER = 5
    PASSWORD = 6
    UPDATE_STATUS = 7
    TURN_ON_TIMER = 8
    SET_ON_TIMERS = 9
    SET_OFF_TIMERS = 10
    SYNC_TIME = 11
    SCHEDULE_REQUEST = 12
    NIGHTLIGHT = 13
    FADE_ON_TIME = 14
    FADE_OFF_TIME = 15
    REQUEST_FADE_TIMES = 16
    CAPBUTTON_POWER = 17
    CAPBUTTON_FASTER = 18
    CAPBUTTON_SLOWER = 19
    CAPBUTTON_NIGHTLIGHT = 20
    CAPBUTTON_DEBOUNCE = 21
    CAPBUTTON_SAMPLE_ARRAY = 22
    REQUEST_CAPBUTTON = 23
    CAPBUTTON_IIR_CO = 24
    SMARTPLUG_MODE = 25
    SET_FADE_SETTINGS = 26
    REQUEST_OTHER_SETTINGS = 27
    SET_TIMEZONE = 28
    SET_TIMEZONE_2 = 29
    SET_REAL_TIME = 30
    FAN_SPEED = 31
    FAN_ENABLED = 32
    AUTO_TEMP_ENABLED = 33
    AUTO_TEMP_THRESHOLD = 34
    ENABLE_LAST_POWERED_STATE = 35


class ResponseCommand(IntEnum):
    SEND_ON_SCHEDULE = 1
    SEND_OFF_SCHEDULE = 2
    SEND_FADE_SETTINGS = 3
    SEND_NIGHTLIGHT = 4
    SEND_CAPBUTTON = 5
    SEND_OTHER_SETTINGS = 6
    OTA_IDX = 7
    OTA_FAILED = 8
    TEMPERATURE = 9


class MissingCharacteristicError(Exception):
    """Raised when a required characteristic is missing on a client"""

    def __init__(self, uuid: str | None = None) -> None:
        super().__init__(f"Missing characteristic {uuid}")


@dataclass
class CharacteristicReference:
    uuid: str
    required: bool = True

    def get(self, client: BleakClient) -> BleakGATTCharacteristic:
        char = client.services.get_characteristic(self.uuid)

        if char is None and self.required:
            raise MissingCharacteristicError(self.uuid)

        return char


class SnoozDeviceApi:
    event_names = ("on_disconnect", "on_state_patched")

    def __init__(
        self,
        client: BleakClient | None = None,
        format_log_message: Callable[[str], str] | None = None,
    ) -> None:
        self.unsubscribe_all_events()
        self._client = client
        self._write_lock = Lock()
        self._ = format_log_message or (lambda msg: msg)
        self._read_state_char = CharacteristicReference(READ_STATE_CHARACTERISTIC)
        self._read_command_char = CharacteristicReference(READ_COMMAND_CHARACTERISTIC)
        self._write_state_char = CharacteristicReference(WRITE_STATE_CHARACTERISTIC)
        self._info_chars = [
            CharacteristicReference(MANUFACTURER_NAME_CHARACTERISTIC),
            CharacteristicReference(MODEL_NUMBER_CHARACTERISTIC),
            CharacteristicReference(HARDWARE_REVISION_CHARACTERISTIC),
            CharacteristicReference(FIRMWARE_REVISION_CHARACTERISTIC),
            # Older Snooz devices don't have this
            CharacteristicReference(SOFTWARE_REVISION_CHARACTERISTIC, required=False),
        ]
        self._required_chars = [
            *[
                ref
                for ref in [getattr(self, c) for c in dir(self)]
                if isinstance(ref, CharacteristicReference) and ref.required
            ],
            *[ref for ref in self._info_chars if ref.required],
        ]

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    def load_client(self, client: BleakClient) -> None:
        self._client = client
        self._info = None

        for char in self._required_chars:
            char.get(client)

    def _require_client(self, require_connection: bool = True) -> BleakClient:
        if self._client is None:
            raise AssertionError("client was None")

        if require_connection and not self._client.is_connected:
            raise AssertionError("client was not connected")

        return self._client

    def unsubscribe_all_events(self) -> None:
        self.events = Events(self.event_names)

    async def async_disconnect(self) -> None:
        client = self._require_client()

        await client.disconnect()

    async def async_get_info(self) -> SnoozDeviceCharacteristicData | None:
        client = self._require_client(False)
        if not client.is_connected:
            return None
        string_props: list[str | None] = []
        for char_ref in self._info_chars:
            char = char_ref.get(client)
            if not char:
                value = None
            else:
                value = (await client.read_gatt_char(char)).decode().split("\0")[0]
            string_props.append(value)

        return SnoozDeviceCharacteristicData(*string_props)  # type: ignore

    async def async_authenticate_connection(self, password: str) -> None:
        await self._async_write_state(
            bytes([Command.PASSWORD, *bytes.fromhex(password)])
        )

    async def async_set_power(self, on: bool) -> None:
        await self._async_write_state(bytes([Command.MOTOR_ENABLED, 1 if on else 0]))

    async def async_set_fan_power(self, on: bool) -> None:
        await self._async_write_state(bytes([Command.FAN_ENABLED, 1 if on else 0]))

    async def async_set_auto_temp_enabled(self, on: bool) -> None:
        await self._async_write_state(
            bytes([Command.AUTO_TEMP_ENABLED, 1 if on else 0])
        )
        await self.async_request_other_settings()

    async def async_set_volume(self, volume: int) -> None:
        if volume < 0 or volume > 100:
            raise ValueError(f"Volume must be between 0 and 100 - got {volume}")

        await self._async_write_state(bytes([Command.MOTOR_SPEED, volume]))

    async def async_set_fan_speed(self, speed: int) -> None:
        if speed < 0 or speed > 100:
            raise ValueError(f"Speed must be between 0 and 100 - got {speed}")

        await self._async_write_state(bytes([Command.FAN_SPEED, speed]))

    async def async_set_auto_temp_threshold(self, threshold_f: int) -> None:
        if threshold_f < 0 or threshold_f > 100:
            raise ValueError(
                f"Temperature must be between 0 and 100 - got {threshold_f}"
            )

        await self._async_write_state(bytes([Command.AUTO_TEMP_THRESHOLD, threshold_f]))
        await self.async_request_other_settings()

    async def async_read_state(self, use_cached: bool = False) -> SnoozDeviceState:
        client = self._require_client()

        data = await client.read_gatt_char(
            self._read_state_char.get(client), use_cached=use_cached
        )
        return unpack_state(data)

    async def async_subscribe(self) -> None:
        client = self._require_client(False)

        if not client.is_connected:
            return

        def on_state_change(_: BleakClient, payload: bytes) -> None:
            self.events.on_state_patched(unpack_state(payload))

        await client.start_notify(
            self._read_state_char.get(client),
            on_state_change,
        )

        def on_response_command(_: BleakClient, data: bytes) -> None:
            command = ResponseCommand(data[0])
            payload = data[1:]

            self.events.on_state_patched(unpack_response_command(command, payload))

        await client.start_notify(
            self._read_command_char.get(client), on_response_command
        )

    async def async_request_other_settings(self) -> None:
        await self._async_write_state(bytes([Command.REQUEST_OTHER_SETTINGS]))

    async def _async_write_state(self, data: bytes) -> None:
        client = self._require_client(False)

        attempts = 0

        async with self._write_lock:
            last_ex: BleakDBusError | None = None

            while client.is_connected and attempts <= RETRY_WRITE_FAILURE_COUNT:
                try:
                    message = f"write {data.hex('-')}"
                    if attempts > 0 and last_ex is not None:
                        message += f" (attempt {attempts+1}, last error: {last_ex})"
                    _LOGGER.debug(self._(message))
                    await client.write_gatt_char(
                        self._write_state_char.get(client), data, response=True
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


def unpack_response_command(command: ResponseCommand, data: bytes) -> SnoozDeviceState:
    result = SnoozDeviceState()

    if command == ResponseCommand.SEND_OTHER_SETTINGS:
        (auto_enabled, target_temperature) = struct.unpack("<xxxxxxxxxxBB", data[0:12])

        result.fan_auto_enabled = bool(auto_enabled)
        result.target_temperature = target_temperature
    if command == ResponseCommand.TEMPERATURE:
        [temp] = struct.unpack("<f", data[0:4])
        result.temperature = round(temp, 2)

    return result


def unpack_state(data: bytes) -> SnoozDeviceState:
    (volume, on, fan_speed, fan_on) = struct.unpack("<BBxBB", data[0:5])

    return SnoozDeviceState(
        volume=volume,
        on=bool(on),
        fan_on=bool(fan_on),
        fan_speed=fan_speed,
    )
