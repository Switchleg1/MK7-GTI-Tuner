from __future__ import annotations

from library.core.constants import (
    BOX_LINE, GREEN, OVERLAY_BIN, OVERLAY_SORT, PANEL_DARK, TOAST_FADE, TOAST_H, TOAST_SECONDS,
    TOAST_W, TOAST_Z, WHITE,
)
from library.stages.hud import Hud


class Toast(Hud):
    """A single game-level toast prompt (bottom-centre, above every stage). Call
    ``show(title, message, seconds)`` to flash a message; it holds for ``seconds``
    then fades out over ``TOAST_FADE``. Used for the "now playing" music notice, but
    generic. Driven by ``render(dt)`` from the app's render loop."""

    def __init__(self, app):
        super().__init__(app, "toast")
        self.root.setBin(OVERLAY_BIN, OVERLAY_SORT["toast"])  # above stage UI + panels
        self.life = 0.0

    def show(self, title: str, message: str, seconds: float = TOAST_SECONDS):
        self.clear()
        x0, x1 = -TOAST_W / 2, TOAST_W / 2
        z0, z1 = TOAST_Z - TOAST_H / 2, TOAST_Z + TOAST_H / 2
        self.ui.add_frame("frame", frame_size=(x0, x1, z0, z1), color=PANEL_DARK, border=BOX_LINE)
        self.ui.add_frame("accent", frame_size=(x0 + 0.012, x0 + 0.03, z0 + 0.012, z1 - 0.012),
                          color=GREEN, border=None)
        self.ui.add_text("title", title, (x0 + 0.06, 0, TOAST_Z + 0.022), 0.024, GREEN)
        self.ui.add_text("message", message, (x0 + 0.06, 0, TOAST_Z - 0.028), 0.038, WHITE, wordwrap=42)
        self.life = max(0.01, seconds)
        self.root.setColorScale(1, 1, 1, 1)

    def render(self, dt):
        if self.life <= 0:
            return
        self.life -= dt
        alpha = 1.0 if self.life > TOAST_FADE else max(0.0, self.life / TOAST_FADE)
        self.root.setColorScale(1, 1, 1, alpha)
        if self.life <= 0:
            self.clear()
            self.root.setColorScale(1, 1, 1, 1)
