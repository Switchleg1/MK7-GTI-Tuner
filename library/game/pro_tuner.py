from __future__ import annotations

import random

from library.core.constants import PRO_TUNERS


class ProTuner:
    """A green-name pro you can DM once verified (Ed, Dave, ...). Each can hand you
    one pro-only map stage, but only after you've sold enough tunes to be taken
    seriously. Roster is data-driven (constants.PRO_TUNERS) -- add more freely."""

    def __init__(self, handle, name, grant_map, min_tunes, lines):
        self.handle = handle
        self.name = name
        self.grant_map = grant_map
        self.min_tunes = min_tunes
        self.lines = list(lines)

    def chatter(self) -> str:
        return random.choice(self.lines) if self.lines else "..."

    @classmethod
    def roster(cls) -> list["ProTuner"]:
        return [cls(*row) for row in PRO_TUNERS]
