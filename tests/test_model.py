from pysnooz.model import SnoozDeviceState, UnknownSnoozState


def test_state_operators() -> None:
    assert SnoozDeviceState(on=True, volume=None) == SnoozDeviceState(
        on=True, volume=None
    )
    assert SnoozDeviceState(on=False, volume=None) == SnoozDeviceState(
        on=False, volume=None
    )
    assert SnoozDeviceState(on=True, volume=10) == SnoozDeviceState(on=True, volume=10)
    assert SnoozDeviceState(on=False, volume=13) == SnoozDeviceState(
        on=False, volume=13
    )
    assert SnoozDeviceState(on=False, volume=13) != SnoozDeviceState(
        on=False, volume=15
    )

    assert SnoozDeviceState(fan_on=True, fan_speed=None) == SnoozDeviceState(
        fan_on=True, fan_speed=None
    )
    assert SnoozDeviceState(fan_on=False, fan_speed=None) == SnoozDeviceState(
        fan_on=False, fan_speed=None
    )
    assert SnoozDeviceState(fan_on=True, fan_speed=10) == SnoozDeviceState(
        fan_on=True, fan_speed=10
    )
    assert SnoozDeviceState(fan_on=False, fan_speed=13) == SnoozDeviceState(
        fan_on=False, fan_speed=13
    )
    assert SnoozDeviceState(fan_on=False, fan_speed=13) != SnoozDeviceState(
        fan_on=False, fan_speed=15
    )
    assert SnoozDeviceState(light_on=True, light_brightness=15) == SnoozDeviceState(
        light_on=True, light_brightness=15
    )
    assert SnoozDeviceState(light_on=True, light_brightness=15) != SnoozDeviceState(
        light_on=True, light_brightness=None
    )

    assert SnoozDeviceState(
        on=True,
        volume=50,
        fan_on=True,
        fan_speed=60,
        fan_auto_enabled=True,
        temperature=64.5,
        target_temperature=32,
    ) == SnoozDeviceState(
        on=True,
        volume=50,
        fan_on=True,
        fan_speed=60,
        fan_auto_enabled=True,
        temperature=64.5,
        target_temperature=32,
    )


def test_repr() -> None:
    assert UnknownSnoozState.__repr__() == "Snooz(Unknown)"
    assert (
        SnoozDeviceState(on=True, volume=10).__repr__()
        == "Snooz(Noise On at 10% volume)"
    )
    assert (
        SnoozDeviceState(on=False, volume=15).__repr__()
        == "Snooz(Noise Off at 15% volume)"
    )
    assert (
        SnoozDeviceState(
            on=False, volume=15, light_on=True, light_brightness=55
        ).__repr__()
        == "Snooz(Noise Off at 15% volume, Light at 55% brightness)"
    )
    assert (
        SnoozDeviceState(on=False, volume=15, night_mode_enabled=True).__repr__()
        == "Snooz(Noise Off at 15% volume, [NightMode])"
    )
    assert (
        SnoozDeviceState(on=False, volume=15, fan_on=True, fan_speed=32).__repr__()
        == "Snooz(Noise Off at 15% volume, Fan On at 32% speed)"
    )
    assert (
        SnoozDeviceState(
            on=False, volume=15, fan_on=True, fan_speed=32, temperature=70
        ).__repr__()
        == "Snooz(Noise Off at 15% volume, Fan On at 32% speed, 70°F)"
    )
    assert (
        SnoozDeviceState(
            on=False,
            volume=15,
            fan_on=True,
            fan_speed=32,
            temperature=63.3,
            fan_auto_enabled=True,
            target_temperature=72,
        ).__repr__()
        == "Snooz(Noise Off at 15% volume, Fan On at 32% speed [Auto]"
        ", 63.3°F, 72°F target)"
    )
