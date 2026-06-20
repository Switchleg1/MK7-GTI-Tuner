from __future__ import annotations

from panda3d.core import TextNode

from library.core.constants import TEXT
from library.stages.button import Button
from library.stages.text import Text


class UIObjectController:
    """Owns a set of managed UI objects (Text + Button) for one task or screen. Objects
    are **built once** -- ``add_text(key, ...)`` / ``add_button(key, ...)`` at task start
    -- and then only changed in place (``get(key).text(...)`` / ``.is_visible(...)`` /
    ``.color(...)`` / ``.enabled(...)``), never destroyed and recreated each redraw. The
    controller is created when the task starts and ``destroy()``-ed when it ends.

    ``render(dt)`` ticks every object (visibility + any flash); ``lift()`` keeps them
    drawn above the frames/labels a surrounding redraw rebuilt."""

    def __init__(self, app, parent):
        self.app = app
        self.parent = parent  # the NodePath layer the objects live under
        self.font = getattr(app, "mono_font", None)
        self.objects: dict = {}

    # -- build -------------------------------------------------------------
    def add_text(self, key, text, pos, scale=0.045, color=TEXT, align=TextNode.ALeft, wordwrap=None,
                 *, is_visible=True, enabled=True, disabled_color=None) -> Text:
        self.remove(key)
        self.objects[key] = Text(self.parent, self.font, text=text, pos=pos, scale=scale, color=color,
                                 align=align, wordwrap=wordwrap, is_visible=is_visible, enabled=enabled,
                                 disabled_color=disabled_color)
        return self.objects[key]

    def add_button(self, key, text, pos, size, command, enabled=True, color=None, text_scale=0.044,
                   *, is_visible=True, clicked_color=None, click_hold=None, style="box", icon=None) -> Button:
        """``color`` tints the fill (box/garage) or the text (pill); ``style`` is
        ``"box"`` / ``"pill"`` / ``"garage"``."""
        self.remove(key)
        self.objects[key] = Button(
            self.parent, self.font, text=text, pos=pos, size=size, command=command, enabled=enabled,
            is_visible=is_visible, normal_color=color, clicked_color=clicked_color,
            click_hold=click_hold, text_scale=text_scale, style=style, icon=icon)
        return self.objects[key]

    # -- access / change ---------------------------------------------------
    def get(self, key):
        return self.objects.get(key)

    def remove(self, key):
        obj = self.objects.pop(key, None)
        if obj is not None:
            obj.destroy()

    # -- lifecycle ---------------------------------------------------------
    def render(self, dt):
        for obj in self.objects.values():
            obj.render(dt)

    def lift(self):
        """Re-add the object layer at the end of its parent so the objects draw (and
        pick) above the frames/labels a surrounding redraw just rebuilt."""
        parent = self.parent.getParent()
        if not parent.isEmpty():
            self.parent.reparentTo(parent)

    def clear(self):
        for obj in self.objects.values():
            obj.destroy()
        self.objects.clear()

    def destroy(self):
        self.clear()
        if not self.parent.isEmpty():
            self.parent.removeNode()
