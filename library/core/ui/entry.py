from __future__ import annotations

from direct.gui.DirectGui import DirectEntry
from panda3d.core import TransparencyAttrib

from library.core.constants import TEXT
from library.core.ui.base_object import _UNSET, BaseObject


class Entry(BaseObject):
    """A managed single-line text input (DirectEntry; derives BaseObject). ``command``
    fires with the typed text on Enter. Built once; read/clear the contents via
    ``text()`` and refocus the caret via ``focus()``."""

    def __init__(self, parent, font, *, command, pos, width=42, scale=0.038, color=TEXT,
                 initial="", focus=True, is_visible=True, enabled=True):
        super().__init__(is_visible=is_visible, enabled=enabled)
        self.node = DirectEntry(
            parent=parent, command=command, initialText=initial, focus=1 if focus else 0,
            width=width, scale=scale, pos=pos, frameColor=(0, 0, 0, 0), text_fg=color,
            text_font=font, relief=None, numLines=1, overflow=1)
        self.node.setTransparency(TransparencyAttrib.MAlpha)
        self._post_init()

    # -- getter / setters --------------------------------------------------
    def text(self, value=_UNSET):
        if value is _UNSET:
            return self.node.get()
        self.node.enterText(value)

    def focus(self):
        self.node["focus"] = 1
        self.node.setFocus()

    def command_fn(self, fn=_UNSET):
        if fn is _UNSET:
            return self.node["command"]
        self.node["command"] = fn
