from __future__ import annotations

from library.stages.button import Button


class ButtonController:
    """Owns a task's buttons (one controller per task: created on enter, destroyed on
    exit). Buttons are **built once** at task start via ``add(key, ...)`` and then only
    tweaked over the task's life -- ``get(key).text(...)`` / ``.color(...)`` /
    ``.is_visible(...)`` / ``.enabled(...)``, or ``edit(key, **props)`` -- rather than
    being recreated each redraw. Because they persist, a click can't be dropped by the
    UI rebuilding mid-press, and they can flash on click.

    ``render(dt)`` enforces every button's visibility and advances its click flash.
    ``lift()`` keeps the buttons drawn above the frames/labels a redraw just rebuilt."""

    def __init__(self, app, parent):
        self.app = app
        self.parent = parent  # the NodePath layer the buttons live under
        self.font = getattr(app, "mono_font", None)
        self.buttons: dict = {}

    # -- build / change ----------------------------------------------------
    def add(self, key, text, pos, size, command, enabled=True, color=None, text_scale=0.044,
            *, is_visible=True, clicked_color=None, click_hold=None) -> Button:
        """Create (or replace) the button for ``key``. ``color`` is the normal/enabled
        fill (None -> the default green)."""
        self.remove(key)
        self.buttons[key] = Button(
            self.parent, self.font, text=text, pos=pos, size=size, command=command, enabled=enabled,
            is_visible=is_visible, normal_color=color, clicked_color=clicked_color,
            click_hold=click_hold, text_scale=text_scale)
        return self.buttons[key]

    def get(self, key) -> Button | None:
        return self.buttons.get(key)

    def edit(self, key, **props):
        button = self.buttons.get(key)
        if button is not None:
            button.configure(**props)

    def remove(self, key):
        button = self.buttons.pop(key, None)
        if button is not None:
            button.destroy()

    # -- lifecycle ---------------------------------------------------------
    def render(self, dt):
        for button in self.buttons.values():
            button.render(dt)

    def lift(self):
        """Re-add the button layer at the end of its parent so buttons draw (and pick)
        above the frames/labels the surrounding redraw just rebuilt."""
        parent = self.parent.getParent()
        if not parent.isEmpty():
            self.parent.reparentTo(parent)

    def clear(self):
        for button in self.buttons.values():
            button.destroy()
        self.buttons.clear()

    def destroy(self):
        self.clear()
        if not self.parent.isEmpty():
            self.parent.removeNode()
