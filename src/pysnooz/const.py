from dataclasses import dataclass
from enum import Enum
from typing import Any

NEW_ISSUE_URL = (
    "https://github.com/AustinBrunkhorst/pysnooz/issues/new?labels=bug"
    "&template=log-unexpected-error.yaml&title=Uncaught+exception"
)
UNEXPECTED_ERROR_LOG_MESSAGE = (
    f"1️⃣  Report this issue: {NEW_ISSUE_URL}\n"
    "2️⃣  ⬇ copy the trace and paste in the issue ⬇\n"
)

MODEL_NUMBER_CHARACTERISTIC = "00002a24-0000-1000-8000-00805f9b34fb"
FIRMWARE_REVISION_CHARACTERISTIC = "00002a26-0000-1000-8000-00805f9b34fb"
HARDWARE_REVISION_CHARACTERISTIC = "00002a27-0000-1000-8000-00805f9b34fb"
SOFTWARE_REVISION_CHARACTERISTIC = "00002a28-0000-1000-8000-00805f9b34fb"
MANUFACTURER_NAME_CHARACTERISTIC = "00002a29-0000-1000-8000-00805f9b34fb"
READ_STATE_CHARACTERISTIC = "80c37f00-cc16-11e4-8830-0800200c9a66"
WRITE_STATE_CHARACTERISTIC = "90759319-1668-44da-9ef3-492d593bd1e5"
READ_COMMAND_CHARACTERISTIC = "f0499b1b-33ab-4df8-a6f2-2484a2ad1451"


class SnoozDeviceModel(Enum):
    ORIGINAL = 0
    PRO = 1
    BREEZ = 2



@dataclass
class SnoozNoiseMachineState:
    on: bool | None = None
    volume: int | None = None


@dataclass
class BreezFanState:
    fan_on: int | None = None
    fan_speed: int | None = None
    fan_auto_enabled: bool | None = None
    temperature: float | None = None
    target_temperature: int | None = None


@dataclass
class SnoozDeviceState(SnoozNoiseMachineState, BreezFanState):
    def __eq__(self, other: Any) -> bool:
        return (
            self.on == other.on
            and self.volume == other.volume
            and self.fan_on == other.fan_on
            and self.fan_speed == other.fan_speed
            and self.fan_auto_enabled == other.fan_auto_enabled
            and self.temperature == other.temperature
            and self.target_temperature == other.target_temperature
        )

    def __repr__(self) -> str:
        if self == UnknownSnoozState:
            return "Snooz(Unknown)"

        attributes = [f"Noise {'On' if self.on else 'Off'} at {self.volume}% volume"]
        fan_attrs: list[str] = []

        if self.fan_on is not None:
            fan_attrs += [f"Fan {'On' if self.fan_on else 'Off'}"]

        if self.fan_speed is not None:
            fan_attrs += [f"at {self.fan_speed}% speed"]

        if self.fan_auto_enabled is not None:
            fan_attrs += ["[Auto]"]

        if len(fan_attrs) > 0:
            attributes += [" ".join(fan_attrs)]

        if self.temperature is not None:
            attributes += [f"{self.temperature}°F"]

        if self.target_temperature is not None:
            attributes += [f"{self.target_temperature}°F threshold"]

        parts = ", ".join(attributes)

        return f"Snooz({parts})"


UnknownSnoozState = SnoozDeviceState()


@dataclass
class SnoozDeviceInfo:
    model: SnoozDeviceModel
    state: SnoozDeviceState
    manufacturer: str
    hardware: str
    firmware: str
    software: str | None

    @property
    def supports_fan(self) -> bool:
        return self.model == SnoozDeviceModel.BREEZ
