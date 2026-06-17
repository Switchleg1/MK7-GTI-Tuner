from __future__ import annotations

import os

from library.core.constants import MODEL_FILES
from library.assetgen.glb_builder import GlbScene


def build(out_dir: str) -> str:
    """A dark shop floor with a lighter service pad under the car."""
    scene = GlbScene()
    ground = scene.group("ground")
    scene.box("floor", (28, 28, 0.2), (0.08, 0.10, 0.12, 1), translation=(0, 0, -0.1), parent=ground, roughness=0.97)
    scene.box("pad", (8.5, 11, 0.06), (0.12, 0.14, 0.17, 1), translation=(-0.8, 0, 0.0), parent=ground, roughness=0.9)
    scene.box("pad_line_l", (0.08, 11, 0.07), (0.55, 0.5, 0.18, 1), translation=(-5.0, 0, 0.01), parent=ground, emissive=0.2)
    scene.box("pad_line_r", (0.08, 11, 0.07), (0.55, 0.5, 0.18, 1), translation=(3.4, 0, 0.01), parent=ground, emissive=0.2)
    path = os.path.join(out_dir, MODEL_FILES["ground"])
    scene.write_glb(path)
    return path
