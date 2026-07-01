from __future__ import annotations

from library.core.constants import EQUIP_FAMILIES, RIVALS, MOD_KEYS
from library.game.car import Car


class RivalGreenName:
    """A bad-guy rival on the street ladder. Encounter metadata (name, purse, colour
    tint, win/loss clips) plus the ``Car`` it drives -- the car's physics (curve,
    gearing, mass, grip) come from ``CAR_TABLE`` via ``car_id``. Bolt-on mods come from the
    ``mods`` list; ``variants`` optionally pins a specific equippable unit per family (e.g.
    ``{"turbo": "arashi_3076", "ic": "smic"}``) so a rival runs the right curve + boost caps
    instead of the family baseline."""

    def __init__(self, name: str, car_id: str, purse: int, color, mods: list, tune,
                 video_loss=None, video_win=None, variants: dict | None = None):
        self.name           = name
        self.car            = Car(car_id, {k: k in mods for k in MOD_KEYS}, tune)
        # Pin any specified turbo/IC variant (else the mods-list anchor -> family baseline).
        for kind, fam in EQUIP_FAMILIES.items():
            variant = (variants or {}).get(kind)
            if variant:
                setattr(self.car, fam["equipped"], variant)
                setattr(self.car, fam["owned"], [variant])
                self.car.mods[fam["anchor"]] = True
        self.car.flashed    = True  # a rival's ECU is already flashed with its map, so its tune applies
        self.model          = self.car.model  # convenience (race_task loads the rival's glb by this)
        self.purse          = purse
        self.color          = color
        self.video_loss     = list(video_loss or [])
        self.video_win      = list(video_win or [])

    @classmethod
    def from_spec(cls, spec: dict) -> "RivalGreenName":
        variants = {kind: spec[kind] for kind in EQUIP_FAMILIES if spec.get(kind)}
        return cls(
            spec["name"], spec["car_id"], spec["purse"], spec["color"],
            spec["mods"], spec["tune"], spec.get("video_loss"), spec.get("video_win"),
            variants=variants,
        )

    @classmethod
    def ladder(cls) -> list["RivalGreenName"]:
        return [cls.from_spec(spec) for spec in RIVALS]

    # No to_dict/from_dict: the ladder is static reference data, always rebuilt from
    # RIVALS. Saving it froze stale specs into old saves (see Game.to_dict); progress
    # is persisted on TunerBro (unlocked_rival / selected_rival).
