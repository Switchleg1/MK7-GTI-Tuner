from __future__ import annotations

from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectGui import DirectButton, DirectFrame
from direct.gui.OnscreenImage import OnscreenImage
from panda3d.core import TextNode, TransparencyAttrib, Vec4

from library.core import assets
from library.core.constants import (
    BTN_DISABLED_FILL, BTN_DISABLED_TEXT, BTN_LINE, BUTTON_CLICK_BRIGHTEN, BUTTON_CLICK_HOLD,
    BUTTON_FLASH_SCALE, BUTTON_STYLES, GREEN_2, LINE, WHITE,
)
from library.core.utils import rgba
from library.core.ui.base_object import _UNSET, BaseObject

_FLASH_SCALE = Vec4(BUTTON_FLASH_SCALE, BUTTON_FLASH_SCALE, BUTTON_FLASH_SCALE, 1.0)
_ACCENT_H = 0.015  # height of the garage-style top accent strip


def _vec(color) -> Vec4:
    if isinstance(color, str):
        return rgba(color)
    return color if isinstance(color, Vec4) else Vec4(*color)


def _brighten(color: Vec4, factor: float = BUTTON_CLICK_BRIGHTEN) -> Vec4:
    return Vec4(min(1.0, color.x * factor), min(1.0, color.y * factor), min(1.0, color.z * factor), color.w)


class Button(BaseObject):
    """A managed button (derives BaseObject) in three **styles** (`constants.BUTTON_STYLES`):
    **box** (rounded glass: ui_box fill tinted by the colour + ui_ring border, white
    text, click flashes the *clicked colour*), **pill** (textured simon_button, the
    colour tints the *text*, optional left ``icon``, click flashes by colour-scale
    brighten), and **garage** (box + a green top accent strip).

    Built once, then tweaked via ``text()`` / ``color()`` / ``enabled()`` /
    ``is_visible()`` / ``command_fn()`` (the last two + ``pos()`` come from BaseObject).
    ``render(dt)`` enforces visibility (BaseObject) and advances the click flash."""

    def __init__(self, parent, font, *, text, pos, size, command, enabled=True, is_visible=True,
                 normal_color=None, clicked_color=None, click_hold=None, text_scale=0.044,
                 style="box", icon=None):
        super().__init__(is_visible=is_visible, enabled=enabled)
        self.font = font
        self.command = command
        self.style = BUTTON_STYLES.get(style, BUTTON_STYLES["box"])
        self.click_hold = BUTTON_CLICK_HOLD if click_hold is None else click_hold
        self.size = size
        self._flash = 0.0
        self.normal_color = _vec(normal_color) if normal_color is not None else _vec(GREEN_2)
        self._auto_clicked = clicked_color is None
        self.clicked_color = _brighten(self.normal_color) if self._auto_clicked else _vec(clicked_color)

        w, h = size
        fs = (-w / 2, w / 2, -h / 2, h / 2)
        extra = {}
        if icon or self.style["text_dy"]:  # only nudge text for pills / icons
            extra["text_pos"] = (0.06 if icon else 0.0, self.style["text_dy"])
        self.node = DirectButton(
            parent=parent, text=text, command=self._clicked, pos=pos, scale=1, text_scale=text_scale,
            text_fg=self._text_color(), text_align=TextNode.ACenter, text_font=font,
            frameSize=fs, frameColor=self._fill(), relief=DGG.FLAT,
            frameTexture=assets.image_path(self.style["texture"]), pressEffect=0, **extra)
        self.node.setTransparency(TransparencyAttrib.MAlpha)
        self.ring = None
        if self.style["ring"]:
            self.ring = DirectFrame(parent=self.node, frameSize=fs, frameColor=self._ring_color(),
                                    relief=DGG.FLAT, frameTexture=assets.image_path(self.style["ring"]))
            self.ring.setTransparency(TransparencyAttrib.MAlpha)
        self.icon = None
        if icon:
            self.icon = OnscreenImage(parent=self.node, image=assets.image_path(icon),
                                      pos=(-w / 2 + 0.09, 0, 0), scale=0.058)
            self.icon.setTransparency(TransparencyAttrib.MAlpha)
        self.accent = None
        if self.style.get("accent"):  # garage style: a coloured strip across the top
            self.accent = DirectFrame(parent=self.node, frameSize=(-w / 2, w / 2, h / 2 - _ACCENT_H, h / 2),
                                      frameColor=_vec(self.style["accent"]), relief=DGG.FLAT,
                                      frameTexture=assets.image_path("ui_box"))
            self.accent.setTransparency(TransparencyAttrib.MAlpha)
        self._post_init()

    # -- derived colours (style-aware) -------------------------------------
    def _fill(self) -> Vec4:
        if self.style["tint"] == "fill":  # box/garage: the colour IS the fill
            return _vec(BTN_DISABLED_FILL) if not self._enabled else self.normal_color
        return _vec(WHITE)                # pill: the texture supplies the look

    def _text_color(self):
        if self.style["tint"] == "text":  # pill: the colour tints the text
            return self.normal_color if self._enabled else BTN_DISABLED_TEXT
        return WHITE if self._enabled else BTN_DISABLED_TEXT

    def _ring_color(self):
        return BTN_LINE if self._enabled else LINE

    def _refresh(self):
        """Re-apply text/ring (always) and fill (unless a fill-flash is in progress)."""
        if self.node is None:
            return
        self.node["text_fg"] = self._text_color()
        if self.ring is not None:
            self.ring["frameColor"] = self._ring_color()
        if not (self.style["flash"] == "fill" and self._flash > 0.0):
            self.node["frameColor"] = self._fill()

    # -- interaction -------------------------------------------------------
    def _clicked(self):
        if not self._enabled or not self._visible:
            return
        self._flash = self.click_hold
        if self.style["flash"] == "fill":
            self.node["frameColor"] = self.clicked_color
        else:  # scale: brighten the whole (textured) pill
            self.node.setColorScale(_FLASH_SCALE)
        if self.command:
            self.command()

    def render(self, dt):
        super().render(dt)  # visibility (BaseObject)
        if self._flash > 0.0:
            self._flash -= dt
            if self._flash <= 0.0:
                if self.style["flash"] == "fill":
                    self.node["frameColor"] = self._fill()
                else:
                    self.node.clearColorScale()

    # -- getter / setters (visibility/enabled/pos are on BaseObject) -------
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
        self._refresh()

    def clicked_colour(self, value=_UNSET):
        if value is _UNSET:
            return self.clicked_color
        self._auto_clicked = value is None
        self.clicked_color = _brighten(self.normal_color) if self._auto_clicked else _vec(value)

    def command_fn(self, value=_UNSET):
        if value is _UNSET:
            return self.command
        self.command = value

    def hold(self, value=_UNSET):
        if value is _UNSET:
            return self.click_hold
        self.click_hold = value

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
            fs = (-w / 2, w / 2, -h / 2, h / 2)
            self.node["frameSize"] = fs
            if self.ring is not None:
                self.ring["frameSize"] = fs
            if self.icon is not None:
                self.icon.setPos(-w / 2 + 0.09, 0, 0)
            if self.accent is not None:
                self.accent["frameSize"] = (-w / 2, w / 2, h / 2 - _ACCENT_H, h / 2)
        if command is not _UNSET:
            self.command = command
        if enabled is not None:
            self._enabled = enabled
        if is_visible is not None:
            self._visible = is_visible
        if normal_color is not _UNSET and normal_color is not None:
            self.normal_color = _vec(normal_color)
            if self._auto_clicked:
                self.clicked_color = _brighten(self.normal_color)
        if clicked_color is not _UNSET:
            self.clicked_colour(clicked_color)
        if click_hold is not None:
            self.click_hold = click_hold
        self._refresh()
