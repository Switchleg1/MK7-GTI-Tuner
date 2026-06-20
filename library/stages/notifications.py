from __future__ import annotations

from panda3d.core import TextNode

from library.core.constants import AMBER, OVERLAY_BIN, OVERLAY_SORT, PANEL_DARK, TEXT, WHITE
from library.core.constants import GREEN as GREEN
from library.core.ui.ui_object_controller import UIObjectController

TOAST_LIFE = 4.5
DAVE_LIFE = 4.6
FADE = 0.6


class Notifications:
    """App-level overlay that lives for the whole session (above every stage):

    - **Achievement toasts** slide in top-right and stack, then fade out.
    - **Dyno Dave** pipes up in a top-left bubble with a reactive quip.

    It's purely a view: the model fills ``game.toast_queue`` (achievement labels)
    and ``game.dave_queue`` (Dave lines); this drains them each frame. Drawn in the
    overlay bin so it sits on top of stage UI and the other overlays."""

    def __init__(self, app, game):
        self.app = app
        self.game = game
        self.font = getattr(app, "mono_font", None)
        self.root = app.aspect2d.attachNewNode("notifications")
        self.root.setBin(OVERLAY_BIN, OVERLAY_SORT["notify"])
        self.toasts = []
        self.dave = None

    def render(self, dt):
        """Called each frame by the app's render loop: drain the model's queues and
        animate the achievement toasts + Dyno Dave bubble."""
        while self.game.toast_queue:
            self._add_toast(self.game.toast_queue.pop(0))
        if self.game.dave_queue:
            line = self.game.dave_queue.pop()  # show the newest, drop the rest
            self.game.dave_queue.clear()
            self._set_dave(line)
        self._tick_toasts(dt)
        self._tick_dave(dt)

    # -- achievement toasts ------------------------------------------------
    def _add_toast(self, label):
        right = self.app.getAspectRatio() - 0.05
        w, h = 0.82, 0.13
        layer = self.root.attachNewNode("achievement-toast")
        layer.setBin(OVERLAY_BIN, OVERLAY_SORT["notify"] + 1)
        layer.setPos(right + w, 0, 0.72)
        ui = UIObjectController(self.app, layer)
        ui.add_frame("frame", frame_size=(-w / 2, w / 2, -h / 2, h / 2), color=PANEL_DARK, border=None, texture=None)
        ui.add_frame("accent", frame_size=(-w / 2, -w / 2 + 0.02, -h / 2, h / 2), color=GREEN, border=None, texture=None)
        ui.add_text("title", "ACHIEVEMENT UNLOCKED", (-w / 2 + 0.06, 0, 0.022), 0.025, GREEN, TextNode.ALeft)
        ui.add_text("label", label, (-w / 2 + 0.06, 0, -0.035), 0.034, WHITE, TextNode.ALeft)
        self.toasts.append({"ui": ui, "layer": layer, "life": TOAST_LIFE, "x": right + w, "anchor": right - w / 2})

    def _tick_toasts(self, dt):
        top, step = 0.72, 0.16
        for i, t in enumerate(list(self.toasts)):
            t["life"] -= dt
            t["x"] += (t["anchor"] - t["x"]) * min(1.0, dt * 10)
            layer = t["layer"]
            z = layer.getZ() + (top - i * step - layer.getZ()) * min(1.0, dt * 9)
            layer.setPos(t["x"], 0, z)
            layer.setColorScale(1, 1, 1, 1.0 if t["life"] > FADE else max(0.0, t["life"] / FADE))
            if t["life"] <= 0:
                t["ui"].destroy()
                self.toasts.remove(t)

    # -- Dyno Dave bubble --------------------------------------------------
    def _set_dave(self, line):
        if self.dave is None:
            left = -self.app.getAspectRatio() + 0.05
            w, h = 0.98, 0.17
            layer = self.root.attachNewNode("dave-toast")
            layer.setBin(OVERLAY_BIN, OVERLAY_SORT["notify"] + 1)
            layer.setPos(left + w / 2, 0, 0.70)
            ui = UIObjectController(self.app, layer)
            ui.add_frame("frame", frame_size=(-w / 2, w / 2, -h / 2, h / 2), color=PANEL_DARK, border=None, texture=None)
            ui.add_frame("accent", frame_size=(-w / 2, w / 2, h / 2 - 0.006, h / 2), color=AMBER, border=None, texture=None)
            ui.add_text("title", "DYNO DAVE", (-w / 2 + 0.05, 0, 0.04), 0.025, AMBER, TextNode.ALeft)
            ui.add_text("line", line, (-w / 2 + 0.05, 0, -0.025), 0.030, TEXT, TextNode.ALeft, wordwrap=29)
            self.dave = {"ui": ui, "layer": layer, "life": DAVE_LIFE}
        else:
            self.dave["ui"].get("line").text(line)
            self.dave["life"] = DAVE_LIFE
            self.dave["layer"].setColorScale(1, 1, 1, 1)

    def _tick_dave(self, dt):
        if not self.dave:
            return
        self.dave["life"] -= dt
        self.dave["layer"].setColorScale(1, 1, 1, 1.0 if self.dave["life"] > FADE else max(0.0, self.dave["life"] / FADE))
        if self.dave["life"] <= 0:
            self.dave["ui"].destroy()
            self.dave = None
