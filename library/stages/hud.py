from __future__ import annotations

from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectGui import DirectSlider
from direct.gui.OnscreenImage import OnscreenImage
from direct.showbase.DirectObject import DirectObject
from panda3d.core import TextNode, TransparencyAttrib

from library.core.assets import assets
from library.core.constants import (
    BOX_LINE, DIM, GREEN, PANEL, PANEL_DARK, TEXT, VIOLET,
)
from library.core.ui.ui_object_controller import UIObjectController


class Hud(DirectObject):
    """Base for any 2D screen: a tracked node tree under aspect2d plus draw helpers,
    the shared header, and Simon-pill buttons. ``destroy()`` removes everything.

    The remaining convenience primitives delegate to managed UI objects, so legacy
    ``self.label(...)`` / ``self.frame(...)`` calls still build ``Text`` / ``Frame`` /
    ``Button`` objects instead of raw DirectGui nodes.
    """

    def __init__(self, app, name: str):
        super().__init__()
        self.app = app
        self.font = getattr(app, "mono_font", None)
        self.root = app.aspect2d.attachNewNode(name)
        self.hud_ui = UIObjectController(app, self.root.attachNewNode(f"{name}-hud-ui"))
        self.nodes: list = []
        self._hud_id = 0

    def bounds(self):
        aspect = self.app.getAspectRatio()
        return -aspect + 0.04, aspect - 0.04

    def render(self, dt):
        """Per-frame hook called by the app's render loop. Screens that animate
        (tasks, the garage turntable, toasts) override this; static panels don't."""

    def set_visible(self, visible: bool):
        """Show or hide this whole UI tree, including its mouse-pick regions. Uses
        stash/unstash (not hide) so a hidden screen's buttons stop catching clicks."""
        if visible:
            self.root.unstash()
        else:
            self.root.stash()

    def clear(self):
        self.hud_ui.clear()
        for node in self.nodes:
            node.destroy()
        self.nodes.clear()
        self._hud_id = 0

    def destroy(self):
        self.clear()
        self.hud_ui.destroy()
        self.root.removeNode()
        self.ignoreAll()

    # -- primitives --------------------------------------------------------
    def _key(self, prefix: str) -> str:
        self._hud_id += 1
        return f"{prefix}-{self._hud_id}"

    def label(self, text, pos, scale=0.045, color=TEXT, align=TextNode.ALeft, wordwrap=None, parent=None):
        if parent is not None:
            return self.hud_ui.add_text(self._key("label"), text, pos, scale, color, align, wordwrap)
        return self.hud_ui.add_text(self._key("label"), text, pos, scale, color, align, wordwrap)

    def frame(self, frame_size, pos=(0, 0, 0), color=PANEL, border=BOX_LINE):
        return self.hud_ui.add_frame(self._key("frame"), frame_size=frame_size, pos=pos, color=color, border=border)

    def button(self, text, pos, size, command, enabled=True, color=None, text_scale=0.044):
        return self.hud_ui.add_button(
            self._key("button"), text, pos, size, command, enabled, color, text_scale)

    def image(self, key, pos, scale, parent=None):
        node = OnscreenImage(parent=parent or self.root, image=assets.image_path(key), pos=pos, scale=scale)
        node.setTransparency(TransparencyAttrib.MAlpha)
        self.nodes.append(node)
        return node

    def slider(self, pos, value_range, value, width=0.5, command=None):
        """A tracked horizontal DirectSlider with a round knob thumb (knob.png) on
        a rounded translucent track. Set ``command`` after building all sliders (or
        pass it here) -- it fires with no args; read ``node['value']``."""
        box = assets.image_path("ui_box")
        node = DirectSlider(
            parent=self.root, pos=pos, scale=1, range=value_range, value=value, command=command,
            frameColor=PANEL_DARK, frameSize=(-width / 2, width / 2, -0.016, 0.016), relief=DGG.FLAT, frameTexture=box,
            thumb_frameColor=(1, 1, 1, 1), thumb_frameSize=(-0.032, 0.032, -0.032, 0.032),
            thumb_relief=DGG.FLAT, thumb_frameTexture=assets.image_path("knob"),
        )
        node.setTransparency(TransparencyAttrib.MAlpha)
        node.thumb.setTransparency(TransparencyAttrib.MAlpha)
        self.nodes.append(node)
        return node

    # -- pill buttons (Simon style) ---------------------------------------
    def pill(self, text, pos, command, icon=None, width=0.60, height=0.155, color=VIOLET):
        return self.hud_ui.add_button(
            self._key("pill"), text, pos, (width, height), command, True, color, 0.05,
            style="pill", icon=icon)

    def back_button(self, command):
        left, _ = self.bounds()
        self.pill("< Back", (left + 0.34, 0, -0.85), command)

    # -- shared header -----------------------------------------------------
    def draw_header(self, game):
        left, right = self.bounds()
        self.frame((left, right, -0.085, 0.085), (0, 0, 0.86), PANEL, border=None)
        self.label("MK7 GTI TUNER", (left + 0.05, 0, 0.89), 0.05, GREEN)
        self.label("EA888  .  SIMOS18.1  .  POPS & BANGS  .  CAREER", (left + 0.05, 0, 0.835), 0.026, DIM)
        # Right side: two right-aligned lines. The old fixed-x labels overlapped
        # once names/rep titles got long (e.g. "Crackle Monster", "Wanted by the
        # HOA") -- right-aligning whole lines keeps them from colliding.
        name = str(game.car.active_tune().get("name", "Stock"))[:16]
        self.label(f"${round(game.bro.cash)}   .   ECU {game.car.ecu_status()}", (right - 0.04, 0, 0.888), 0.033, GREEN, align=TextNode.ARight)
        self.label(f"MAP {game.car.active_slot + 1} {name}   .   REP {game.bro.rep()}", (right - 0.04, 0, 0.832), 0.027, TEXT, align=TextNode.ARight)
