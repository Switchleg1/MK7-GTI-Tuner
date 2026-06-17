from __future__ import annotations

import os

from library.core.constants import MODEL_FILES
from library.assetgen.glb_builder import GlbScene

BODY = (0.03, 0.03, 0.04, 1)
SCREEN = (0.05, 0.09, 0.11, 1)
CAM = (0.10, 0.12, 0.14, 1)
LED = (0.20, 1.0, 0.45, 1)


def build(out_dir: str) -> str:
    """A simple phone slab; the live screen is a 2D overlay drawn in-game.

    Authored centred at origin with the screen facing -Y so it points at the
    camera once reparented to the character's hand and raised.
    """
    scene = GlbScene()
    phone = scene.group("phone")
    scene.box("phone_body", (0.34, 0.06, 0.68), BODY, parent=phone, roughness=0.35, metallic=0.1)
    scene.box("phone_screen", (0.30, 0.012, 0.60), SCREEN, translation=(0, -0.032, 0.0), parent=phone, emissive=0.5)
    scene.box("phone_notch", (0.06, 0.014, 0.02), CAM, translation=(0, -0.034, 0.31), parent=phone)
    scene.cylinder("phone_led", 0.012, 0.01, axis=1, color=LED, translation=(0.12, -0.034, 0.31), parent=phone, emissive=0.9)
    path = os.path.join(out_dir, MODEL_FILES["phone"])
    scene.write_glb(path)
    return path
