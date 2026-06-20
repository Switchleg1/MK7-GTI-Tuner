from __future__ import annotations

_UNSET = object()  # "argument not supplied" sentinel (so None can be a real value)


class BaseObject:
    """Base for a managed UI object (Text, Button, ...): wraps a single DirectGui
    NodePath under a controller's layer, with common **visibility** and **enabled**
    state. Built once (by a UIObjectController), then tweaked over its life via
    getter/setter methods — `is_visible()` / `enabled()` / `pos()` (no arg = read, one
    arg = set). `render(dt)` enforces visibility by stash/unstash (a not-visible object
    is off-screen AND unclickable); subclasses extend `render` (e.g. a button's click
    flash) and `_refresh` (re-apply colours for the current enabled state). Never
    destroyed by a redraw."""

    def __init__(self, *, is_visible=True, enabled=True):
        self.node = None          # the subclass creates the NodePath
        self._visible = is_visible
        self._enabled = enabled

    def _post_init(self):
        """Call after the subclass has created ``self.node`` (applies initial state)."""
        if self.node is not None and not self._visible:
            self.node.stash()

    # -- per-frame ---------------------------------------------------------
    def render(self, dt):
        if self.node is None:
            return
        stashed = self.node.isStashed()
        if self._visible and stashed:
            self.node.unstash()
        elif not self._visible and not stashed:
            self.node.stash()

    # -- common getter / setters ------------------------------------------
    def is_visible(self, value=_UNSET):
        if value is _UNSET:
            return self._visible
        self._visible = value
        if self.node is None:
            return
        if value and self.node.isStashed():
            self.node.unstash()
        elif not value and not self.node.isStashed():
            self.node.stash()

    def enabled(self, value=_UNSET):
        if value is _UNSET:
            return self._enabled
        self._enabled = value
        self._refresh()

    def pos(self, value=_UNSET):
        if value is _UNSET:
            return self.node.getPos()
        self.node.setPos(*value)

    def _refresh(self):
        """Re-apply appearance for the current state. Subclass hook (no-op by default)."""

    def destroy(self):
        if self.node is not None:
            self.node.destroy()
            self.node = None
