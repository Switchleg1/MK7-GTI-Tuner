from __future__ import annotations

import os

from library.core.constants import MODEL_FILES
from library.assetgen.glb_builder import GlbScene

RED = (0.80, 0.10, 0.13, 1)
DARK = (0.03, 0.03, 0.04, 1)
GLASS = (0.05, 0.08, 0.11, 1)
TRIM = (0.06, 0.06, 0.07, 1)
TIRE = (0.04, 0.04, 0.05, 1)
RIM = (0.62, 0.64, 0.68, 1)
SEAT = (0.09, 0.09, 0.11, 1)
INTERIOR = (0.07, 0.08, 0.09, 1)
HEAD = (0.85, 0.88, 0.92, 1)
TAIL = (0.70, 0.05, 0.06, 1)

# Static body panels: (name, size, color, translation, material kwargs)
BODY_PARTS = [
    ("lower_body", (1.84, 4.30, 0.58), RED, (0, 0, 0.50), {"roughness": 0.35, "metallic": 0.1}),
    ("belt_line", (1.74, 4.05, 0.30), RED, (0, -0.05, 0.84), {"roughness": 0.35, "metallic": 0.1}),
    ("greenhouse", (1.52, 2.90, 0.46), GLASS, (0, -0.45, 1.20), {"roughness": 0.15, "metallic": 0.2}),
    ("roof", (1.48, 2.30, 0.12), RED, (0, -0.60, 1.46), {"roughness": 0.35, "metallic": 0.1}),
    ("a_pillar", (1.40, 0.14, 0.46), DARK, (0, 0.98, 1.18), {}),
    ("hood", (1.62, 1.30, 0.10), RED, (0, 1.48, 0.96), {"roughness": 0.35, "metallic": 0.1}),
    ("front_bumper", (1.86, 0.45, 0.54), TRIM, (0, 2.12, 0.46), {}),
    ("grille", (1.30, 0.10, 0.26), DARK, (0, 2.30, 0.54), {}),
    ("gti_stripe", (1.34, 0.12, 0.05), RED, (0, 2.31, 0.72), {"emissive": 0.2}),
    ("rear_bumper", (1.86, 0.42, 0.50), TRIM, (0, -2.12, 0.46), {}),
    ("hatch", (1.58, 0.34, 0.76), RED, (0, -1.96, 0.94), {"roughness": 0.35, "metallic": 0.1}),
    ("dash", (1.46, 0.34, 0.22), INTERIOR, (0, 1.45, 0.82), {}),
    ("console", (0.34, 1.00, 0.26), INTERIOR, (0.0, 0.70, 0.60), {}),
]

# Headlights / taillights: (name, x, y, color)
LIGHTS = [
    ("hl_l", -0.60, 2.32, HEAD), ("hl_r", 0.60, 2.32, HEAD),
    ("tl_l", -0.62, -2.30, TAIL), ("tl_r", 0.62, -2.30, TAIL),
]

# Wheels at (x, y); driver side is -x.
WHEEL_XY = [(-0.92, 1.45), (0.92, 1.45), (-0.92, -1.45), (0.92, -1.45)]


def build(out_dir: str) -> str:
    """Stylised MK7 GTI (red, faces +Y) with the driver door (-X) already open
    and a visible interior, so the seated character can reach the OBD2 port."""
    scene = GlbScene()
    car = scene.group("car")

    for name, size, color, pos, kw in BODY_PARTS:
        scene.box(name, size, color, translation=pos, parent=car, **kw)

    for name, x, y, color in LIGHTS:
        scene.box(name, (0.40, 0.10, 0.18), color, translation=(x, y, 0.62), parent=car, emissive=0.5)

    for index, (x, y) in enumerate(WHEEL_XY):
        scene.cylinder(f"tire_{index}", 0.36, 0.26, axis=0, color=TIRE, translation=(x, y, 0.36), parent=car, segments=20)
        scene.cylinder(f"rim_{index}", 0.20, 0.28, axis=0, color=RIM, translation=(x, y, 0.36), parent=car, segments=12, metallic=0.8, roughness=0.3)

    # Driver seat (left, -X), reachable through the open door.
    seat = scene.group("driver_seat", translation=(-0.48, 0.05, 0), parent=car)
    scene.box("seat_base", (0.46, 0.52, 0.16), SEAT, translation=(0, 0, 0.50), parent=seat)
    scene.box("seat_back", (0.46, 0.16, 0.56), SEAT, translation=(0, 0.30, 0.86), parent=seat)

    # Steering wheel + column on the driver side.
    scene.cylinder("steering_wheel", 0.18, 0.05, axis=1, color=DARK, translation=(-0.48, 1.28, 0.86), parent=car, segments=18)
    scene.box("steering_column", (0.07, 0.28, 0.07), DARK, translation=(-0.48, 1.40, 0.78), parent=car)

    # Open driver door: hinge at the front edge, panel swings outward (-X).
    hinge = scene.group("door_hinge", translation=(-0.90, 0.92, 0.74), parent=car, rotation_hpr=(70, 0, 0))
    scene.box("driver_door", (0.07, 1.45, 0.80), RED, center=(-0.02, -0.72, 0.0), parent=hinge, roughness=0.35, metallic=0.1)
    scene.box("door_window", (0.05, 1.10, 0.34), GLASS, center=(-0.02, -0.70, 0.50), parent=hinge, roughness=0.15)
    scene.box("door_trim", (0.09, 1.30, 0.10), TRIM, center=(0, -0.70, -0.16), parent=hinge)

    path = os.path.join(out_dir, MODEL_FILES["car"])
    scene.write_glb(path)
    return path
