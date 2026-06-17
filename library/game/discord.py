from __future__ import annotations

import random

from library.core.utils import clamp, pick
from library.game.simos import build_context, select_insight

# ---------------------------------------------------------------------------
# The SimosTools Discord, as a character. EDIT FREELY: drop in your real handles,
# roles and running bits. "role" drives the reply colour in the panel; the "vet"
# has no canned lines -- it speaks the live, state-aware tip from the Simon rules
# engine, so the one helpful reply actually reads your tune.
# (No emoji in the text -- the mono UI font can't render them.)
# ---------------------------------------------------------------------------
DISCORD_MEMBERS = {
    "log":  {"name": "PostALog",      "lines": ["post a log", "datalog or it didn't happen",
                                                 "3rd gear pull, full send, then post the longview", "no log? bold strategy"]},
    "gate": {"name": "mod_static",    "lines": ["known issue, search the channel", "read the pinned message",
                                                 "moved to #noob-questions", "this has been asked 100 times"]},
    "hype": {"name": "send_it_steve", "lines": ["SEND IT", "tune it till it breaks, then back off one click",
                                                 "stage 2 isn't a stage, it's a lifestyle", "just delete the cat lol"]},
    "corn": {"name": "corn_dad",      "lines": ["what's your ethanol content?", "blend more corn",
                                                 "E85 fixes everything except your wallet", "did you re-log after the blend?"]},
    "dev":  {"name": "the_dev",       "lines": ["it's open source, PR it", "works on my bench",
                                                 "did you ECM3 patch first?", "skill issue", "that's a you problem, not a tool problem"]},
    "vet":  {"name": "boost_vet",     "lines": []},  # speaks the live Simon tip
}
NOLOG_LINES = ["post a log first", "did you even search?", "no log, no help", "read the pinned before posting", "we're not mind readers, log it"]


def _name(role):
    return DISCORD_MEMBERS[role]["name"]


def _line(role):
    return pick(DISCORD_MEMBERS[role]["lines"])


def thread(game, posted_log: bool, tick: int = 0) -> list[dict]:
    """Compose a #help thread: a list of {name, text, kind} replies. Without a log
    it's all dismissive; with a log the 'vet' usually drops a real (state-aware)
    tip, the odds rising with your street cred / rep."""
    ctx = build_context(game, "discord")
    cred = ctx.get("cred", 0)
    out = []
    if not posted_log:
        out.append({"name": _name("log"), "text": pick(NOLOG_LINES), "kind": "dismiss"})
        out.append({"name": _name("gate"), "text": _line("gate"), "kind": "dismiss"})
        if random.random() < 0.6:
            out.append({"name": _name("hype"), "text": _line("hype"), "kind": "hype"})
        return out
    # log posted -> a real thread
    out.append({"name": _name("log"), "text": _line("log"), "kind": "dismiss"})  # someone always says it anyway
    if random.random() < clamp(0.45 + cred / 400.0, 0.45, 0.95):
        out.append({"name": _name("vet"), "text": select_insight(ctx, tick)["tip"], "kind": "help"})
    else:
        out.append({"name": _name("gate"), "text": _line("gate"), "kind": "dismiss"})
    role = random.choice(["hype", "corn", "dev"])
    out.append({"name": _name(role), "text": _line(role), "kind": role})
    return out
