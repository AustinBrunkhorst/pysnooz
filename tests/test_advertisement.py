# mypy: warn_unreachable=False
from bluetooth_sensor_state_data import BluetoothServiceInfo
import pytest

from pysnooz.advertisement import (
    get_device_display_name,
    get_device_model,
    parse_snooz_advertisement,
)
from pysnooz.api import READ_STATE_CHARACTERISTIC, WRITE_STATE_CHARACTERISTIC
from pysnooz.const import (
    FIRMWARE_VERSION_BY_FLAGS,
    READ_COMMAND_CHARACTERISTIC,
    SNOOZ_ADVERTISEMENT_LENGTH,
    SUPPORTED_FIRMWARE_VERSIONS,
    SnoozAdvertisementFlags,
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
    assert get_device_display_name("Very custom", "00:00:00:00:AB:CD") == "Very custom"


def test_model_detection():
    assert (
        get_device_model("Snooz-ABCD", SnoozFirmwareVersion.V2)
        == SnoozDeviceModel.ORIGINAL
    )
    assert (
        get_device_model("Snooz-ABCD", SnoozFirmwareVersion.V3)
        == SnoozDeviceModel.ORIGINAL
    )
    assert (
        get_device_model("Snooz-ABCD", SnoozFirmwareVersion.V4)
        == SnoozDeviceModel.ORIGINAL
    )
    assert (
        get_device_model("Snooz-ABCD", SnoozFirmwareVersion.V5)
        == SnoozDeviceModel.ORIGINAL
    )
    assert (
        get_device_model("Snooz-ABCD", SnoozFirmwareVersion.V6) == SnoozDeviceModel.PRO
    )
    assert (
        get_device_model("Breez-ABCD", SnoozFirmwareVersion.V6)
        == SnoozDeviceModel.BREEZ
    )

    for supported in SUPPORTED_FIRMWARE_VERSIONS:
        assert (
            # doesn't match supported name
            get_device_model("NotSnooz-ABCD", supported)
            == SnoozDeviceModel.UNSUPPORTED
        )

    for unsupported in [
        v for v in SnoozFirmwareVersion if v not in SUPPORTED_FIRMWARE_VERSIONS
    ]:
        assert (
            get_device_model("Snooz-ABCD", unsupported) == SnoozDeviceModel.UNSUPPORTED
        )


def test_unsupported():
    assert parse_snooz_advertisement(DEVICE_NO_MANUFACTURER_DATA) is None
    assert parse_snooz_advertisement(DEVICE_DATA_TOO_SHORT) is None
    assert parse_snooz_advertisement(DEVICE_DATA_TOO_SHORT) is None
    assert parse_snooz_advertisement(DEVICE_UNKNOWN_FIRMWARE_VERSION) is None
    assert parse_snooz_advertisement(DEVICE_UNKNOWN_NAME) is None


@pytest.fixture(params=SUPPORTED_FIRMWARE_VERSIONS)
def firmware_version(request: SnoozFirmwareVersion):
    yield request.param


def test_supported_firmware_version(firmware_version: SnoozFirmwareVersion):
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
        flags |= SnoozAdvertisementFlags.PAIRING_ENABLED

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
