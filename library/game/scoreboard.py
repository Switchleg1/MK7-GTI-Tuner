from __future__ import annotations

from library.core.constants import ACHIEVEMENTS, SCOREBOARD_NAMES


def build_achievements(unlocked: set) -> list[dict]:
    """The trophy case for the scoreboard's ACHIEVEMENTS pane: every achievement in the
    registry, each flagged unlocked or not. Unlocked trophies float to the top (stable,
    so registry order is kept within each group) so the player sees their haul first."""
    rows = [{"key": key, "label": ach.label, "blurb": ach.blurb, "unlocked": key in unlocked}
            for key, ach in ACHIEVEMENTS.items()]
    rows.sort(key=lambda row: not row["unlocked"])
    return rows


def build_scoreboard(player_name: str, player_score: int) -> list[dict]:
    """The arcade hall-of-fame: the fixed made-up handles (whose scores span a full
    playthrough) plus the player's row, sorted high->low and ranked. The player's row is
    flagged so the board can highlight it; it always appears (one player + the handles)."""
    rows = [{"name": handle, "score": score, "is_player": False} for handle, score in SCOREBOARD_NAMES]
    rows.append({"name": (player_name or "YOU").upper()[:10], "score": int(player_score), "is_player": True})
    rows.sort(key=lambda row: row["score"], reverse=True)
    for index, row in enumerate(rows):
        row["rank"] = index + 1
    return rows
