from __future__ import annotations

from direct.showbase.DirectObject import DirectObject
from panda3d.core import BitMask32, CollisionHandlerQueue, CollisionNode, CollisionRay, CollisionTraverser, GeomNode


class Picker(DirectObject):
    """Click-to-pick for tagged 3D nodes via a camera ray.

    Register a NodePath with a tag + callback; a left click fires the callback of
    the nearest tagged node under the cursor (untagged geometry is skipped).
    """

    def __init__(self, base):
        super().__init__()
        self.base = base
        self.traverser = CollisionTraverser("picker")
        self.queue = CollisionHandlerQueue()
        self.ray = CollisionRay()
        node = CollisionNode("picker-ray")
        node.addSolid(self.ray)
        node.setFromCollideMask(GeomNode.getDefaultCollideMask())
        node.setIntoCollideMask(BitMask32.allOff())
        self.ray_np = self.base.camera.attachNewNode(node)
        self.traverser.addCollider(self.ray_np, self.queue)
        self.handlers: dict[str, callable] = {}
        self.enabled = True
        self.accept("mouse1", self._on_click)

    def register(self, np, tag: str, callback):
        np.setTag("pick", tag)
        self.handlers[tag] = callback

    def clear(self):
        self.handlers.clear()

    def set_enabled(self, flag: bool):
        self.enabled = flag

    def _on_click(self):
        if not self.enabled or self.base.mouseWatcherNode is None or not self.base.mouseWatcherNode.hasMouse():
            return
        mouse = self.base.mouseWatcherNode.getMouse()
        self.ray.setFromLens(self.base.camNode, mouse.getX(), mouse.getY())
        self.traverser.traverse(self.base.render)
        self.queue.sortEntries()
        for i in range(self.queue.getNumEntries()):
            tagged = self.queue.getEntry(i).getIntoNodePath().findNetTag("pick")
            if not tagged.isEmpty():
                handler = self.handlers.get(tagged.getTag("pick"))
                if handler:
                    handler()
                    return

    def destroy(self):
        self.ignoreAll()
        if not self.ray_np.isEmpty():
            self.ray_np.removeNode()
        self.handlers.clear()
