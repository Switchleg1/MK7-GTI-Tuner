from __future__ import annotations

from library.core.constants import GREEN_2
from library.stages.button import _UNSET, Button


class ButtonController:
    """Owns a task's buttons (one controller per task -- created on enter, destroyed
    on exit). Buttons are keyed and **persist** between redraws: declaring the same key
    again edits the existing button instead of destroying/recreating it, so a click is
    never dropped by the UI rebuilding mid-press, and buttons can flash on click.

    Two ways to drive it:
      * Declarative (how tasks use it each redraw): ``begin()`` then a ``button(key, ...)``
        per button, then ``prune()`` to drop any key not re-declared this pass.
      * Imperative (any time): ``add``/``edit``/``remove``/``get``.

    ``render(dt)`` advances every button's click-flash. ``lift()`` keeps the buttons
    drawn above the frames/labels a redraw just rebuilt."""

    def __init__(self, app, parent):
        self.app = app
        self.parent = parent  # a NodePath layer the buttons live under
        self.font = getattr(app, "mono_font", None)
        self.buttons: dict = {}
        self._seen: set = set()

    # -- declarative redraw pass -------------------------------------------
    def begin(self):
        self._seen = set()

    def button(self, key, text, pos, size, command, enabled=True, color=None, text_scale=0.044,
               *, clicked_color=_UNSET, click_hold=None):
        """Create the button for ``key`` (or edit it if it already exists) and mark it
        seen for this pass. ``color`` is the normal (enabled) fill; ``None`` -> default."""
        self._seen.add(key)
        normal = color if color is not None else GREEN_2
        existing = self.buttons.get(key)
        if existing is None:
            self.buttons[key] = Button(
                self.parent, self.font, text=text, pos=pos, size=size, command=command, enabled=enabled,
                normal_color=normal, clicked_color=(None if clicked_color is _UNSET else clicked_color),
                click_hold=click_hold, text_scale=text_scale)
        else:
            existing.configure(text=text, pos=pos, size=size, command=command, enabled=enabled,
                               normal_color=normal, clicked_color=clicked_color, click_hold=click_hold,
                               text_scale=text_scale)
        return self.buttons[key]

    def prune(self):
        """Destroy every button not re-declared since the last ``begin()``."""
        for key in [k for k in self.buttons if k not in self._seen]:
            self.buttons.pop(key).destroy()

    # -- imperative --------------------------------------------------------
    def add(self, key, **kwargs) -> Button:
        self.remove(key)
        self.buttons[key] = Button(self.parent, self.font, **kwargs)
        self._seen.add(key)
        return self.buttons[key]

    def edit(self, key, **kwargs):
        button = self.buttons.get(key)
        if button is not None:
            button.configure(**kwargs)

    def get(self, key) -> Button | None:
        return self.buttons.get(key)

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
