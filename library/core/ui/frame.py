from __future__ import annotations

from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectGui import DirectFrame
from panda3d.core import TransparencyAttrib

from library.core import assets
from library.core.constants import BOX_LINE, PANEL
from library.core.ui.base_object import _UNSET, BaseObject


class Frame(BaseObject):
    """A managed rectangle (derives BaseObject). By default a translucent rounded
    ``ui_box`` tinted by ``color`` with an optional ``ui_ring`` border child (the
    glass-panel look). Pass ``texture=None`` for a plain flat frame (e.g. the Discord
    modal shade) and ``state=DGG.NORMAL`` to make it catch mouse clicks. Built once by
    a UIObjectController, then changed via ``color()`` / ``frame_size()`` (and the
    BaseObject setters ``is_visible()`` / ``pos()``)."""

    def __init__(self, parent, *, frame_size, pos=(0, 0, 0), color=PANEL, border=BOX_LINE,
                 texture="ui_box", state=None, is_visible=True, enabled=True):
        super().__init__(is_visible=is_visible, enabled=enabled)
        kwargs = dict(parent=parent, frameSize=frame_size, frameColor=color, relief=DGG.FLAT)
        if texture is not None:
            kwargs["frameTexture"] = assets.image_path(texture)
        if state is not None:
            kwargs["state"] = state
        self.node = DirectFrame(**kwargs)
        self.node.setTransparency(TransparencyAttrib.MAlpha)
        self.node.setPos(*pos)
        self.ring = None
        if border:
            self.ring = DirectFrame(parent=self.node, frameSize=frame_size, frameColor=border,
                                    relief=DGG.FLAT, frameTexture=assets.image_path("ui_ring"))
            self.ring.setTransparency(TransparencyAttrib.MAlpha)
        self._post_init()

    # -- getter / setters --------------------------------------------------
    def color(self, value=_UNSET):
        if value is _UNSET:
            return self.node["frameColor"]
        self.node["frameColor"] = value

    def frame_size(self, value=_UNSET):
        if value is _UNSET:
            return self.node["frameSize"]
        self.node["frameSize"] = value
        if self.ring is not None:
            self.ring["frameSize"] = value
