from __future__ import annotations

import asyncio
import dataclasses
import struct
import logging
from asyncio import Event, Lock
from enum import IntEnum
from typing import Callable
from attr import dataclass

from bleak import BleakClient
from bleak.exc import BleakDBusError
from events import Events

from .const import (
    FIRMWARE_REVISION_CHARACTERISTIC,
    HARDWARE_REVISION_CHARACTERISTIC,
    MANUFACTURER_NAME_CHARACTERISTIC,
    MODEL_NUMBER_CHARACTERISTIC,
    READ_STATE_CHARACTERISTIC,
    READ_COMMAND_CHARACTERISTIC,
    SOFTWARE_REVISION_CHARACTERISTIC,
    WRITE_STATE_CHARACTERISTIC,
    SnoozDeviceInfo,
    SnoozDeviceModel,
    SnoozDeviceState,
    UnknownSnoozState,
)

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


class SnoozDeviceApi:
    def __init__(
        self,
        client: BleakClient | None = None,
        format_log_message: Callable[[str], str] | None = None,
    ) -> None:
        self.state = UnknownSnoozState
        self.unsubscribe_all_events()
        self._client = client
        self._device_info: SnoozDeviceInfo | None = None
        self._write_lock = Lock()
        self._other_settings_received = Event()
        self._ = format_log_message or (lambda msg: msg)

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    def set_client(self, client: BleakClient) -> None:
        self._client = client

    def unsubscribe_all_events(self) -> None:
        self.events = Events(("on_disconnect", "on_state_change"))

    async def async_disconnect(self) -> None:
        if self._client is None:
            raise Exception("self._client was None")
        await self._client.disconnect()

    async def async_get_info(self) -> SnoozDeviceInfo | None:
        if self._client is None:
            raise Exception("self._client was None")

        if not self.is_connected:
            return None

        char_props = []
        for char_uuid in (
            MANUFACTURER_NAME_CHARACTERISTIC,
            MODEL_NUMBER_CHARACTERISTIC,
            HARDWARE_REVISION_CHARACTERISTIC,
            FIRMWARE_REVISION_CHARACTERISTIC,
            SOFTWARE_REVISION_CHARACTERISTIC,
        ):
            char = self._client.services.get_characteristic(char_uuid)
            # Older Snooz devices don't have SOFTWARE_REVISION_CHARACTERISTIC
            if not char:
                value = None
            else:
                value = (
                    (await self._client.read_gatt_char(char)).decode().split("\0")[0]
                )
            char_props.append(value)

        data = SnoozDeviceCharacteristicData(*char_props)
        model = get_device_model(data)

        self.state = await self.async_read_state()

        if model == SnoozDeviceModel.BREEZ:
            await self._request_other_settings()
            _LOGGER.debug(self._("Waiting for settings"))
            await self._other_settings_received.wait()

        # result is cached in memory
        self._device_info = SnoozDeviceInfo(
            model=model,
            state=self.state,
            manufacturer=data.manufacturer,
            hardware=data.hardware,
            firmware=data.firmware,
            software=data.software,
        )

        return self._device_info

    async def async_authenticate_connection(self, token: bytes) -> None:
        await self._async_write_state(bytes([Command.PASSWORD, *token]))

    async def async_set_power(self, on: bool) -> None:
        await self._async_write_state(bytes([Command.MOTOR_ENABLED, 1 if on else 0]))

    async def async_set_fan_enabled(self, on: bool) -> None:
        await self._async_write_state(bytes([Command.FAN_ENABLED, 1 if on else 0]))

    async def async_set_auto_temp_enabled(self, on: bool) -> None:
        await self._async_write_state(
            bytes([Command.AUTO_TEMP_ENABLED, 1 if on else 0])
        )

    async def async_set_volume(self, volume: int) -> None:
        if volume < 0 or volume > 100:
            raise ValueError(f"Volume must be between 0 and 100 - got {volume}")

        await self._async_write_state(bytes([Command.MOTOR_SPEED, volume]))

    async def async_set_fan_speed(self, speed: int) -> None:
        if speed < 0 or speed > 10:
            raise ValueError(f"Speed must be between 0 and 10 - got {speed}")

        await self._async_write_state(bytes([Command.FAN_SPEED, speed]))

    async def async_set_auto_temp_threshold(self, threshold_f: int) -> None:
        if threshold_f < 0 or threshold_f > 100:
            raise ValueError(
                f"Temperature must be between 0 and 100 - got {threshold_f}"
            )

        await self._async_write_state(bytes([Command.AUTO_TEMP_THRESHOLD, threshold_f]))
        await self._request_other_settings()

    async def async_read_state(self, use_cached: bool = False) -> SnoozDeviceState:
        if self._client is None:
            raise Exception("self._client was None")

        data = await self._client.read_gatt_char(
            READ_STATE_CHARACTERISTIC, use_cached=use_cached
        )
        return unpack_state(data)

    async def async_subscribe_to_notifications(self) -> None:
        if self._client is None:
            raise Exception("self._client was None")

        if not self._client.is_connected:
            return

        def on_state_update(_, data: bytes) -> None:
            _LOGGER.debug(self._(f"Receive state {data.hex('-')}"))
            self._update_state(combine_state(self.state, unpack_state(data)))

        def on_response_command(_, data: bytes) -> None:
            command = ResponseCommand(data[0])
            payload = data[1:]

            _LOGGER.debug(self._(f"Receive {command} {payload.hex('-')}"))

            next_state = reduce_response_command(self.state, command, payload)
            self._update_state(next_state)

            if command == ResponseCommand.SEND_OTHER_SETTINGS:
                self._other_settings_received.set()

        await self._client.start_notify(
            READ_STATE_CHARACTERISTIC,
            on_state_update,
        )
        await self._client.start_notify(
            READ_COMMAND_CHARACTERISTIC, on_response_command
        )

    async def _request_other_settings(self) -> None:
        await self._async_write_state(bytes([Command.REQUEST_OTHER_SETTINGS]))

    def _update_state(self, next_state: SnoozDeviceState) -> None:
        did_change = next_state != self.state
        self.state = next_state

        if did_change:
            _LOGGER.debug(self._(f"State change {self.state}"))
            self.events.on_state_change(self.state)

    async def _async_write_state(self, data: bytes | None = None) -> None:
        assert self._client

        attempts = 0

        async with self._write_lock:
            last_ex: BleakDBusError | None = None

            while self._client.is_connected and attempts <= RETRY_WRITE_FAILURE_COUNT:
                try:
                    message = f"write {data.hex('-')}"
                    if attempts > 0 and last_ex is not None:
                        message += f" (attempt {attempts+1}, last error: {last_ex})"
                    _LOGGER.debug(self._(message))
                    await self._client.write_gatt_char(
                        WRITE_STATE_CHARACTERISTIC, data, response=True
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


@dataclass
class SnoozDeviceCharacteristicData:
    manufacturer: str
    model: str
    hardware: str
    firmware: str
    software: str | None


def get_device_model(data: SnoozDeviceCharacteristicData) -> SnoozDeviceModel:
    if data.model == "V4":
        return SnoozDeviceModel.BREEZ if data.hardware == "0" else SnoozDeviceModel.PRO

    return SnoozDeviceModel.ORIGINAL


def combine_state(
    current: SnoozDeviceState, update: SnoozDeviceState
) -> SnoozDeviceState:
    result = copy_state(current)

    result.volume = update.volume
    result.on = update.on

    return result


def reduce_response_command(
    state: SnoozDeviceState, command: ResponseCommand, data: bytes
) -> SnoozDeviceState:
    result = copy_state(state)

    match command:
        case ResponseCommand.SEND_OTHER_SETTINGS:
            result.fan_speed = int(data[3])
            result.fan_auto_enabled = data[10] == 0x01
            result.target_temperature = int(data[11])
        case ResponseCommand.TEMPERATURE:
            [temp] = struct.unpack("<f", data[0:4])
            result.temperature = round(temp, 2)

    return result


def unpack_state(data: bytes) -> SnoozDeviceState:
    (volume, on) = struct.unpack("<BB", data[0:2])

    return SnoozDeviceState(
        volume=volume,
        on=on == 0x01,
    )


def copy_state(state: SnoozDeviceState) -> SnoozDeviceState:
    return SnoozDeviceState(**dataclasses.asdict(state))
