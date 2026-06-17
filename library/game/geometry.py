from __future__ import annotations

from panda3d.core import Geom, GeomNode, GeomTriangles, GeomVertexData, GeomVertexFormat, GeomVertexWriter, LineSegs, NodePath, Vec4


def make_box(name: str, sx: float, sy: float, sz: float, color: Vec4) -> NodePath:
    fmt = GeomVertexFormat.getV3c4()
    vdata = GeomVertexData(name, fmt, Geom.UHStatic)
    vertex = GeomVertexWriter(vdata, "vertex")
    col = GeomVertexWriter(vdata, "color")
    x, y, z = sx / 2, sy / 2, sz / 2
    pts = [(-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z), (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]
    for point in pts:
        vertex.addData3(*point)
        col.addData4(color)
    tris = GeomTriangles(Geom.UHStatic)
    for a, b, c, d in [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]:
        tris.addVertices(a, b, c)
        tris.addVertices(a, c, d)
    geom = Geom(vdata)
    geom.addPrimitive(tris)
    node = GeomNode(name)
    node.addGeom(geom)
    return NodePath(node)


def make_grid(parent: NodePath):
    lines = LineSegs()
    lines.setThickness(1)
    lines.setColor(0.13, 0.22, 0.28, 1)
    for x in range(-16, 17, 2):
        lines.moveTo(x, -12, 0.02)
        lines.drawTo(x, 30, 0.02)
    for y in range(-12, 31, 2):
        lines.moveTo(-16, y, 0.02)
        lines.drawTo(16, y, 0.02)
    parent.attachNewNode(lines.create())


def build_car(parent: NodePath, color: Vec4):
    parent.getChildren().detach()
    for node, pos, h in [
        (make_box("body", 2.7, 4.5, 0.7, color), (0, 0, 0.35), 0),
        (make_box("roof", 1.55, 2.1, 0.62, Vec4(0.08, 0.12, 0.14, 1)), (0, -0.2, 0.98), 0),
        (make_box("front-lip", 2.85, 0.25, 0.22, Vec4(0.03, 0.035, 0.04, 1)), (0, -2.35, 0.22), 0),
    ]:
        node.reparentTo(parent)
        node.setPos(*pos)
        node.setH(h)
    for x in (-1.15, 1.15):
        for y in (-1.55, 1.55):
            wheel = make_box("wheel", 0.42, 0.26, 0.72, Vec4(0.02, 0.02, 0.025, 1))
            wheel.reparentTo(parent)
            wheel.setPos(x, y, 0.02)
            wheel.setH(90)
