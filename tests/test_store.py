from pysnooz import SnoozDeviceState
from pysnooz.model import SnoozAdvertisementData, SnoozDeviceModel, SnoozFirmwareVersion
from pysnooz.store import SnoozStateStore

DOESNT_SUPPORT_FAN = SnoozAdvertisementData(
    SnoozDeviceModel.ORIGINAL, SnoozFirmwareVersion.V2, "12345678"
)

SUPPORTS_FAN = SnoozAdvertisementData(
    SnoozDeviceModel.BREEZ, SnoozFirmwareVersion.V6, "12345678"
)


def test_patch():
    store = SnoozStateStore(SUPPORTS_FAN)
    assert store.current == SnoozDeviceState()

    initial_state = SnoozDeviceState(on=True, volume=10)
    assert store.patch(initial_state) is True

    assert store.current == initial_state

    new_state = SnoozDeviceState(on=False, fan_speed=50)
    assert store.patch(new_state) is True
    assert store.current.volume is initial_state.volume
    assert store.current.on is new_state.on
    assert store.current.fan_speed is new_state.fan_speed

    assert store.patch(new_state) is False


def test_patch_unsupported_props():
    store = SnoozStateStore(DOESNT_SUPPORT_FAN)

    assert store.current == SnoozDeviceState()

    initial_state = SnoozDeviceState(on=True, volume=10)
    assert store.patch(initial_state) is True

    assert store.current == initial_state

    new_state = SnoozDeviceState(on=False, fan_speed=50)
    assert store.patch(new_state) is True
    assert store.current.volume is initial_state.volume
    assert store.current.on is new_state.on
    assert store.current.fan_speed is None

    assert (
        store.patch(
            SnoozDeviceState(
                fan_on=True,
                fan_speed=33,
                fan_auto_enabled=True,
                temperature=69,
                target_temperature=68,
            )
        )
        is False
    )
    assert store.current.fan_on is None
    assert store.current.fan_speed is None
    assert store.current.fan_auto_enabled is None
    assert store.current.temperature is None
    assert store.current.target_temperature is None
