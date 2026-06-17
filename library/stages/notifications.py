from __future__ import annotations

from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectGui import DirectFrame, DirectLabel
from direct.task import Task
from panda3d.core import ClockObject, TextNode

from library.core.constants import AMBER, PANEL_DARK, TEXT, WHITE
from library.core.constants import GREEN as GREEN

TOAST_LIFE = 4.5
DAVE_LIFE = 4.6
FADE = 0.6


class Notifications:
    """App-level overlay that lives for the whole session (above every stage):

    - **Achievement toasts** slide in top-right and stack, then fade out.
    - **Dyno Dave** pipes up in a top-left bubble with a reactive quip.

    It's purely a view: the model fills ``game.toast_queue`` (achievement labels)
    and ``game.dave_queue`` (Dave lines); this drains them each frame. Drawn in the
    ``fixed`` bin so it sits on top of task panels."""

    def __init__(self, app, game):
        self.app = app
        self.game = game
        self.font = getattr(app, "mono_font", None)
        self.root = app.aspect2d.attachNewNode("notifications")
        self.root.setBin("fixed", 1000)
        self.toasts = []
        self.dave = None
        app.taskMgr.add(self._update, "notifications")

    def _update(self, task):
        dt = ClockObject.getGlobalClock().getDt()
        while self.game.toast_queue:
            self._add_toast(self.game.toast_queue.pop(0))
        if self.game.dave_queue:
            line = self.game.dave_queue.pop()  # show the newest, drop the rest
            self.game.dave_queue.clear()
            self._set_dave(line)
        self._tick_toasts(dt)
        self._tick_dave(dt)
        return Task.cont

    # -- achievement toasts ------------------------------------------------
    def _add_toast(self, label):
        right = self.app.getAspectRatio() - 0.05
        w, h = 0.82, 0.13
        frame = DirectFrame(parent=self.root, frameSize=(-w / 2, w / 2, -h / 2, h / 2),
                            frameColor=PANEL_DARK, relief=DGG.FLAT, pos=(right + w, 0, 0.72))
        frame.setBin("fixed", 1001)
        frame.setTransparency(1)
        DirectFrame(parent=frame, frameSize=(-w / 2, -w / 2 + 0.02, -h / 2, h / 2), frameColor=GREEN, relief=DGG.FLAT)
        DirectLabel(parent=frame, text="ACHIEVEMENT UNLOCKED", pos=(-w / 2 + 0.06, 0, 0.022), scale=0.025,
                    text_fg=GREEN, text_align=TextNode.ALeft, text_font=self.font, frameColor=(0, 0, 0, 0), relief=None)
        DirectLabel(parent=frame, text=label, pos=(-w / 2 + 0.06, 0, -0.035), scale=0.034,
                    text_fg=WHITE, text_align=TextNode.ALeft, text_font=self.font, frameColor=(0, 0, 0, 0), relief=None)
        self.toasts.append({"frame": frame, "life": TOAST_LIFE, "x": right + w, "anchor": right - w / 2})

    def _tick_toasts(self, dt):
        top, step = 0.72, 0.16
        for i, t in enumerate(list(self.toasts)):
            t["life"] -= dt
            t["x"] += (t["anchor"] - t["x"]) * min(1.0, dt * 10)
            frame = t["frame"]
            z = frame.getZ() + (top - i * step - frame.getZ()) * min(1.0, dt * 9)
            frame.setPos(t["x"], 0, z)
            frame.setColorScale(1, 1, 1, 1.0 if t["life"] > FADE else max(0.0, t["life"] / FADE))
            if t["life"] <= 0:
                frame.removeNode()
                self.toasts.remove(t)

    # -- Dyno Dave bubble --------------------------------------------------
    def _set_dave(self, line):
        if self.dave is None:
            left = -self.app.getAspectRatio() + 0.05
            w, h = 0.98, 0.17
            frame = DirectFrame(parent=self.root, frameSize=(-w / 2, w / 2, -h / 2, h / 2),
                                frameColor=PANEL_DARK, relief=DGG.FLAT, pos=(left + w / 2, 0, 0.70))
            frame.setBin("fixed", 1001)
            frame.setTransparency(1)
            DirectFrame(parent=frame, frameSize=(-w / 2, w / 2, h / 2 - 0.006, h / 2), frameColor=AMBER, relief=DGG.FLAT)
            DirectLabel(parent=frame, text="DYNO DAVE", pos=(-w / 2 + 0.05, 0, 0.04), scale=0.025,
                        text_fg=AMBER, text_align=TextNode.ALeft, text_font=self.font, frameColor=(0, 0, 0, 0), relief=None)
            label = DirectLabel(parent=frame, text=line, pos=(-w / 2 + 0.05, 0, -0.025), scale=0.030,
                                text_fg=TEXT, text_align=TextNode.ALeft, text_wordwrap=29, text_font=self.font,
                                frameColor=(0, 0, 0, 0), relief=None)
            self.dave = {"frame": frame, "label": label, "life": DAVE_LIFE}
        else:
            self.dave["label"]["text"] = line
            self.dave["life"] = DAVE_LIFE
            self.dave["frame"].setColorScale(1, 1, 1, 1)

    def _tick_dave(self, dt):
        if not self.dave:
            return
        self.dave["life"] -= dt
        self.dave["frame"].setColorScale(1, 1, 1, 1.0 if self.dave["life"] > FADE else max(0.0, self.dave["life"] / FADE))
        if self.dave["life"] <= 0:
            self.dave["frame"].removeNode()
            self.dave = None
