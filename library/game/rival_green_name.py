from __future__ import annotations

from library.core.constants import RIVALS


class RivalGreenName:
    """A bad-guy rival on the street ladder - a rival 'green name' tuner's car."""

    def __init__(self, name: str, whp: float, weight: float, grip: float, purse: int, color, model: str):
        self.name = name
        self.whp = whp
        self.weight = weight
        self.grip = grip
        self.purse = purse
        self.color = color
        self.model = model

    @classmethod
    def from_spec(cls, spec: dict) -> "RivalGreenName":
        return cls(spec["name"], spec["whp"], spec["weight"], spec["grip"], spec["purse"], spec["color"], spec["model"])

    @classmethod
    def ladder(cls) -> list["RivalGreenName"]:
        return [cls.from_spec(spec) for spec in RIVALS]

    # No to_dict/from_dict: the ladder is static reference data, always rebuilt from
    # RIVALS. Saving it froze stale specs into old saves (see Game.to_dict); progress
    # is persisted on TunerBro (unlocked_rival / selected_rival).
