from __future__ import annotations

from library.core.utils import clamp
from library.game.tuning import rep_title


class TunerBro:
    """The user ("the bro"): wallet, reputation, heat, and street-ladder progress.

    Personal stats only — the car build lives in Car. Built to serialize for save
    games (see to_dict/from_dict). Room to grow: emotional_damage, route, skills.
    """

    def __init__(self, name: str = "Bro"):
        self.name = name
        self.cash = 750
        self.cred = 0.0
        self.karen = 0.0  # heat / Karen meter, 0..100
        self.simon_tick = 0
        self.selected_rival = 0
        self.unlocked_rival = 0

    def rep(self) -> str:
        return rep_title(self.cred)

    def can_afford(self, cost: float) -> bool:
        return self.cash >= cost

    def spend(self, cost: float) -> bool:
        if self.cash < cost:
            return False
        self.cash -= cost
        return True

    def earn(self, amount: float):
        self.cash += amount

    def add_cred(self, amount: float):
        self.cred += amount

    def add_heat(self, amount: float):
        self.karen = clamp(self.karen + amount, 0, 100)

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in ("name", "cash", "cred", "karen", "simon_tick", "selected_rival", "unlocked_rival")}

    def from_dict(self, data: dict):
        for key, value in data.items():
            setattr(self, key, value)
