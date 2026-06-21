from __future__ import annotations

from library.core.constants import SCOREBOARD_NAMES


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
