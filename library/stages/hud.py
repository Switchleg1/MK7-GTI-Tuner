from __future__ import annotations

from direct.showbase.DirectObject import DirectObject

from library.core.ui.ui_object_controller import UIObjectController


class Hud(DirectObject):
    """Base for any 2D screen: a root node under ``aspect2d`` plus one managed UI
    controller. Subclasses build through ``self.ui`` directly."""

    def __init__(self, app, name: str):
        super().__init__()
        self.app = app
        self.font = getattr(app, "mono_font", None)
        self.root = app.aspect2d.attachNewNode(name)
        self.ui = UIObjectController(app, self.root.attachNewNode(f"{name}-ui"))

    def bounds(self):
        aspect = self.app.getAspectRatio()
        return -aspect + 0.04, aspect - 0.04

    def render(self, dt):
        """Per-frame hook called by the app's render loop. Screens that animate
        (tasks, the garage turntable, toasts) override this; static panels don't."""

    def clear(self):
        self.ui.clear()

    def destroy(self):
        self.clear()
        self.ui.destroy()
        self.root.removeNode()
        self.ignoreAll()
