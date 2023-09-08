from __future__ import annotations
import logging

from home_assistant_bluetooth import BluetoothServiceInfo
from pysnooz.const import (
    FIRMWARE_VERSION_BY_FLAGS,
    SUPPORTED_MODEL_NAMES,
    MODEL_NAME_BREEZ,
    SNOOZ_ADVERTISEMENT_LENGTH,
    SnoozAdvertisementFlags,
)

from pysnooz.model import SnoozAdvertisementData, SnoozDeviceModel, SnoozFirmwareVersion


_LOGGER = logging.getLogger(__name__)


def parse_snooz_advertisement(
    data: BluetoothServiceInfo,
) -> SnoozAdvertisementData | None:
    advertisement = data.manufacturer_data.get(data.manufacturer_id)

    if advertisement is None:
        return None

    if len(advertisement) != SNOOZ_ADVERTISEMENT_LENGTH:
        return None

    flags = advertisement[0]
    is_pairing = SnoozAdvertisementFlags.PAIRING_ENABLED in SnoozAdvertisementFlags(
        flags
    )
    password = advertisement[1:].hex() if is_pairing else None

    flags_without_pairing = flags & ~SnoozAdvertisementFlags.PAIRING_ENABLED

    if flags_without_pairing not in FIRMWARE_VERSION_BY_FLAGS:
        _LOGGER.debug(
            f"Unknown device flags {flags_without_pairing:02x}"
            f" in advertisement {advertisement}"
        )
        return None

    firmware_version = FIRMWARE_VERSION_BY_FLAGS[flags_without_pairing]

    model = get_device_model(data.name, firmware_version)

    if model == SnoozDeviceModel.UNSUPPORTED:
        _LOGGER.debug(f"{data.name} is unsupported with firmware {firmware_version}")
        return None

    return SnoozAdvertisementData(model, firmware_version, password)


def match_known_model_name(advertised_name: str) -> str | None:
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
    known = match_known_model_name(advertised_name)

    if known is None:
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
    known = match_known_model_name(advertised_name)
    if known is not None:
        return f"{known} {address.replace(':', '')[-4:]}"

    return advertised_name.replace("-", " ")
