from __future__ import annotations

from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectGui import DirectButton, DirectFrame, DirectLabel, DirectSlider
from direct.gui.OnscreenImage import OnscreenImage
from direct.showbase.DirectObject import DirectObject
from panda3d.core import TextNode, TransparencyAttrib, Vec4

from library.core import assets
from library.core.constants import DIM, GREEN, GREEN_2, LINE, PANEL, PANEL_DARK, TEXT, VIOLET, WHITE


class Hud(DirectObject):
    """Base for any 2D screen: a tracked node tree under aspect2d plus draw helpers,
    the shared header, and Simon-pill buttons. ``destroy()`` removes everything."""

    def __init__(self, app, name: str):
        super().__init__()
        self.app = app
        self.font = getattr(app, "mono_font", None)
        self.root = app.aspect2d.attachNewNode(name)
        self.nodes: list = []

    def bounds(self):
        aspect = self.app.getAspectRatio()
        return -aspect + 0.04, aspect - 0.04

    def clear(self):
        for node in self.nodes:
            node.destroy()
        self.nodes.clear()

    def destroy(self):
        self.clear()
        self.root.removeNode()
        self.ignoreAll()

    # -- primitives --------------------------------------------------------
    def label(self, text, pos, scale=0.045, color=TEXT, align=TextNode.ALeft, wordwrap=None, parent=None):
        node = DirectLabel(parent=parent or self.root, text=text, pos=pos, scale=scale, text_fg=color, text_align=align, text_wordwrap=wordwrap, text_font=self.font, frameColor=(0, 0, 0, 0), relief=None)
        self.nodes.append(node)
        return node

    def frame(self, frame_size, pos=(0, 0, 0), color=PANEL, border=LINE):
        node = DirectFrame(parent=self.root, frameSize=frame_size, frameColor=color, pos=pos, relief=DGG.FLAT)
        self.nodes.append(node)
        if border:
            outline = DirectFrame(parent=node, frameSize=frame_size, frameColor=border, relief=DGG.RIDGE, borderWidth=(0.006, 0.006))
            self.nodes.append(outline)
        return node

    def button(self, text, pos, size, command, enabled=True, color=None, text_scale=0.044):
        width, height = size
        fill = color or (GREEN_2 if enabled else Vec4(0.05, 0.08, 0.10, 0.92))
        fg = WHITE if enabled else Vec4(0.32, 0.39, 0.43, 1)
        node = DirectButton(parent=self.root, text=text, command=command if (enabled and command) else None, pos=pos, scale=1, text_scale=text_scale, text_fg=fg, text_align=TextNode.ACenter, text_font=self.font, frameSize=(-width / 2, width / 2, -height / 2, height / 2), frameColor=fill, relief=DGG.FLAT, pressEffect=0)
        self.nodes.append(node)
        return node

    def image(self, key, pos, scale, parent=None):
        node = OnscreenImage(parent=parent or self.root, image=assets.image_path(key), pos=pos, scale=scale)
        node.setTransparency(TransparencyAttrib.MAlpha)
        self.nodes.append(node)
        return node

    def slider(self, pos, value_range, value, width=0.5, command=None):
        """A tracked horizontal DirectSlider. Set ``command`` after building all
        sliders (or pass it here) -- it fires with no args; read ``node['value']``."""
        node = DirectSlider(
            parent=self.root, pos=pos, scale=1, range=value_range, value=value, command=command,
            frameColor=PANEL_DARK, frameSize=(-width / 2, width / 2, -0.018, 0.018), relief=DGG.FLAT,
            thumb_frameColor=GREEN, thumb_frameSize=(-0.02, 0.02, -0.034, 0.034), thumb_relief=DGG.FLAT,
        )
        self.nodes.append(node)
        return node

    # -- pill buttons (Simon style) ---------------------------------------
    def pill(self, text, pos, command, icon=None, width=0.60, height=0.155, color=VIOLET):
        bx, _, bz = pos
        node = DirectButton(parent=self.root, text=text, command=command, pos=pos, scale=1, text_scale=0.05, text_fg=color, text_align=TextNode.ACenter, text_pos=(0.07 if icon else 0.0, -0.016), text_font=self.font, frameSize=(-width / 2, width / 2, -height / 2, height / 2), frameTexture=assets.image_path("simon_button"), frameColor=(1, 1, 1, 1), relief=DGG.FLAT, pressEffect=0)
        node.setTransparency(TransparencyAttrib.MAlpha)
        self.nodes.append(node)
        if icon:
            self.image(icon, (bx - 0.19, 0, bz), 0.058)
        return node

    def back_button(self, command):
        left, _ = self.bounds()
        self.pill("< Back", (left + 0.34, 0, -0.85), command)

    # -- shared header -----------------------------------------------------
    def draw_header(self, game):
        left, right = self.bounds()
        self.frame((left, right, -0.085, 0.085), (0, 0, 0.86), PANEL, border=None)
        self.label("MK7 GTI TUNER", (left + 0.05, 0, 0.89), 0.05, GREEN)
        self.label("EA888  .  SIMOS18.1  .  POPS & BANGS  .  CAREER", (left + 0.05, 0, 0.835), 0.026, DIM)
        self.image("emoji_cash", (right - 1.16, 0, 0.872), 0.028)
        self.label(f"${round(game.bro.cash)}", (right - 1.11, 0, 0.858), 0.036, GREEN)
        self.label(f"ECU {game.car.ecu_status()}", (right - 0.80, 0, 0.858), 0.032, TEXT)
        self.label(f"MAP {game.car.active_slot + 1} {game.car.active_tune().get('name', 'Stock')}", (right - 0.46, 0, 0.858), 0.030, TEXT)
        self.label(f"REP {game.bro.rep()}", (right - 0.03, 0, 0.858), 0.030, TEXT, align=TextNode.ARight)
