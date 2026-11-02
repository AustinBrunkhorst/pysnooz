from __future__ import annotations

import logging
from dataclasses import dataclass

from home_assistant_bluetooth import BluetoothServiceInfo

from pysnooz.const import (
    FIRMWARE_PAIRING_FLAGS,
    FIRMWARE_VERSION_BY_FLAGS,
    MODEL_NAME_BREEZ,
    MODEL_NAME_SNOOZ_PRO,
    ORIGINAL_FIRMWARE_VERSIONS,
    SNOOZ_ADVERTISEMENT_LENGTH,
    SUPPORTED_MODEL_NAMES,
)
from pysnooz.model import SnoozAdvertisementData, SnoozDeviceModel, SnoozFirmwareVersion

_LOGGER = logging.getLogger(__name__)


@dataclass
class ParsedAdvertisementFlags:
    firmware_version: SnoozFirmwareVersion
    is_pairing: bool


def parse_firmware_flags(flags: int) -> ParsedAdvertisementFlags | None:
    is_pairing = (FIRMWARE_PAIRING_FLAGS & flags) == FIRMWARE_PAIRING_FLAGS
    flags_without_pairing = flags & ~FIRMWARE_PAIRING_FLAGS

    if flags_without_pairing not in FIRMWARE_VERSION_BY_FLAGS:
        _LOGGER.debug(f"Unknown device flags {flags_without_pairing:02X}")
        return None

    return ParsedAdvertisementFlags(
        FIRMWARE_VERSION_BY_FLAGS[flags_without_pairing], is_pairing
    )


def parse_snooz_advertisement(
    data: BluetoothServiceInfo,
) -> SnoozAdvertisementData | None:
    advertisement = data.manufacturer_data.get(data.manufacturer_id)

    if advertisement is None:
        return None

    if len(advertisement) != SNOOZ_ADVERTISEMENT_LENGTH:
        return None

    if not (flags := parse_firmware_flags(advertisement[0])):
        return None

    model = get_device_model(data.name, flags.firmware_version)

    if model == SnoozDeviceModel.UNSUPPORTED:
        _LOGGER.debug(
            f"{data.name} is unsupported with firmware {flags.firmware_version}"
        )
        return None

    return SnoozAdvertisementData(
        model,
        flags.firmware_version,
        password=advertisement[1:].hex() if flags.is_pairing else None,
    )


def match_known_device_name(advertised_name: str) -> str | None:
    return next(
        (
            value
            for value in SUPPORTED_MODEL_NAMES
            if advertised_name.lower().startswith(value.lower())
        ),
        None,
    )


def get_device_model(
    advertised_name: str, firmware: SnoozFirmwareVersion
) -> SnoozDeviceModel:
    known = match_known_device_name(advertised_name)

    # Devices normally advertise a name like "Snooz-XXXX" or "Breez-XXXX", but
    # the name seen by a client isn't guaranteed to be in that format: the name
    # stored in the device name characteristic is "Snooz" for every model (and
    # some stacks report that instead of the advertised name after connecting),
    # and a Pro model has been observed with the name "Szpro EF22". Anything
    # that starts with a known name is accepted so a device can always be set up.
    if known is None:
        return SnoozDeviceModel.UNSUPPORTED

    if known == MODEL_NAME_BREEZ:
        return SnoozDeviceModel.BREEZ

    if known == MODEL_NAME_SNOOZ_PRO:
        return SnoozDeviceModel.PRO

    # "Snooz" is advertised by both the original and Pro models, so the
    # firmware version is the only way to tell them apart
    if firmware in ORIGINAL_FIRMWARE_VERSIONS:
        return SnoozDeviceModel.ORIGINAL

    return SnoozDeviceModel.PRO


def get_device_display_name(advertised_name: str, address: str) -> str:
    known = match_known_device_name(advertised_name)
    if known is not None:
        return f"{known} {address.replace(':', '')[-4:]}"

    return advertised_name.replace("-", " ")
