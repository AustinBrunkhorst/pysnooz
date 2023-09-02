from __future__ import annotations

import logging

from bluetooth_sensor_state_data import BluetoothData
from home_assistant_bluetooth import BluetoothServiceInfo

ADVERTISEMENT_TOKEN_LENGTH = 8
TOKEN_EMPTY = bytes([0] * ADVERTISEMENT_TOKEN_LENGTH)
TOKEN_SEQUENCE = bytes(range(1, ADVERTISEMENT_TOKEN_LENGTH + 1))
KNOWN_DEVICE_NAMES = ["Snooz", "Breez"]

_LOGGER = logging.getLogger(__name__)


class SnoozAdvertisementData(BluetoothData):
    """Represents data from a SNOOZ advertisement."""

    def __init__(self) -> None:
        super().__init__()
        # string of hex digits stored in the device advertisement only in pairing mode
        self.pairing_token: str | None = None

        # formatted name like "Snooz AABB"
        # where AABB is the last 4 digits of the MAC address
        self.display_name: str | None = None

    @property
    def is_pairing(self) -> bool:
        """Return True if the device is in pairing mode"""

        return self.pairing_token is not None

    def _start_update(self, data: BluetoothServiceInfo) -> None:
        """Update from BLE advertisement data"""

        advertisement = data.manufacturer_data.get(data.manufacturer_id)

        if advertisement is None:
            return

        raw_token = advertisement[1:]

        if len(raw_token) != ADVERTISEMENT_TOKEN_LENGTH:
            _LOGGER.debug(
                f"Skipped {data.name} because token length was unexpected"
                f" ({len(raw_token)}): {raw_token.hex('-')}"
            )
            return

        # pairing mode is enabled if the advertisement token is
        # all zeros or a sequence from 1-8
        if raw_token not in (TOKEN_EMPTY, TOKEN_SEQUENCE):
            self.pairing_token = raw_token.hex()

        name = get_device_display_name(data.name, data.address)
        self.display_name = name

        self.set_title(name)
        self.set_device_name(name)
        self.set_device_manufacturer("SNOOZ, LLC")
        self.set_device_type("SNOOZ White Noise Machine")
        self.set_device_hw_version(advertisement[0])


def get_device_display_name(local_name: str, address: str) -> str:
    # if the advertised name doesn't have any digits, then use
    # the last 4 from the mac address
    supported = next(
        (x for x in KNOWN_DEVICE_NAMES if x.lower() == local_name.lower()), None
    )
    if supported is not None:
        return f"{supported} {address.replace(':', '')[-4:]}"

    return local_name.replace("-", " ")
