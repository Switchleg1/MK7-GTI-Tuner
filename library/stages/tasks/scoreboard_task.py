from __future__ import annotations

import time

from panda3d.core import TextNode

from library.core.constants import (
    AMBER, ARCADE_BG, ARCADE_SCANLINE, BLUE, DIM, GREEN, MAGENTA, TEXT, VIOLET, WHITE,
)
from library.game.scoreboard import build_achievements, build_scoreboard
from library.stages.task_base import TaskBase

CENTER, LEFT, RIGHT = TextNode.ACenter, TextNode.ALeft, TextNode.ARight


class ScoreboardTask(TaskBase):
    """An 80s-arcade HALL OF FAME. The score IS the bro's cred (races + pops & bangs +
    tune sales + achievements + the Bench Wizard's Trial all feed it), shown big and then
    ranked on a CRT-style high-score board against made-up handles whose fixed scores span
    a full playthrough -- so you climb the board as you progress. An ACHIEVEMENTS button
    pulls up a scrollable trophy pane over the board (without disturbing it). Pure 2D."""

    title = "HIGH SCORES"
    key = "scoreboard"
    live = False  # static board; tick() only blinks the player row + the prompt

    # high-score table columns (x) and the row block (top z + spacing)
    X_RANK, X_NAME, X_SCORE, X_MARK = -0.58, -0.50, 0.58, 0.66
    ROW_TOP, ROW_GAP = 0.21, 0.063
    # trophy pane: how many trophies show at once, and the row block geometry
    ACH_ROWS, ACH_TOP, ACH_GAP, ACH_X = 6, 0.17, 0.115, -0.68

    def build_scene(self):
        pass  # the scoreboard is a pure 2D arcade screen -- no 3D garage behind it

    def build_ui(self):
        self.show_ach = False
        self.ach_scroll = 0
        self.ach = build_achievements(self.game.achievements)
        self._build_board()
        self._build_ach_pane()  # built once, hidden until the ACHIEVEMENTS button is hit

    # -- the high-score board ---------------------------------------------
    def _build_board(self):
        bro = self.game.bro
        # Arcade backdrop (below the header bar) + faint CRT scanlines behind everything.
        self.ui.add_frame("backdrop", frame_size=(-2.2, 2.2, -1.0, 0.77), color=ARCADE_BG, border=None)
        z = 0.74
        i = 0
        while z > -0.95:
            self.ui.add_frame(f"scan-{i}", frame_size=(-2.2, 2.2, z, z + 0.004), color=ARCADE_SCANLINE, border=None)
            z -= 0.05
            i += 1
        # Marquee + the player's big score + a stats line + the trophy-pane button.
        self.ui.add_text("marquee", "*   H A L L   O F   F A M E   *", (0, 0, 0.60), 0.045, MAGENTA, CENTER)
        self.ui.add_text("score", f"YOUR SCORE   {bro.cred:,}", (0, 0, 0.46), 0.052, AMBER, CENTER)
        self.ui.add_text("stats", self._stats_line(), (0, 0, 0.38), 0.026, BLUE, CENTER)
        self.ui.add_button("open-ach", "ACHIEVEMENTS", (self._right() - 0.31, 0, 0.50), (0.5, 0.085),
                           self._open_ach, True, VIOLET, 0.03)
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

    # -- the trophy pane (over the board) ---------------------------------
    def _build_ach_pane(self):
        """A scrollable trophy case, built once and hidden. Opening it hides the board and
        shows these objects; CLOSE flips it back. Every object here is keyed ``ach-*`` so
        the board/pane visibility swap can toggle each group by prefix."""
        self.ui.add_frame("ach-bg", frame_size=(-2.2, 2.2, -1.0, 0.77), color=ARCADE_BG, border=None)
        self.ui.add_text("ach-title", "*  T R O P H Y   C A S E  *", (0, 0, 0.58), 0.045, MAGENTA, CENTER)
        self.ui.add_text("ach-count", "", (0, 0, 0.30), 0.030, AMBER, CENTER)
        for i in range(self.ACH_ROWS):
            z = self.ACH_TOP - i * self.ACH_GAP
            self.ui.add_text(f"ach-mark-{i}", "", (self.ACH_X, 0, z), 0.034, GREEN, LEFT)
            self.ui.add_text(f"ach-label-{i}", "", (self.ACH_X + 0.08, 0, z), 0.034, TEXT, LEFT)
            self.ui.add_text(f"ach-blurb-{i}", "", (self.ACH_X + 0.08, 0, z - 0.045), 0.024, DIM, LEFT, wordwrap=52)
        self.ui.add_button("ach-up", "▲", (0.74, 0, 0.06), (0.13, 0.11), lambda: self._scroll_ach(-1), True, BLUE, 0.05)
        self.ui.add_button("ach-down", "▼", (0.74, 0, -0.10), (0.13, 0.11), lambda: self._scroll_ach(1), True, BLUE, 0.05)
        self.ui.add_text("ach-pos", "", (0.74, 0, -0.22), 0.022, DIM, CENTER)
        self.ui.add_text("ach-hint", "WHEEL or ▲ ▼ TO SCROLL", (-0.2, 0, -0.55), 0.024, DIM, CENTER)
        self.ui.add_button("ach-close", "CLOSE", (0.5, 0, -0.55), (0.4, 0.10), self._close_ach, True, MAGENTA, 0.038)
        self._set_pane_visible(False)

    def _open_ach(self):
        self.show_ach = True
        self.ach_scroll = 0
        self.ach = build_achievements(self.game.achievements)  # refresh in case new trophies landed
        self._set_board_visible(False)
        self._set_pane_visible(True)
        self._refresh_ach()
        self.ui.lift()

    def _close_ach(self):
        self.show_ach = False
        self._set_pane_visible(False)
        self._set_board_visible(True)
        self.ui.lift()

    def _scroll_ach(self, delta):
        if not self.show_ach:
            return
        ceiling = max(0, len(self.ach) - self.ACH_ROWS)
        self.ach_scroll = max(0, min(ceiling, self.ach_scroll + delta))
        self._refresh_ach()

    def _refresh_ach(self):
        total = len(self.ach)
        unlocked = sum(1 for row in self.ach if row["unlocked"])
        self.ui.get("ach-count").text(f"UNLOCKED  {unlocked} / {total}")
        for i in range(self.ACH_ROWS):
            mark, label, blurb = self.ui.get(f"ach-mark-{i}"), self.ui.get(f"ach-label-{i}"), self.ui.get(f"ach-blurb-{i}")
            index = self.ach_scroll + i
            if index >= total:
                for obj in (mark, label, blurb):
                    obj.is_visible(False)
                continue
            row = self.ach[index]
            won = row["unlocked"]
            mark.text("*" if won else "-")
            mark.color(GREEN if won else DIM)
            label.text(row["label"])
            label.color(AMBER if won else DIM)
            blurb.text(row["blurb"])
            for obj in (mark, label, blurb):
                obj.is_visible(True)
        start = self.ach_scroll + 1
        self.ui.get("ach-pos").text(f"{start}-{min(self.ach_scroll + self.ACH_ROWS, total)} / {total}")

    def _set_pane_visible(self, flag):
        for key, obj in self.ui.objects.items():
            if key.startswith("ach-"):
                obj.is_visible(flag)

    def _set_board_visible(self, flag):
        for key, obj in self.ui.objects.items():
            if not key.startswith("ach-") and not key.startswith("header") and key != "task-title":
                obj.is_visible(flag)

    def _right(self):
        return self.bounds()[1]

    # -- input + per-frame -------------------------------------------------
    def bind_keys(self):
        self.accept("wheel_up", lambda: self._scroll_ach(-1))
        self.accept("wheel_down", lambda: self._scroll_ach(1))
        self.accept("arrow_up", lambda: self._scroll_ach(-1))
        self.accept("arrow_down", lambda: self._scroll_ach(1))

    def tick(self, dt):
        if self.show_ach:
            return  # the trophy pane is up; leave the (hidden) board alone
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
