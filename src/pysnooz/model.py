from dataclasses import dataclass
from enum import IntEnum


class SnoozDeviceModel(IntEnum):
    UNSUPPORTED = 0
    ORIGINAL = 1
    PRO = 2
    BREEZ = 3


class SnoozFirmwareVersion(IntEnum):
    V2 = 2
    V3 = 3
    V4 = 4
    V5 = 5
    V6 = 6
    V7 = 7
    V8 = 8
    V9 = 9
    V10 = 10
    V11 = 11
    V12 = 12
    V13 = 13
    V14 = 14
    V15 = 15


@dataclass
class SnoozDeviceCharacteristicData:
    manufacturer: str
    model: str
    hardware: str
    firmware: str
    software: str | None


@dataclass
class SnoozAdvertisementData:
    model: SnoozDeviceModel
    firmware_version: SnoozFirmwareVersion
    password: str | None

    @property
    def is_pairing(self) -> bool:
        return self.password is not None

    @property
    def supports_fan(self) -> bool:
        return self.model == SnoozDeviceModel.BREEZ


@dataclass(repr=False)
class SnoozDeviceState:
    on: bool | None = None
    volume: int | None = None

    # Breez specific
    fan_on: bool | None = None
    fan_speed: int | None = None
    fan_auto_enabled: bool | None = None
    temperature: float | None = None
    target_temperature: int | None = None

    def __repr__(self) -> str:
        if self == UnknownSnoozState:
            return "Snooz(Unknown)"

        attributes = [f"Noise {'On' if self.on else 'Off'} at {self.volume}% volume"]
        fan_attrs: list[str] = []

        if self.fan_on is not None:
            fan_attrs += [f"Fan {'On' if self.fan_on else 'Off'}"]

        if self.fan_speed is not None:
            fan_attrs += [f"at {self.fan_speed}% speed"]

        if self.fan_auto_enabled is True:
            fan_attrs += ["[Auto]"]

        if len(fan_attrs) > 0:
            attributes += [" ".join(fan_attrs)]

        if self.temperature is not None:
            attributes += [f"{self.temperature}°F"]

        if self.target_temperature is not None:
            attributes += [f"{self.target_temperature}°F target"]

        parts = ", ".join(attributes)

        return f"Snooz({parts})"


UnknownSnoozState = SnoozDeviceState()
