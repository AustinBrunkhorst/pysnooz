from pysnooz.model import SnoozAdvertisementData, SnoozDeviceState

SOUND_PROPS = ["on", "volume"]
FAN_PROPS = [
    "fan_on",
    "fan_speed",
    "fan_auto_enabled",
    "temperature",
    "target_temperature",
]


class SnoozStateStore:
    def __init__(self, adv_data: SnoozAdvertisementData) -> None:
        self.current = SnoozDeviceState()
        self._adv_data = adv_data

    def patch(self, state: SnoozDeviceState) -> bool:
        updated_props = [
            p
            for p in dir(state)
            if not p.startswith("__")
            and getattr(state, p) is not None
            and self._supports_prop(p)
        ]
        did_change = False
        for prop in updated_props:
            p_current = getattr(self.current, prop)
            p_state = getattr(state, prop)

            if p_current != p_state:
                did_change = True
                setattr(self.current, prop, p_state)

        return did_change

    def _supports_prop(self, prop: str) -> bool:
        if not self._adv_data.supports_fan and prop in FAN_PROPS:
            return False

        return True
