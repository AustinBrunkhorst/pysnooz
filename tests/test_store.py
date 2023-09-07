from pysnooz import SnoozDeviceState
from pysnooz.store import SnoozStateStore


def test_patch():
    store = SnoozStateStore()
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
