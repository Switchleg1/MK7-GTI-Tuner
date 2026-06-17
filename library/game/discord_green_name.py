from __future__ import annotations

from library.game.discord_user import DiscordUser


class GreenName(DiscordUser):
    """A "green name" pro tuner (Gary, Wunder, ...). Loves money -- their presence
    pulls a good outcome toward cash / paid map drops rather than free clout."""

    role = "greenname"

    def lean(self):
        good, bad, money = super().lean()
        return (good, bad, money + 0.6)
