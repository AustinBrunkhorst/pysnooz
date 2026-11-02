# mypy: warn_unreachable=False
import pytest
from bluetooth_sensor_state_data import BluetoothServiceInfo

from pysnooz.advertisement import (
    get_device_display_name,
    get_device_model,
    parse_firmware_flags,
    parse_snooz_advertisement,
)
from pysnooz.api import READ_STATE_CHARACTERISTIC, WRITE_STATE_CHARACTERISTIC
from pysnooz.const import (
    FIRMWARE_PAIRING_FLAGS,
    FIRMWARE_VERSION_BY_FLAGS,
    ORIGINAL_FIRMWARE_VERSIONS,
    READ_COMMAND_CHARACTERISTIC,
    SNOOZ_ADVERTISEMENT_LENGTH,
    SUPPORTED_FIRMWARE_VERSIONS,
)
from pysnooz.model import SnoozDeviceModel, SnoozFirmwareVersion

EMPTY_PASSWORD = bytes([0x00] * (SNOOZ_ADVERTISEMENT_LENGTH - 1))


DEVICE_NO_MANUFACTURER_DATA = BluetoothServiceInfo(
    name="Snooz-ABCD",
    address="00:00:00:00:AB:CD",
    rssi=-63,
    manufacturer_data={},
    service_uuids=[],
    service_data={},
    source="local",
)

DEVICE_DATA_TOO_SHORT = BluetoothServiceInfo(
    name="Snooz-ABCD",
    address="00:00:00:00:AB:CD",
    rssi=-63,
    manufacturer_data={0xFFFF: bytes([0x00] * 2)},
    service_uuids=[],
    service_data={},
    source="local",
)

DEVICE_DATA_TOO_LONG = BluetoothServiceInfo(
    name="Snooz-ABCD",
    address="00:00:00:00:AB:CD",
    rssi=-63,
    manufacturer_data={0xFFFF: bytes([0x00] * 14)},
    service_uuids=[],
    service_data={},
    source="local",
)

DEVICE_UNKNOWN_FIRMWARE_VERSION = BluetoothServiceInfo(
    name="Snooz-ABCD",
    address="00:00:00:00:AB:CD",
    rssi=-63,
    manufacturer_data={0xFFFF: bytes([0xFF]) + EMPTY_PASSWORD},
    service_uuids=[],
    service_data={},
    source="local",
)

DEVICE_UNKNOWN_NAME = BluetoothServiceInfo(
    name="Wowee-ABCD",
    address="00:00:00:00:AB:CD",
    rssi=-63,
    manufacturer_data={0xFFFF: bytes([0x04]) + EMPTY_PASSWORD},
    service_uuids=[],
    service_data={},
    source="local",
)

# the name stored in the device name characteristic, which some bluetooth
# stacks report instead of the advertised name once a device has been connected
DEVICE_CHARACTERISTIC_NAME = BluetoothServiceInfo(
    name="Snooz",
    address="00:00:00:00:AB:CD",
    rssi=-63,
    manufacturer_data={0xFFFF: bytes([0x04]) + EMPTY_PASSWORD},
    service_uuids=[],
    service_data={},
    source="local",
)

DEVICE_PRO_NAME = BluetoothServiceInfo(
    name="Szpro-EF22",
    address="00:00:00:00:EF:22",
    rssi=-63,
    manufacturer_data={0xFFFF: bytes([0x14]) + EMPTY_PASSWORD},
    service_uuids=[],
    service_data={},
    source="local",
)

DEVICE_NEWER_FIRMWARE = BluetoothServiceInfo(
    name="Snooz-ABCD",
    address="00:00:00:00:AB:CD",
    rssi=-63,
    manufacturer_data={0xFFFF: bytes([0x18]) + EMPTY_PASSWORD},
    service_uuids=[],
    service_data={},
    source="local",
)


def test_display_name():
    assert get_device_display_name("Snooz", "00:00:00:00:00:00") == "Snooz 0000"
    assert get_device_display_name("snooz", "00:00:00:00:AB:CD") == "Snooz ABCD"
    assert get_device_display_name("sNooZ", "00:00:00:00:AB:CD") == "Snooz ABCD"
    assert get_device_display_name("Breez", "00:00:00:00:00:00") == "Breez 0000"
    assert get_device_display_name("breez", "00:00:00:00:AB:CD") == "Breez ABCD"
    assert get_device_display_name("bReEZ", "00:00:00:00:AB:CD") == "Breez ABCD"
    assert get_device_display_name("Snooz-DEBF", "00:00:00:00:AB:CD") == "Snooz ABCD"
    assert get_device_display_name("Snooz CCCC", "00:00:00:00:AB:CD") == "Snooz ABCD"
    assert get_device_display_name("Breez-DEBF", "00:00:00:00:AB:CD") == "Breez ABCD"
    assert get_device_display_name("Breez CCCC", "00:00:00:00:AB:CD") == "Breez ABCD"
    assert get_device_display_name("Szpro-EF22", "00:00:00:00:AB:CD") == "Szpro ABCD"
    assert get_device_display_name("Very custom", "00:00:00:00:AB:CD") == "Very custom"


def test_model_detection():
    for original in ORIGINAL_FIRMWARE_VERSIONS:
        assert get_device_model("Snooz-ABCD", original) == SnoozDeviceModel.ORIGINAL
        # the name isn't always in the Snooz-XXXX format
        assert get_device_model("Snooz", original) == SnoozDeviceModel.ORIGINAL
        assert get_device_model("snooz", original) == SnoozDeviceModel.ORIGINAL
        # pro and breez models are identified by name regardless of firmware
        assert get_device_model("Szpro-ABCD", original) == SnoozDeviceModel.PRO
        assert get_device_model("Breez-ABCD", original) == SnoozDeviceModel.BREEZ

    for newer in [
        v for v in SnoozFirmwareVersion if v not in ORIGINAL_FIRMWARE_VERSIONS
    ]:
        assert get_device_model("Snooz-ABCD", newer) == SnoozDeviceModel.PRO
        assert get_device_model("Snooz", newer) == SnoozDeviceModel.PRO
        assert get_device_model("Szpro-ABCD", newer) == SnoozDeviceModel.PRO
        assert get_device_model("Szpro", newer) == SnoozDeviceModel.PRO
        assert get_device_model("Breez-ABCD", newer) == SnoozDeviceModel.BREEZ
        assert get_device_model("Breez", newer) == SnoozDeviceModel.BREEZ

    for supported in SUPPORTED_FIRMWARE_VERSIONS:
        # doesn't match a supported name
        assert (
            get_device_model("NotSnooz-ABCD", supported) == SnoozDeviceModel.UNSUPPORTED
        )
        assert get_device_model("Wowee", supported) == SnoozDeviceModel.UNSUPPORTED


def test_unsupported():
    assert parse_snooz_advertisement(DEVICE_NO_MANUFACTURER_DATA) is None
    assert parse_snooz_advertisement(DEVICE_DATA_TOO_SHORT) is None
    assert parse_snooz_advertisement(DEVICE_DATA_TOO_LONG) is None
    assert parse_snooz_advertisement(DEVICE_UNKNOWN_FIRMWARE_VERSION) is None
    assert parse_snooz_advertisement(DEVICE_UNKNOWN_NAME) is None


def test_supported_name_variants():
    characteristic_name = parse_snooz_advertisement(DEVICE_CHARACTERISTIC_NAME)
    assert characteristic_name is not None
    assert characteristic_name.model == SnoozDeviceModel.ORIGINAL
    assert characteristic_name.firmware_version == SnoozFirmwareVersion.V2

    pro = parse_snooz_advertisement(DEVICE_PRO_NAME)
    assert pro is not None
    assert pro.model == SnoozDeviceModel.PRO
    assert pro.firmware_version == SnoozFirmwareVersion.V6

    newer = parse_snooz_advertisement(DEVICE_NEWER_FIRMWARE)
    assert newer is not None
    assert newer.model == SnoozDeviceModel.PRO
    assert newer.firmware_version == SnoozFirmwareVersion.V7


@pytest.fixture(params=SUPPORTED_FIRMWARE_VERSIONS)
def firmware_version(request: pytest.FixtureRequest) -> SnoozFirmwareVersion:
    return request.param


def test_parse_flags() -> None:
    assert parse_firmware_flags(0xFF) is None

    for flags in FIRMWARE_VERSION_BY_FLAGS:
        parsed = parse_firmware_flags(flags)
        assert parsed is not None
        assert parsed.firmware_version == FIRMWARE_VERSION_BY_FLAGS[flags]
        assert parsed.is_pairing is False

        parsed = parse_firmware_flags(flags | FIRMWARE_PAIRING_FLAGS)
        assert parsed is not None
        assert parsed.firmware_version == FIRMWARE_VERSION_BY_FLAGS[flags]
        assert parsed.is_pairing is True


def test_supported_firmware_version(firmware_version: SnoozFirmwareVersion) -> None:
    password = bytes([0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0xFA, 0xFB])

    flags = next(
        (
            x
            for x in FIRMWARE_VERSION_BY_FLAGS
            if FIRMWARE_VERSION_BY_FLAGS[x] == firmware_version
        ),
        None,
    )
    assert flags is not None

    not_pairing = parse_snooz_advertisement(_make_advertisement(flags, None))

    assert not_pairing is not None
    assert not_pairing.firmware_version == firmware_version
    assert not_pairing.password is None
    assert not not_pairing.is_pairing

    pairing = parse_snooz_advertisement(_make_advertisement(flags, password))

    assert pairing is not None
    assert pairing.firmware_version == firmware_version
    assert pairing.password == password.hex()
    assert pairing.is_pairing


def _make_advertisement(flags: int, password: bytes | None) -> BluetoothServiceInfo:
    if password is not None:
        flags |= FIRMWARE_PAIRING_FLAGS

    return BluetoothServiceInfo(
        name="Snooz-ABCD",
        address="00:00:00:00:AB:CD",
        rssi=-63,
        manufacturer_data={0xFFFF: bytes([flags]) + (password or EMPTY_PASSWORD)},
        service_uuids=[
            READ_STATE_CHARACTERISTIC,
            WRITE_STATE_CHARACTERISTIC,
            READ_COMMAND_CHARACTERISTIC,
        ],
        service_data={},
        source="local",
    )
