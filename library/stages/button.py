from __future__ import annotations

from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectGui import DirectButton, DirectFrame
from panda3d.core import TextNode, TransparencyAttrib, Vec4

from library.core import assets
from library.core.constants import (
    BTN_DISABLED_FILL, BTN_DISABLED_TEXT, BTN_LINE, BUTTON_CLICK_BRIGHTEN, BUTTON_CLICK_HOLD,
    GREEN_2, LINE, WHITE,
)

_UNSET = object()  # "argument not supplied" sentinel (so None can be a real value)


def _vec(color) -> Vec4:
    return color if isinstance(color, Vec4) else Vec4(*color)


def _brighten(color: Vec4, factor: float = BUTTON_CLICK_BRIGHTEN) -> Vec4:
    return Vec4(min(1.0, color.x * factor), min(1.0, color.y * factor), min(1.0, color.z * factor), color.w)


class Button:
    """One managed task button: a translucent rounded DirectButton (ui_box fill +
    ui_ring border, the project's glass style) that flashes a "clicked" colour for a
    short hold when pressed, then reverts.

    Built once (by a ButtonController, on task create) and then tweaked over the task's
    life via the getter/setter methods -- ``text()``, ``color()``, ``enabled()``,
    ``is_visible()``, ``command()`` (each returns the current value when called with no
    argument, sets it when given one). ``is_visible`` defaults True; a button set
    not-visible is hidden on ``render`` (and can't be clicked). ``render(dt)`` enforces
    visibility and advances the click flash. Never destroyed by a redraw, so a click
    can't be dropped by the UI rebuilding mid-press."""

    def __init__(self, parent, font, *, text, pos, size, command, enabled=True, is_visible=True,
                 normal_color=None, clicked_color=None, click_hold=None, text_scale=0.044):
        self.font = font
        self.command = command
        self._enabled = enabled
        self._visible = is_visible
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
        if not self._visible:
            self.node.stash()

    # -- derived colours ---------------------------------------------------
    def _fill(self) -> Vec4:
        return _vec(BTN_DISABLED_FILL) if not self._enabled else self.normal_color

    def _text_color(self):
        return WHITE if self._enabled else BTN_DISABLED_TEXT

    def _ring_color(self):
        return BTN_LINE if self._enabled else LINE

    def _refresh_fill(self):
        if self._flash <= 0.0:  # don't stomp an in-progress click flash
            self.node["frameColor"] = self._fill()

    # -- interaction -------------------------------------------------------
    def _clicked(self):
        """DirectButton command: flash the clicked colour, then run the user command."""
        if not self._enabled or not self._visible:
            return
        self._flash = self.click_hold
        self.node["frameColor"] = self.clicked_color
        if self.command:
            self.command()

    def render(self, dt):
        # Visibility: hidden buttons are stashed (off-screen AND unclickable).
        stashed = self.node.isStashed()
        if self._visible and stashed:
            self.node.unstash()
        elif not self._visible and not stashed:
            self.node.stash()
        # Click flash: revert to the normal/disabled fill once the hold elapses.
        if self._flash > 0.0:
            self._flash -= dt
            if self._flash <= 0.0:
                self.node["frameColor"] = self._fill()

    # -- getter / setter properties (set at any time after build) ----------
    def text(self, value=_UNSET):
        if value is _UNSET:
            return self.node["text"]
        self.node["text"] = value

    def color(self, value=_UNSET):
        if value is _UNSET:
            return self.normal_color
        self.normal_color = _vec(value)
        if self._auto_clicked:
            self.clicked_color = _brighten(self.normal_color)
        self._refresh_fill()

    def clicked_colour(self, value=_UNSET):
        if value is _UNSET:
            return self.clicked_color
        self._auto_clicked = value is None
        self.clicked_color = _brighten(self.normal_color) if self._auto_clicked else _vec(value)

    def enabled(self, value=_UNSET):
        if value is _UNSET:
            return self._enabled
        self._enabled = value
        self.node["text_fg"] = self._text_color()
        self.ring["frameColor"] = self._ring_color()
        self._refresh_fill()

    def is_visible(self, value=_UNSET):
        if value is _UNSET:
            return self._visible
        self._visible = value  # applied on the next render()

    def command_fn(self, value=_UNSET):
        if value is _UNSET:
            return self.command
        self.command = value

    def hold(self, value=_UNSET):
        if value is _UNSET:
            return self.click_hold
        self.click_hold = value

    def pos(self, value=_UNSET):
        if value is _UNSET:
            return self.node.getPos()
        self.node.setPos(*value)

    # -- bulk edit (used by the controller when (re)creating) --------------
    def configure(self, *, text=None, pos=None, size=None, command=_UNSET, enabled=None, is_visible=None,
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
            self.enabled(enabled)
        if is_visible is not None:
            self._visible = is_visible
        if normal_color is not _UNSET and normal_color is not None:
            self.color(normal_color)
        if clicked_color is not _UNSET:
            self.clicked_colour(clicked_color)
        if click_hold is not None:
            self.click_hold = click_hold
        self._refresh_fill()

    def destroy(self):
        self.node.destroy()  # ring is a child, freed with it
