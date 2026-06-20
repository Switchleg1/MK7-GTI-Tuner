from __future__ import annotations

from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectGui import DirectSlider
from panda3d.core import TransparencyAttrib

from library.core import assets
from library.core.constants import PANEL_DARK
from library.core.ui.base_object import _UNSET, BaseObject


class Slider(BaseObject):
    """A managed horizontal slider (round knob on a rounded translucent track; derives
    BaseObject). Built once; wire/replace its callback with ``command_fn()`` (set it
    after building so it doesn't fire on init) and read the live value with ``value()``
    (``node['value']``)."""

    def __init__(self, parent, *, pos, value_range, value, width=0.5, command=None,
                 is_visible=True, enabled=True):
        super().__init__(is_visible=is_visible, enabled=enabled)
        box = assets.image_path("ui_box")
        self.node = DirectSlider(
            parent=parent, pos=pos, scale=1, range=value_range, value=value, command=command,
            frameColor=PANEL_DARK, frameSize=(-width / 2, width / 2, -0.016, 0.016), relief=DGG.FLAT, frameTexture=box,
            thumb_frameColor=(1, 1, 1, 1), thumb_frameSize=(-0.032, 0.032, -0.032, 0.032),
            thumb_relief=DGG.FLAT, thumb_frameTexture=assets.image_path("knob"),
        )
        self.node.setTransparency(TransparencyAttrib.MAlpha)
        self.node.thumb.setTransparency(TransparencyAttrib.MAlpha)
        self._post_init()

    # -- getter / setters --------------------------------------------------
    def value(self, value=_UNSET):
        if value is _UNSET:
            return self.node["value"]
        self.node["value"] = value

    def command_fn(self, fn=_UNSET):
        if fn is _UNSET:
            return self.node["command"]
        self.node["command"] = fn
