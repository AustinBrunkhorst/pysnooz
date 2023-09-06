from .advertisement import SnoozAdvertisementData
from .commands import (
    SnoozCommandResultStatus,
    set_auto_temp_enabled,
    get_device_info,
    set_fan_speed,
    set_temp_target,
    set_volume,
    turn_fan_off,
    turn_fan_on,
    turn_off,
    turn_on,
)
from .const import SnoozDeviceModel, SnoozDeviceInfo, SnoozDeviceState, UnknownSnoozState
from .device import SnoozCommandData, SnoozDevice

__version__ = "0.8.6"

__all__ = [
    "SnoozDeviceModel",
    "SnoozDevice",
    "SnoozDeviceState",
    "UnknownSnoozState",
    "SnoozDeviceInfo",
    "SnoozCommandData",
    "SnoozCommandResultStatus",
    "SnoozAdvertisementData",
    "get_device_info",
    "turn_on",
    "turn_off",
    "set_volume",
    "turn_fan_on",
    "turn_fan_off",
    "set_fan_speed",
    "set_auto_temp_enabled",
    "set_temp_target",
]
