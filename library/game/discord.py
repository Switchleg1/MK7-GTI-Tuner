from __future__ import annotations

import random

from library.core.constants import (
    COMMUNITY_MAPS, DISCORD_ACTIVE_CHANNEL, DISCORD_BAD, DISCORD_CHANNELS, DISCORD_GOOD,
    DISCORD_GOOD_WORDS, DISCORD_LOG_WORDS, DISCORD_NOLOG, DISCORD_ROSTER,
)
from library.core.utils import clamp, pick
from library.game.discord_admin import Admin
from library.game.discord_green_name import GreenName
from library.game.discord_normal_user import NormalUser

ROLE_CLASS = {"admin": Admin, "greenname": GreenName, "user": NormalUser}


def _build_member(row):
    handle, name, role, persona, online, color, status, lines = row
    return ROLE_CLASS[role](handle, name, persona, online, color, status, lines)


class Discord:
    """The "MQB Vibe Coders" server, as a game system.

    Builds the member roster from ``DISCORD_ROSTER`` (each row -> an Admin /
    GreenName / NormalUser), samples who's online, supplies ambient chatter for the
    channel backlog, and resolves a typed help request into an outcome: text quality
    plus the lean of whoever's online plus a dice roll decide good vs bad."""

    def __init__(self):
        self.members = [_build_member(row) for row in DISCORD_ROSTER]
        self.by_handle = {m.handle: m for m in self.members}
        self.channels = list(DISCORD_CHANNELS)
        self.active_channel = DISCORD_ACTIVE_CHANNEL
        self.refresh_online()

    # -- presence ----------------------------------------------------------
    def refresh_online(self) -> list:
        for member in self.members:
            member.roll_online()
        if not any(m.online for m in self.members):  # never an empty room
            pick(self.members).online = True
        return self.online()

    def online(self) -> list:
        return [m for m in self.members if m.online]

    def offline(self) -> list:
        return [m for m in self.members if not m.online]

    def backlog(self, count: int = 4) -> list[dict]:
        """A few ambient messages from online members to seed the channel."""
        roster = self.online() or self.members
        speakers = random.sample(roster, min(count, len(roster)))
        return [{"name": m.name, "color": m.color, "text": m.chatter()} for m in speakers]

    # -- outcome engine ----------------------------------------------------
    def _quality(self, text: str):
        t = text.lower()
        has_log = any(w in t for w in DISCORD_LOG_WORDS)
        good_words = sum(1 for w in DISCORD_GOOD_WORDS if w in t)
        length = clamp(len(t) / 110.0, 0.0, 1.0)
        return has_log, good_words, length

    def resolve(self, text: str, context: dict) -> dict:
        """Return an outcome dict for a help request. ``context`` carries cred and
        the already-unlocked map keys; Game reads ``effect``/``amount`` to apply it.

        Odds favour effort (a datalog word matters most), then nudge with who's
        online -- a room of helpers lifts you, trolls drag you down."""
        online = self.online()
        has_log, good_words, length = self._quality(text)
        good_w = sum(m.lean()[0] for m in online)
        bad_w = sum(m.lean()[1] for m in online)
        money_pull = sum(m.lean()[2] for m in online)
        p_good = clamp(
            0.30 + (0.18 if has_log else -0.14) + good_words * 0.045 + length * 0.05
            + (good_w - bad_w) * 0.012 + context.get("cred", 0) / 1000.0,
            0.05, 0.93,
        )
        good = random.random() < p_good

        effect, amount, summary, actor = self._pick_outcome(good, online, money_pull, context)
        replies = self._replies(text, has_log, good, actor, online)
        return {"kind": "good" if good else "bad", "effect": effect, "amount": amount,
                "map_key": amount if effect == "map" else None, "summary": summary, "replies": replies}

    def _pick_outcome(self, good: bool, online: list, money_pull: float, context: dict):
        pool = DISCORD_GOOD if good else DISCORD_BAD
        # On a strong-money room, favour a cash/map result over plain clout.
        if good and money_pull >= 1.2 and random.random() < 0.6:
            choices = [o for o in DISCORD_GOOD if o[0] in ("cash", "map")] or pool
        else:
            choices = pool
        effect, (lo, hi), template = pick(choices)

        if effect == "map":
            available = [k for k in COMMUNITY_MAPS if k not in context.get("unlocked_maps", [])]
            if not available:  # nothing left to unlock -> a cash tip instead
                effect, (lo, hi), template = ("cash", (60, 160), "{user} would've sent a map but you have them all. +${amt} tip instead")
        actor = self._attribute(good, effect, online)
        if effect == "map":
            key = pick(available)
            summary = template.format(user=actor.name if actor else "someone", amt=COMMUNITY_MAPS[key]["name"])
            return effect, key, summary, actor
        amount = random.randint(int(lo), int(hi))
        summary = template.format(user=actor.name if actor else "someone", amt=amount)
        return effect, amount, summary, actor

    def _attribute(self, good: bool, effect: str, online: list):
        """Pin the result on a fitting online member."""
        if not online:
            return None
        if effect == "map":  # prefer the map's namesake if they're around
            pass
        if good:
            picks = [m for m in online if m.lean()[0] >= 1.3] or online
        else:
            picks = [m for m in online if m.lean()[1] >= 1.3] or online
        return pick(picks)

    def _replies(self, text: str, has_log: bool, good: bool, actor, online: list) -> list[dict]:
        out = []
        if not has_log and online:
            nag = pick(online)
            out.append({"name": nag.name, "color": nag.color, "text": pick(DISCORD_NOLOG)})
        if actor is not None:
            out.append({"name": actor.name, "color": actor.color, "text": actor.chatter()})
        # one more ambient voice if anyone else is around
        others = [m for m in online if m is not actor]
        if others:
            extra = pick(others)
            out.append({"name": extra.name, "color": extra.color, "text": extra.chatter()})
        return out

    def member(self, handle: str):
        return self.by_handle.get(handle)
