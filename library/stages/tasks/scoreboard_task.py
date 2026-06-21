from __future__ import annotations

import time

from panda3d.core import TextNode

from library.core.constants import (
    AMBER, ARCADE_BG, ARCADE_SCANLINE, BLUE, DIM, GREEN, MAGENTA, TEXT, WHITE,
)
from library.game.scoreboard import build_scoreboard
from library.stages.task_base import TaskBase

CENTER, LEFT, RIGHT = TextNode.ACenter, TextNode.ALeft, TextNode.ARight


class ScoreboardTask(TaskBase):
    """An 80s-arcade HALL OF FAME. The bro's running ``score`` (races + pops & bangs +
    achievements + the Bench Wizard's Trial) is shown big, then ranked on a CRT-style
    high-score board against made-up handles whose fixed scores span a full playthrough --
    so you climb the board as you progress. Pure 2D (no garage scene)."""

    title = "HIGH SCORES"
    key = "scoreboard"
    live = False  # static board; tick() only blinks the player row + the prompt

    # table columns (x) and the row block (top z + spacing)
    X_RANK, X_NAME, X_SCORE, X_MARK = -0.58, -0.50, 0.58, 0.66
    ROW_TOP, ROW_GAP = 0.21, 0.063

    def build_scene(self):
        pass  # the scoreboard is a pure 2D arcade screen -- no 3D garage behind it

    def build_ui(self):
        bro, game = self.game.bro, self.game
        # Arcade backdrop (below the header bar) + faint CRT scanlines behind everything.
        self.ui.add_frame("backdrop", frame_size=(-2.2, 2.2, -1.0, 0.77), color=ARCADE_BG, border=None)
        z = 0.74
        i = 0
        while z > -0.95:
            self.ui.add_frame(f"scan-{i}", frame_size=(-2.2, 2.2, z, z + 0.004), color=ARCADE_SCANLINE, border=None)
            z -= 0.05
            i += 1
        # Marquee + the player's big score + a stats line.
        self.ui.add_text("marquee", "*   H A L L   O F   F A M E   *", (0, 0, 0.60), 0.045, MAGENTA, CENTER)
        self.ui.add_text("score", f"YOUR SCORE   {bro.cred:,}", (0, 0, 0.46), 0.052, AMBER, CENTER)
        self.ui.add_text("stats", self._stats_line(), (0, 0, 0.38), 0.026, BLUE, CENTER)
        # Column header.
        self.ui.add_text("h-rank", "RANK", (self.X_RANK, 0, 0.29), 0.022, DIM, RIGHT)
        self.ui.add_text("h-name", "NAME", (self.X_NAME, 0, 0.29), 0.022, DIM, LEFT)
        self.ui.add_text("h-score", "SCORE", (self.X_SCORE, 0, 0.29), 0.022, DIM, RIGHT)
        # The ranked rows (built once; the player's row blinks in tick()).
        self._player_i = 0
        for i, row in enumerate(build_scoreboard(bro.name, bro.cred)):
            z = self.ROW_TOP - i * self.ROW_GAP
            color = self._row_color(row)
            self.ui.add_text(f"row-{i}-rank", f"{row['rank']}", (self.X_RANK, 0, z), 0.034, color, RIGHT)
            self.ui.add_text(f"row-{i}-name", row["name"], (self.X_NAME, 0, z), 0.034, color, LEFT)
            self.ui.add_text(f"row-{i}-score", f"{row['score']:,}", (self.X_SCORE, 0, z), 0.034, color, RIGHT)
            if row["is_player"]:
                self._player_i = i
                self.ui.add_text(f"row-{i}-mark", "◄ YOU", (self.X_MARK, 0, z), 0.030, WHITE, LEFT)
        self.ui.add_text("prompt", "◄  BACK TO EXIT", (0, 0, -0.46), 0.028, DIM, CENTER)

    def _stats_line(self) -> str:
        bro, game = self.game.bro, self.game
        line = (f"LADDER {min(bro.unlocked_rival + 1, len(game.rivals))}/{len(game.rivals)}"
                f"     POPS {bro.total_pops}     BADGES {len(game.achievements)}")
        return line + ("     * GOD MODE *" if bro.god else "")

    @staticmethod
    def _row_color(row):
        if row["is_player"]:
            return WHITE
        if row["rank"] == 1:
            return AMBER       # the untouchable top legend, in gold
        if row["rank"] <= 3:
            return TEXT
        return DIM

    def tick(self, dt):
        # Blink the player's row (white <-> green) and the exit prompt, arcade-style.
        on = int(time.perf_counter() * 2) % 2 == 0
        prompt = self.ui.get("prompt")
        if prompt is not None:
            prompt.is_visible(on)
        color = WHITE if on else GREEN
        for part in ("rank", "name", "score", "mark"):
            obj = self.ui.get(f"row-{self._player_i}-{part}")
            if obj is not None:
                obj.color(color)
