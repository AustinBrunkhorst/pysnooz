# mypy: warn_unreachable=False
from bluetooth_sensor_state_data import BluetoothServiceInfo

from pysnooz.advertisement import (
    TOKEN_EMPTY,
    TOKEN_SEQUENCE,
    SnoozAdvertisementData,
    get_snooz_display_name,
)
from pysnooz.api import READ_STATE_UUID, WRITE_STATE_UUID

DEVICE_TOKEN_EMPTY = BluetoothServiceInfo(
    name="Snooz-ABCD",
    address="00:00:00:00:AB:CD",
    rssi=-63,
    manufacturer_data={65552: bytes([4]) + TOKEN_EMPTY},
    service_uuids=[READ_STATE_UUID, WRITE_STATE_UUID],
    service_data={},
    source="local",
)

DEVICE_TOKEN_SEQUENCE = BluetoothServiceInfo(
    name="Snooz-ABCD",
    address="00:00:00:00:AB:CD",
    rssi=-63,
    manufacturer_data={65552: bytes([4]) + TOKEN_SEQUENCE},
    service_uuids=[READ_STATE_UUID, WRITE_STATE_UUID],
    service_data={},
    source="local",
)

DEVICE_TOKEN_DEADBEEF = BluetoothServiceInfo(
    name="Snooz-ABCD",
    address="00:00:00:00:AB:CD",
    rssi=-63,
    manufacturer_data={65552: bytes([4]) + b"\xDE\xAD\xBE\xEF"},
    service_uuids=[READ_STATE_UUID, WRITE_STATE_UUID],
    service_data={},
    source="local",
)


def test_display_name():
    assert get_snooz_display_name("Snooz", "00:00:00:00:00:00") == "Snooz 0000"
    assert get_snooz_display_name("snooz", "00:00:00:00:AB:CD") == "Snooz ABCD"
    assert get_snooz_display_name("sNooZ", "00:00:00:00:AB:CD") == "Snooz ABCD"
    assert get_snooz_display_name("Snooz-DEBF", "00:00:00:00:AB:CD") == "Snooz DEBF"
    assert get_snooz_display_name("Snooz CCCC", "00:00:00:00:AB:CD") == "Snooz CCCC"
    assert get_snooz_display_name("Very custom", "00:00:00:00:AB:CD") == "Very custom"

    parser = SnoozAdvertisementData()
    assert parser.supported(DEVICE_TOKEN_EMPTY) is True
    assert parser.display_name == "Snooz ABCD"


def test_pairing_mode():
    parser = SnoozAdvertisementData()

    assert parser.supported(DEVICE_TOKEN_EMPTY) is True
    assert parser.is_pairing is False

    assert parser.supported(DEVICE_TOKEN_SEQUENCE) is True
    assert parser.is_pairing is False

    assert parser.supported(DEVICE_TOKEN_DEADBEEF) is True
    assert parser.is_pairing is True
    assert parser.pairing_token == "deadbeef"
