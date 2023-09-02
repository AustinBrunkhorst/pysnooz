# mypy: warn_unreachable=False
from bluetooth_sensor_state_data import BluetoothServiceInfo

from pysnooz.advertisement import (
    TOKEN_EMPTY,
    TOKEN_SEQUENCE,
    SnoozAdvertisementData,
    get_device_display_name,
)
from pysnooz.api import READ_STATE_CHARACTERISTIC, WRITE_STATE_CHARACTERISTIC

DEVICE_TOKEN_EMPTY = BluetoothServiceInfo(
    name="Snooz-ABCD",
    address="00:00:00:00:AB:CD",
    rssi=-63,
    manufacturer_data={65552: bytes([4]) + TOKEN_EMPTY},
    service_uuids=[READ_STATE_CHARACTERISTIC, WRITE_STATE_CHARACTERISTIC],
    service_data={},
    source="local",
)

DEVICE_TOKEN_SEQUENCE = BluetoothServiceInfo(
    name="Snooz-ABCD",
    address="00:00:00:00:AB:CD",
    rssi=-63,
    manufacturer_data={65552: bytes([4]) + TOKEN_SEQUENCE},
    service_uuids=[READ_STATE_CHARACTERISTIC, WRITE_STATE_CHARACTERISTIC],
    service_data={},
    source="local",
)

DEVICE_TOKEN_ABCD = BluetoothServiceInfo(
    name="Snooz-ABCD",
    address="00:00:00:00:AB:CD",
    rssi=-63,
    manufacturer_data={65552: bytes([4]) + bytes.fromhex("ABCD")},
    service_uuids=[READ_STATE_CHARACTERISTIC, WRITE_STATE_CHARACTERISTIC],
    service_data={},
    source="local",
)

DEADBEEFCAFED00D = "DEADBEEFCAFED00D"
DEVICE_TOKEN_DEADBEEFCAFED00D = BluetoothServiceInfo(
    name="Snooz-ABCD",
    address="00:00:00:00:AB:CD",
    rssi=-63,
    manufacturer_data={65552: bytes([4]) + bytes.fromhex(DEADBEEFCAFED00D)},
    service_uuids=[READ_STATE_CHARACTERISTIC, WRITE_STATE_CHARACTERISTIC],
    service_data={},
    source="local",
)

DEVICE_NO_MANUFACTURER_DATA = BluetoothServiceInfo(
    name="Snooz-ABCD",
    address="00:00:00:00:AB:CD",
    rssi=-63,
    manufacturer_data={},
    service_uuids=[READ_STATE_CHARACTERISTIC, WRITE_STATE_CHARACTERISTIC],
    service_data={},
    source="local",
)

DEVICE_UNRECOGNIZED_NAME = BluetoothServiceInfo(
    name="LG Speaker",
    address="00:00:00:00:CC:CC",
    rssi=-63,
    manufacturer_data={},
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
    assert get_device_display_name("Snooz-DEBF", "00:00:00:00:AB:CD") == "Snooz DEBF"
    assert get_device_display_name("Snooz CCCC", "00:00:00:00:AB:CD") == "Snooz CCCC"
    assert get_device_display_name("Breez-DEBF", "00:00:00:00:AB:CD") == "Breez DEBF"
    assert get_device_display_name("Breez CCCC", "00:00:00:00:AB:CD") == "Breez CCCC"
    assert get_device_display_name("Very custom", "00:00:00:00:AB:CD") == "Very custom"

    parser = SnoozAdvertisementData()
    assert parser.supported(DEVICE_TOKEN_EMPTY) is True
    assert parser.display_name == "Snooz ABCD"


def test_unsupported():
    parser = SnoozAdvertisementData()
    assert parser.supported(DEVICE_NO_MANUFACTURER_DATA) is False
    assert parser.supported(DEVICE_UNRECOGNIZED_NAME) is False


def test_pairing_mode():
    parser = SnoozAdvertisementData()

    assert parser.supported(DEVICE_TOKEN_EMPTY) is True
    assert parser.is_pairing is False

    assert parser.supported(DEVICE_TOKEN_SEQUENCE) is True
    assert parser.is_pairing is False

    assert parser.supported(DEVICE_TOKEN_ABCD) is True
    assert parser.is_pairing is False

    assert parser.supported(DEVICE_TOKEN_DEADBEEFCAFED00D) is True
    assert parser.is_pairing is True
    assert parser.pairing_token == DEADBEEFCAFED00D.lower()
