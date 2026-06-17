from __future__ import annotations

from library.core.constants import RIVALS


class RivalGreenName:
    """A bad-guy rival on the street ladder - a rival 'green name' tuner's car."""

    def __init__(self, name: str, whp: float, weight: float, grip: float, purse: int, color):
        self.name = name
        self.whp = whp
        self.weight = weight
        self.grip = grip
        self.purse = purse
        self.color = color

    @classmethod
    def from_spec(cls, spec: dict) -> "RivalGreenName":
        return cls(spec["name"], spec["whp"], spec["weight"], spec["grip"], spec["purse"], spec["color"])

    @classmethod
    def ladder(cls) -> list["RivalGreenName"]:
        return [cls.from_spec(spec) for spec in RIVALS]

    def to_dict(self) -> dict:
        return {"name": self.name, "whp": self.whp, "weight": self.weight, "grip": self.grip, "purse": self.purse}
