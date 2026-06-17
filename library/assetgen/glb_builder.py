from __future__ import annotations

import math
import struct

from pygltflib import (
    ARRAY_BUFFER,
    ELEMENT_ARRAY_BUFFER,
    FLOAT,
    GLTF2,
    SCALAR,
    UNSIGNED_INT,
    VEC3,
    Accessor,
    Attributes,
    Buffer,
    BufferView,
    Material,
    Mesh,
    Node,
    PbrMetallicRoughness,
    Primitive,
    Scene,
)


def _box_geometry(hx: float, hy: float, hz: float, center: tuple[float, float, float]):
    """Return (positions, normals, indices) for an axis-aligned box.

    Geometry is centered on ``center`` so a part can pivot about its node origin
    (e.g. a limb whose joint sits at the origin while the mesh extends away).
    """
    cx, cy, cz = center
    faces = [
        ((1, 0, 0), [(hx, -hy, -hz), (hx, hy, -hz), (hx, hy, hz), (hx, -hy, hz)]),
        ((-1, 0, 0), [(-hx, hy, -hz), (-hx, -hy, -hz), (-hx, -hy, hz), (-hx, hy, hz)]),
        ((0, 1, 0), [(hx, hy, -hz), (-hx, hy, -hz), (-hx, hy, hz), (hx, hy, hz)]),
        ((0, -1, 0), [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, -hy, hz), (-hx, -hy, hz)]),
        ((0, 0, 1), [(-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]),
        ((0, 0, -1), [(-hx, hy, -hz), (hx, hy, -hz), (hx, -hy, -hz), (-hx, -hy, -hz)]),
    ]
    positions: list[tuple[float, float, float]] = []
    normals: list[tuple[float, float, float]] = []
    indices: list[int] = []
    for normal, corners in faces:
        base = len(positions)
        for x, y, z in corners:
            positions.append((x + cx, y + cy, z + cz))
            normals.append(normal)
        indices += [base, base + 1, base + 2, base, base + 2, base + 3]
    return positions, normals, indices


def _cylinder_geometry(radius: float, half_len: float, axis: int, segments: int, center):
    """Return (positions, normals, indices) for a capped cylinder along ``axis``."""
    cx, cy, cz = center
    b, c = [j for j in range(3) if j != axis]

    def pt(along, idx, ring_r):
        ang = 2 * math.pi * idx / segments
        v = [0.0, 0.0, 0.0]
        v[axis] = along
        v[b] = math.cos(ang) * ring_r
        v[c] = math.sin(ang) * ring_r
        return (v[0] + cx, v[1] + cy, v[2] + cz)

    def radial(idx):
        ang = 2 * math.pi * idx / segments
        n = [0.0, 0.0, 0.0]
        n[b], n[c] = math.cos(ang), math.sin(ang)
        return tuple(n)

    positions: list = []
    normals: list = []
    indices: list = []
    for i in range(segments):
        j = (i + 1) % segments
        base = len(positions)
        positions += [pt(half_len, i, radius), pt(half_len, j, radius), pt(-half_len, j, radius), pt(-half_len, i, radius)]
        normals += [radial(i), radial(j), radial(j), radial(i)]
        indices += [base, base + 1, base + 2, base, base + 2, base + 3]
    for sign, along in ((1, half_len), (-1, -half_len)):
        cap_n = [0.0, 0.0, 0.0]
        cap_n[axis] = sign
        hub = len(positions)
        positions.append(pt(along, 0, 0.0))
        normals.append(tuple(cap_n))
        ring = len(positions)
        for i in range(segments):
            positions.append(pt(along, i, radius))
            normals.append(tuple(cap_n))
        for i in range(segments):
            j = (i + 1) % segments
            indices += ([hub, ring + i, ring + j] if sign > 0 else [hub, ring + j, ring + i])
    return positions, normals, indices


def _hpr_to_quat(hpr):
    """Convert Panda HPR (degrees) to a glTF [x, y, z, w] quaternion.

    Valid because models are loaded with skip_axis_conversion=True, so glTF
    space equals Panda space.
    """
    from panda3d.core import LQuaternion

    quat = LQuaternion()
    quat.setHpr(tuple(hpr))
    return [quat.getI(), quat.getJ(), quat.getK(), quat.getR()]


class GlbScene:
    """Minimal procedural glTF builder.

    Authoring convention is Panda3D-native (Z up, +Y into the scene, +X right);
    load the result with ``skip_axis_conversion=True`` so values pass straight
    through. Geometry is flat-shaded boxes grouped into a named node hierarchy.
    """

    def __init__(self):
        self.gltf = GLTF2(scene=0, scenes=[Scene(nodes=[])])
        self.gltf.materials = []
        self.gltf.meshes = []
        self.gltf.accessors = []
        self.gltf.bufferViews = []
        self.gltf.nodes = []
        self._blob = bytearray()
        self._material_cache: dict[tuple, int] = {}

    # -- low level ---------------------------------------------------------
    def _add_buffer_view(self, data: bytes, target: int) -> int:
        offset = len(self._blob)
        self._blob += data
        while len(self._blob) % 4:  # keep 4-byte alignment
            self._blob += b"\x00"
        self.gltf.bufferViews.append(BufferView(buffer=0, byteOffset=offset, byteLength=len(data), target=target))
        return len(self.gltf.bufferViews) - 1

    def _add_accessor(self, view: int, comp_type: int, count: int, acc_type: str, mins=None, maxs=None) -> int:
        self.gltf.accessors.append(Accessor(bufferView=view, componentType=comp_type, count=count, type=acc_type, min=mins, max=maxs))
        return len(self.gltf.accessors) - 1

    def add_material(self, color: tuple[float, float, float, float], metallic: float = 0.0, roughness: float = 0.85, emissive: float = 0.0) -> int:
        key = (round(color[0], 3), round(color[1], 3), round(color[2], 3), round(color[3], 3), metallic, roughness, emissive)
        if key in self._material_cache:
            return self._material_cache[key]
        material = Material(
            pbrMetallicRoughness=PbrMetallicRoughness(baseColorFactor=list(color), metallicFactor=metallic, roughnessFactor=roughness),
            emissiveFactor=[color[0] * emissive, color[1] * emissive, color[2] * emissive],
            doubleSided=True,
        )
        self.gltf.materials.append(material)
        index = len(self.gltf.materials) - 1
        self._material_cache[key] = index
        return index

    def _add_mesh(self, positions, normals, indices, material: int) -> int:
        pos_bytes = b"".join(struct.pack("<3f", *p) for p in positions)
        nrm_bytes = b"".join(struct.pack("<3f", *n) for n in normals)
        idx_bytes = b"".join(struct.pack("<I", i) for i in indices)
        pos_view = self._add_buffer_view(pos_bytes, ARRAY_BUFFER)
        nrm_view = self._add_buffer_view(nrm_bytes, ARRAY_BUFFER)
        idx_view = self._add_buffer_view(idx_bytes, ELEMENT_ARRAY_BUFFER)
        mins = [min(p[i] for p in positions) for i in range(3)]
        maxs = [max(p[i] for p in positions) for i in range(3)]
        pos_acc = self._add_accessor(pos_view, FLOAT, len(positions), VEC3, mins, maxs)
        nrm_acc = self._add_accessor(nrm_view, FLOAT, len(normals), VEC3)
        idx_acc = self._add_accessor(idx_view, UNSIGNED_INT, len(indices), SCALAR)
        primitive = Primitive(attributes=Attributes(POSITION=pos_acc, NORMAL=nrm_acc), indices=idx_acc, material=material)
        self.gltf.meshes.append(Mesh(primitives=[primitive]))
        return len(self.gltf.meshes) - 1

    def _add_node(self, name: str, translation, mesh: int | None, parent: int | None, rotation_hpr=None) -> int:
        node = Node(name=name, translation=list(translation) if translation else None, mesh=mesh)
        if rotation_hpr:
            node.rotation = _hpr_to_quat(rotation_hpr)
        self.gltf.nodes.append(node)
        index = len(self.gltf.nodes) - 1
        if parent is None:
            self.gltf.scenes[0].nodes.append(index)
        else:
            children = self.gltf.nodes[parent].children or []
            children.append(index)
            self.gltf.nodes[parent].children = children
        return index

    # -- high level --------------------------------------------------------
    def group(self, name: str, translation=(0, 0, 0), parent: int | None = None, rotation_hpr=None) -> int:
        """An empty pivot node used to build and pose a hierarchy."""
        return self._add_node(name, translation, None, parent, rotation_hpr)

    def box(self, name, size, color, translation=(0, 0, 0), center=(0, 0, 0), parent=None, rotation_hpr=None, **material_kwargs) -> int:
        sx, sy, sz = size
        positions, normals, indices = _box_geometry(sx / 2, sy / 2, sz / 2, center)
        mesh = self._add_mesh(positions, normals, indices, self.add_material(color, **material_kwargs))
        return self._add_node(name, translation, mesh, parent, rotation_hpr)

    def cylinder(self, name, radius, length, axis=2, color=(0.5, 0.5, 0.5, 1), translation=(0, 0, 0), center=(0, 0, 0), parent=None, segments=18, rotation_hpr=None, **material_kwargs) -> int:
        positions, normals, indices = _cylinder_geometry(radius, length / 2, axis, segments, center)
        mesh = self._add_mesh(positions, normals, indices, self.add_material(color, **material_kwargs))
        return self._add_node(name, translation, mesh, parent, rotation_hpr)

    def write_glb(self, path: str):
        self.gltf.buffers = [Buffer(byteLength=len(self._blob))]
        self.gltf.set_binary_blob(bytes(self._blob))
        self.gltf.save_binary(path)
