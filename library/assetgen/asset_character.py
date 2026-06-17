from __future__ import annotations

import os

from library.core.constants import MODEL_FILES
from library.assetgen.glb_builder import GlbScene

JEANS = (0.16, 0.20, 0.30, 1)
HOODIE = (0.20, 0.22, 0.27, 1)
HOODIE_2 = (0.26, 0.29, 0.35, 1)
SKIN = (0.82, 0.62, 0.48, 1)
HAIR = (0.06, 0.05, 0.05, 1)
SHOE = (0.05, 0.05, 0.06, 1)

# Arms and legs are built per side; +Y is the character's right, -Y the left.
SIDES = [("r", 1.0), ("l", -1.0)]


def build(out_dir: str) -> str:
    """A seated guy authored at his own origin (feet ~z=0), facing -X so he looks
    out the open driver door. Arms hang straight down at rest; the stage rotates
    the named shoulder/elbow/hand joints to plug in, raise the phone, and cheer."""
    scene = GlbScene()
    root = scene.group("character")

    pelvis = scene.group("pelvis", translation=(0, 0, 0.60), parent=root)
    scene.box("hips", (0.42, 0.34, 0.24), JEANS, parent=pelvis)

    torso = scene.group("torso", translation=(0, -0.02, 0.12), parent=pelvis)
    scene.box("torso", (0.46, 0.30, 0.50), HOODIE, center=(0, 0, 0.25), parent=torso)
    scene.box("zip", (0.06, 0.02, 0.44), HOODIE_2, center=(0, -0.15, 0.25), parent=torso)

    head = scene.group("head", translation=(0, 0, 0.52), parent=torso)
    scene.box("neck", (0.12, 0.12, 0.10), SKIN, center=(0, 0, 0.04), parent=head)
    scene.box("head", (0.25, 0.25, 0.27), SKIN, center=(0, 0, 0.22), parent=head)
    scene.box("hair", (0.27, 0.27, 0.12), HAIR, center=(0, 0.01, 0.40), parent=head)

    for tag, side in SIDES:
        shoulder = scene.group(f"{tag}Shoulder", translation=(0, side * 0.27, 0.44), parent=torso)
        scene.box(f"{tag}UpperArm", (0.13, 0.13, 0.36), HOODIE, center=(0, 0, -0.18), parent=shoulder)
        elbow = scene.group(f"{tag}Elbow", translation=(0, 0, -0.36), parent=shoulder)
        scene.box(f"{tag}Forearm", (0.11, 0.11, 0.30), SKIN, center=(0, 0, -0.15), parent=elbow)
        hand = scene.group(f"{tag}Hand", translation=(0, 0, -0.30), parent=elbow)
        scene.box(f"{tag}HandMesh", (0.12, 0.09, 0.12), SKIN, center=(0, 0, -0.05), parent=hand)

    for tag, side in SIDES:
        hip = scene.group(f"{tag}Hip", translation=(0.0, side * 0.13, -0.02), parent=pelvis)
        scene.box(f"{tag}Thigh", (0.46, 0.16, 0.16), JEANS, center=(-0.23, 0, 0), parent=hip)
        knee = scene.group(f"{tag}Knee", translation=(-0.46, 0, -0.03), parent=hip)
        scene.box(f"{tag}Shin", (0.15, 0.15, 0.52), JEANS, center=(0, 0, -0.26), parent=knee)
        foot = scene.group(f"{tag}Foot", translation=(0, 0, -0.52), parent=knee)
        scene.box(f"{tag}Shoe", (0.18, 0.32, 0.12), SHOE, center=(-0.05, 0, 0.0), parent=foot)

    path = os.path.join(out_dir, MODEL_FILES["character"])
    scene.write_glb(path)
    return path
