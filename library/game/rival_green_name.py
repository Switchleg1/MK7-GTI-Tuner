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

    def to_dict(self) -> dict:
        return {"name": self.name, "whp": self.whp, "weight": self.weight, "grip": self.grip, "purse": self.purse, "model": self.model}

    def from_dict(self, data: dict):
        # Restore the stats from a save (the ladder itself is rebuilt from RIVALS, so
        # the colour stays); guards against a future roster change shifting indices.
        for key in ("name", "whp", "weight", "grip", "purse", "model"):
            if key in data:
                setattr(self, key, data[key])
