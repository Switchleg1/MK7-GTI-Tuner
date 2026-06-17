from __future__ import annotations

from library.game.discord_user import DiscordUser


class Admin(DiscordUser):
    """A server admin / pro tuner (Simon, CP4334, Exley, ...). Trusted: their
    presence leans an outcome a little more positive (the troll personas still
    drag it down). Shown with a crown in the member list."""

    role = "admin"
    crown = True

    def lean(self):
        good, bad, money = super().lean()
        return (good * 1.15, bad * 0.9, money)
