from attr import dataclass

from pysnooz.const import SnoozDeviceState, UnknownSnoozState


@dataclass
class SnoozStateStore:
    current: SnoozDeviceState = UnknownSnoozState

    def patch(self, state: SnoozDeviceState) -> bool:
        updated_props = [
            p
            for p in dir(state)
            if not p.startswith("__") and getattr(state, p) is not None
        ]
        did_change = False
        for prop in updated_props:
            p_current = getattr(self.current, prop)
            p_state = getattr(state, prop)

            if p_current != p_state:
                did_change = True
                setattr(self.current, prop, p_state)

        return did_change
