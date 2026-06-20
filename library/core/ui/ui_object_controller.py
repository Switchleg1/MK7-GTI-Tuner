from __future__ import annotations

from panda3d.core import TextNode

from library.core.constants import BOX_LINE, PANEL, TEXT
from library.core.ui.button import Button
from library.core.ui.entry import Entry
from library.core.ui.frame import Frame
from library.core.ui.image import Image
from library.core.ui.slider import Slider
from library.core.ui.text import Text


class UIObjectController:
    """Owns a set of managed UI objects (Text / Button / Frame / Image / Slider / Entry)
    for one task or screen -- every ``Hud`` primitive has a BaseObject-derived equivalent
    here. Objects are added via ``add_text`` / ``add_button`` / ``add_frame`` /
    ``add_image`` / ``add_slider`` / ``add_entry`` and then changed in place
    (``get(key).text(...)`` / ``.is_visible(...)`` / ``.color(...)`` / ``.enabled(...)``).
    Persistent screens build them once on enter and only tweak them; event-driven screens
    (panels, the hub) instead ``clear()`` and re-add on each ``draw()``. The controller is
    created when the screen starts and ``destroy()``-ed when it ends.

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

    def add_frame(self, key, *, frame_size, pos=(0, 0, 0), color=PANEL, border=BOX_LINE,
                  texture="ui_box", state=None, is_visible=True, enabled=True) -> Frame:
        """A glass/plain rectangle. ``texture=None`` -> a plain flat frame; ``state``
        (DGG.NORMAL) makes it catch mouse clicks (the modal shade)."""
        self.remove(key)
        self.objects[key] = Frame(self.parent, frame_size=frame_size, pos=pos, color=color,
                                  border=border, texture=texture, state=state,
                                  is_visible=is_visible, enabled=enabled)
        return self.objects[key]

    def add_image(self, key, image, pos, scale, *, color_scale=None, is_visible=True, enabled=True) -> Image:
        self.remove(key)
        self.objects[key] = Image(self.parent, key=image, pos=pos, scale=scale,
                                  color_scale=color_scale, is_visible=is_visible, enabled=enabled)
        return self.objects[key]

    def add_slider(self, key, pos, value_range, value, width=0.5, command=None,
                   *, is_visible=True, enabled=True) -> Slider:
        self.remove(key)
        self.objects[key] = Slider(self.parent, pos=pos, value_range=value_range, value=value,
                                   width=width, command=command, is_visible=is_visible, enabled=enabled)
        return self.objects[key]

    def add_entry(self, key, command, pos, *, width=42, scale=0.038, color=TEXT, initial="",
                  focus=True, is_visible=True, enabled=True) -> Entry:
        self.remove(key)
        self.objects[key] = Entry(self.parent, self.font, command=command, pos=pos, width=width,
                                  scale=scale, color=color, initial=initial, focus=focus,
                                  is_visible=is_visible, enabled=enabled)
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
