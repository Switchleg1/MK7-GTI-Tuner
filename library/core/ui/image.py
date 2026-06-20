from __future__ import annotations

from direct.gui.OnscreenImage import OnscreenImage
from panda3d.core import TransparencyAttrib

from library.core import assets
from library.core.ui.base_object import _UNSET, BaseObject


class Image(BaseObject):
    """A managed image (OnscreenImage) keyed by an asset name (derives BaseObject).
    Built once by a UIObjectController; change it via ``color_scale()`` / ``scale()``
    (and the BaseObject setters ``is_visible()`` / ``pos()``)."""

    def __init__(self, parent, *, key, pos, scale, color_scale=None, is_visible=True, enabled=True):
        super().__init__(is_visible=is_visible, enabled=enabled)
        self.node = OnscreenImage(parent=parent, image=assets.image_path(key), pos=pos, scale=scale)
        self.node.setTransparency(TransparencyAttrib.MAlpha)
        if color_scale is not None:
            self.node.setColorScale(color_scale)
        self._post_init()

    # -- getter / setters --------------------------------------------------
    def color_scale(self, value=_UNSET):
        if value is _UNSET:
            return self.node.getColorScale()
        self.node.setColorScale(value)

    def scale(self, value=_UNSET):
        if value is _UNSET:
            return self.node.getScale()
        self.node.setScale(value)
