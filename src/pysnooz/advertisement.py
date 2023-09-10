from __future__ import annotations

import logging
from dataclasses import dataclass

from home_assistant_bluetooth import BluetoothServiceInfo

from pysnooz.const import (
    FIRMWARE_PAIRING_FLAGS,
    FIRMWARE_VERSION_BY_FLAGS,
    MODEL_NAME_BREEZ,
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

    # The advertised name is in the format "Snooz-XXXX" or "Breez-XXXX"
    # we require this format since the name stored in device characteristics
    # is always "Snooz" and matching it would not correctly identify Breez models
    if known is None or len(advertised_name) != len(known) + 5:
        return SnoozDeviceModel.UNSUPPORTED

    if firmware in [
        SnoozFirmwareVersion.V2,
        SnoozFirmwareVersion.V3,
        SnoozFirmwareVersion.V4,
        SnoozFirmwareVersion.V5,
    ]:
        return SnoozDeviceModel.ORIGINAL

    if firmware == SnoozFirmwareVersion.V6:
        return (
            SnoozDeviceModel.BREEZ
            if known == MODEL_NAME_BREEZ
            else SnoozDeviceModel.PRO
        )

    return SnoozDeviceModel.UNSUPPORTED


def get_device_display_name(advertised_name: str, address: str) -> str:
    known = match_known_device_name(advertised_name)
    if known is not None:
        return f"{known} {address.replace(':', '')[-4:]}"

    return advertised_name.replace("-", " ")
