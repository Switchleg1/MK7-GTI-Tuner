from __future__ import annotations

from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectGui import DirectButton, DirectFrame
from panda3d.core import TextNode, TransparencyAttrib, Vec4

from library.core import assets
from library.core.constants import (
    BTN_DISABLED_FILL, BTN_DISABLED_TEXT, BTN_LINE, BUTTON_CLICK_BRIGHTEN, BUTTON_CLICK_HOLD,
    GREEN_2, LINE, WHITE,
)

_UNSET = object()  # "argument not supplied" sentinel (so None can mean "clear it")


def _vec(color) -> Vec4:
    return color if isinstance(color, Vec4) else Vec4(*color)


def _brighten(color: Vec4, factor: float = BUTTON_CLICK_BRIGHTEN) -> Vec4:
    return Vec4(min(1.0, color.x * factor), min(1.0, color.y * factor), min(1.0, color.z * factor), color.w)


class Button:
    """One managed task button: a translucent rounded DirectButton (ui_box fill +
    ui_ring border, the project's glass style) that flashes a "clicked" colour for a
    short hold when pressed, then reverts to its normal/disabled fill.

    Owned by a ButtonController, never destroyed on a redraw, so a click can't be
    dropped by the UI rebuilding mid-press. Properties (text, pos, size, command,
    enabled, normal/clicked colour, hold time) can be changed any time via
    ``configure``; ``render(dt)`` advances the flash timer."""

    def __init__(self, parent, font, *, text, pos, size, command, enabled=True,
                 normal_color=None, clicked_color=None, click_hold=BUTTON_CLICK_HOLD, text_scale=0.044):
        self.font = font
        self.command = command
        self.enabled = enabled
        self.click_hold = BUTTON_CLICK_HOLD if click_hold is None else click_hold
        self.size = size
        self._flash = 0.0
        self.normal_color = _vec(normal_color) if normal_color is not None else _vec(GREEN_2)
        self._auto_clicked = clicked_color is None
        self.clicked_color = _brighten(self.normal_color) if self._auto_clicked else _vec(clicked_color)

        w, h = size
        fs = (-w / 2, w / 2, -h / 2, h / 2)
        self.node = DirectButton(
            parent=parent, text=text, command=self._clicked, pos=pos, scale=1, text_scale=text_scale,
            text_fg=self._text_color(), text_align=TextNode.ACenter, text_font=font, frameSize=fs,
            frameColor=self._fill(), relief=DGG.FLAT, frameTexture=assets.image_path("ui_box"), pressEffect=0)
        self.node.setTransparency(TransparencyAttrib.MAlpha)
        self.ring = DirectFrame(parent=self.node, frameSize=fs, frameColor=self._ring_color(),
                                relief=DGG.FLAT, frameTexture=assets.image_path("ui_ring"))
        self.ring.setTransparency(TransparencyAttrib.MAlpha)

    # -- derived colours ---------------------------------------------------
    def _fill(self) -> Vec4:
        return _vec(BTN_DISABLED_FILL) if not self.enabled else self.normal_color

    def _text_color(self):
        return WHITE if self.enabled else BTN_DISABLED_TEXT

    def _ring_color(self):
        return BTN_LINE if self.enabled else LINE

    # -- interaction -------------------------------------------------------
    def _clicked(self):
        """DirectButton command: flash the clicked colour, then run the user command."""
        if not self.enabled:
            return
        self._flash = self.click_hold
        self.node["frameColor"] = self.clicked_color
        if self.command:
            self.command()

    def render(self, dt):
        if self._flash > 0.0:
            self._flash -= dt
            if self._flash <= 0.0:
                self.node["frameColor"] = self._fill()  # flash over -> back to normal

    # -- live editing ------------------------------------------------------
    def configure(self, *, text=None, pos=None, size=None, command=_UNSET, enabled=None,
                  normal_color=_UNSET, clicked_color=_UNSET, click_hold=None, text_scale=None):
        if text is not None:
            self.node["text"] = text
        if text_scale is not None:
            self.node["text_scale"] = text_scale
        if pos is not None:
            self.node.setPos(*pos)
        if size is not None and tuple(size) != tuple(self.size):
            self.size = size
            w, h = size
            self.node["frameSize"] = self.ring["frameSize"] = (-w / 2, w / 2, -h / 2, h / 2)
        if command is not _UNSET:
            self.command = command
        if enabled is not None:
            self.enabled = enabled
            self.node["text_fg"] = self._text_color()
            self.ring["frameColor"] = self._ring_color()
        if normal_color is not _UNSET and normal_color is not None:
            self.normal_color = _vec(normal_color)
            if self._auto_clicked:
                self.clicked_color = _brighten(self.normal_color)
        if clicked_color is not _UNSET:
            self._auto_clicked = clicked_color is None
            self.clicked_color = _brighten(self.normal_color) if self._auto_clicked else _vec(clicked_color)
        if click_hold is not None:
            self.click_hold = click_hold
        if self._flash <= 0.0:  # not mid-flash -> reflect any colour/enabled change now
            self.node["frameColor"] = self._fill()

    def destroy(self):
        self.node.destroy()  # ring is a child, freed with it
