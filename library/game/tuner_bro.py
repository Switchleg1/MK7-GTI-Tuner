from __future__ import annotations

from library.core.utils import clamp
from library.game.tuning import rep_title
from library.core.constants import MINIMUM_BRO_BANK_VALUE


class TunerBro:
    """The user ("the bro"): wallet, reputation, heat, and street-ladder progress.

    Personal stats only — the car build lives in Car. Built to serialize for save
    games (see to_dict/from_dict). Room to grow: emotional_damage, route, skills.
    """

    def __init__(self, name: str = "Bro"):
        self.name                       = name
        self.cash                       = 750
        self.cred                       = 0.0
        self.karen                      = 0.0       # heat / Karen meter, 0..100
        self.simon_tick                 = 0
        self.selected_rival             = 0
        self.unlocked_rival             = 0
        self.unlocked_maps: list[str]   = []        # community/pro map keys earned
        self.green_name                 = False     # verified pro status
        self.tunes_sold                 = 0         # tunes sold to other users (green-name income)
        self.god                        = False     # passed the Bench Wizard's Trial
        self.emotional_damage           = 0.0       # 0..100; high = shaky hands on the strip
        self.total_pops                 = 0
        self.total_busts                = 0
        self.map_switches               = 0

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

    def pay_repair(self, amount: float):
        """Forced spend (broken parts) -- never goes below minimum value."""
        self.cash = max(MINIMUM_BRO_BANK_VALUE, self.cash - amount)
    
    def is_broke(self):
        return self.cash <= 0

    def add_cred(self, amount: float):
        self.cred = max(0.0, self.cred + amount)  # losing clients can't go below zero

    def add_heat(self, amount: float):
        self.karen = clamp(self.karen + amount, 0, 100)

    def add_damage(self, amount: float):
        """Emotional damage, 0..100 (negative amount heals)."""
        self.emotional_damage = clamp(self.emotional_damage + amount, 0, 100)

    def unlock_map(self, key: str) -> bool:
        if key in self.unlocked_maps:
            return False
        self.unlocked_maps.append(key)
        return True

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in (
                "name", "cash", "cred", "karen", 
                "simon_tick", "selected_rival", 
                "unlocked_rival", "unlocked_maps", 
                "green_name", "tunes_sold", "god", 
                "emotional_damage",
                "total_pops", "total_busts",
                "map_switches", "score",
            )
        }

    def from_dict(self, data: dict):
        for key, value in data.items():
            setattr(self, key, value)
