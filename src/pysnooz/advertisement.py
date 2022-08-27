from bluetooth_sensor_state_data import BluetoothData
from home_assistant_bluetooth import BluetoothServiceInfo

ADVERTISEMENT_TOKEN_LENGTH = 8
TOKEN_EMPTY = bytes([0] * ADVERTISEMENT_TOKEN_LENGTH)
TOKEN_SEQUENCE = bytes(range(1, ADVERTISEMENT_TOKEN_LENGTH + 1))


class SnoozAdvertisementData(BluetoothData):
    """string of hex digits stored in the device advertisement only in pairing mode"""

    pairing_token: str

    @property
    def is_pairing(self) -> bool:
        """Return True if the device is in pairing mode"""

        return self.pairing_token is not None

    def _start_update(self, data: BluetoothServiceInfo) -> None:
        """Update from BLE advertisement data"""

        # device local names are prefixed with Snooz
        if not data.name.startswith("Snooz"):
            return

        advertisement = data.manufacturer_data.get(data.manufacturer_id)

        if advertisement is None:
            return

        raw_token = advertisement[1:]

        # pairing mode is enabled if the advertisement token is
        # all zeros or a sequence from 1-8
        if raw_token not in (TOKEN_EMPTY, TOKEN_SEQUENCE):
            self.pairing_token = raw_token.hex()

        name = data.name.replace("-", " ")
        self.set_title(name)
        self.set_device_name(name)
        self.set_device_manufacturer("SNOOZ, LLC")
        self.set_device_type("SNOOZ White Noise Machine")
        self.set_device_hw_version(advertisement[0])
