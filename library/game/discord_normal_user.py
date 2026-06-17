from __future__ import annotations

from library.game.discord_user import DiscordUser


class NormalUser(DiscordUser):
    """A regular member (Brimstone, Tacos, ...). No role bias -- the persona lean
    is the whole story, so the troll's bad advice and the needy guy's bad luck
    come through untouched."""

    role = "user"
