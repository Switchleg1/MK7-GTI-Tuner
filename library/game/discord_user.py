from __future__ import annotations

import random

from library.core.constants import PERSONA_LEAN
from library.core.utils import pick


class DiscordUser:
    """Base for a Discord member: identity, an online roll, ambient chatter, and a
    persona ``lean`` that biases a help-request outcome.

    Subclasses (Admin / GreenName / NormalUser) set the ``role`` and nudge the lean;
    the per-member ``persona`` (from the roster table) supplies the flavour. Built to
    serialize with the game (only ``online`` is transient)."""

    role = "user"

    def __init__(self, handle, name, persona, online_chance, color, status, lines):
        self.handle = handle
        self.name = name
        self.persona = persona
        self.online_chance = online_chance
        self.color = color
        self.status = status
        self.lines = list(lines)
        self.online = False

    def roll_online(self) -> bool:
        self.online = random.random() < self.online_chance
        return self.online

    def chatter(self) -> str:
        return pick(self.lines) if self.lines else "..."

    def lean(self) -> tuple[float, float, float]:
        """(good_weight, bad_weight, money_pull) for the outcome engine."""
        return PERSONA_LEAN.get(self.persona, (1.0, 1.0, 0.0))
