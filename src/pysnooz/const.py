from pysnooz.model import SnoozFirmwareVersion

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


SNOOZ_ADVERTISEMENT_LENGTH = 9

FIRMWARE_PAIRING_FLAGS = 0x01
FIRMWARE_VERSION_BY_FLAGS = {
    0x04: SnoozFirmwareVersion.V2,
    0x08: SnoozFirmwareVersion.V3,
    0x0C: SnoozFirmwareVersion.V4,
    0x10: SnoozFirmwareVersion.V5,
    0x14: SnoozFirmwareVersion.V6,
    0x18: SnoozFirmwareVersion.V7,
    0x1C: SnoozFirmwareVersion.V8,
    0x20: SnoozFirmwareVersion.V9,
    0x24: SnoozFirmwareVersion.V10,
    0x28: SnoozFirmwareVersion.V11,
    0x2C: SnoozFirmwareVersion.V12,
    0x30: SnoozFirmwareVersion.V13,
    0x34: SnoozFirmwareVersion.V14,
    0x38: SnoozFirmwareVersion.V15,
}
SUPPORTED_FIRMWARE_VERSIONS = [
    SnoozFirmwareVersion.V2,
    SnoozFirmwareVersion.V3,
    SnoozFirmwareVersion.V4,
    SnoozFirmwareVersion.V5,
    SnoozFirmwareVersion.V6,
]

MODEL_NAME_SNOOZ = "Snooz"
MODEL_NAME_BREEZ = "Breez"
SUPPORTED_MODEL_NAMES = [MODEL_NAME_SNOOZ, MODEL_NAME_BREEZ]
