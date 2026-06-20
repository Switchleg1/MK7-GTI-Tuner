from __future__ import annotations

from direct.gui.DirectGui import DirectLabel
from panda3d.core import TextNode

from library.core.constants import TEXT
from library.core.ui.base_object import _UNSET, BaseObject


class Text(BaseObject):
    """A managed label (DirectLabel). Built once by a UIObjectController, then changed
    over the task's life via ``text()`` / ``color()`` / ``is_visible()`` / ``enabled()``
    (no arg = read, one arg = set) -- it is NOT destroyed and recreated each redraw.
    ``enabled(False)`` dims it to ``disabled_color`` if one was given."""

    def __init__(self, parent, font, *, text, pos, scale=0.045, color=TEXT, align=TextNode.ALeft,
                 wordwrap=None, is_visible=True, enabled=True, disabled_color=None):
        super().__init__(is_visible=is_visible, enabled=enabled)
        self.normal_color = color
        self.disabled_color = disabled_color
        self.node = DirectLabel(parent=parent, text=text, pos=pos, scale=scale, text_fg=self._color(),
                                text_align=align, text_wordwrap=wordwrap, text_font=font,
                                frameColor=(0, 0, 0, 0), relief=None)
        self._post_init()

    def _color(self):
        if not self._enabled and self.disabled_color is not None:
            return self.disabled_color
        return self.normal_color

    def _refresh(self):
        if self.node is not None:
            self.node["text_fg"] = self._color()

    # -- getter / setters --------------------------------------------------
    def text(self, value=_UNSET):
        if value is _UNSET:
            return self.node["text"]
        self.node["text"] = value

    def color(self, value=_UNSET):
        if value is _UNSET:
            return self.normal_color
        self.normal_color = value
        self._refresh()

    def scale(self, value=_UNSET):
        if value is _UNSET:
            return self.node["scale"]
        self.node["scale"] = value
