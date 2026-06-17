from __future__ import annotations

import os

from library.core.constants import MODEL_FILES
from library.assetgen.glb_builder import GlbScene

PORT = (0.04, 0.05, 0.06, 1)
PORT_RIM = (0.20, 0.24, 0.28, 1)
DONGLE = (0.10, 0.32, 0.62, 1)
DONGLE_TOP = (0.14, 0.42, 0.78, 1)
CABLE = (0.05, 0.05, 0.06, 1)
LED = (0.30, 1.0, 0.55, 1)


def build(out_dir: str) -> str:
    """OBD2 socket + a separate plug-in adapter dongle.

    Two independent top-level nodes ('obd_port', 'obd_adapter') so the stage can
    place the port under the dash and slide the adapter into it on click.
    """
    scene = GlbScene()

    port = scene.group("obd_port")
    scene.box("port_shell", (0.18, 0.07, 0.10), PORT, parent=port, roughness=0.5)
    scene.box("port_rim", (0.20, 0.03, 0.12), PORT_RIM, translation=(0, -0.05, 0), parent=port, emissive=0.15)

    adapter = scene.group("obd_adapter")
    scene.box("dongle_body", (0.16, 0.16, 0.11), DONGLE, parent=adapter, roughness=0.4)
    scene.box("dongle_top", (0.13, 0.13, 0.02), DONGLE_TOP, translation=(0, 0, 0.065), parent=adapter, emissive=0.1)
    scene.box("dongle_plug", (0.14, 0.06, 0.07), PORT, translation=(0, -0.10, 0), parent=adapter)
    scene.cylinder("dongle_led", 0.014, 0.012, axis=1, color=LED, translation=(0.05, 0.085, 0.0), parent=adapter, emissive=0.9)
    scene.cylinder("dongle_cable", 0.02, 0.5, axis=2, color=CABLE, translation=(-0.05, 0.06, -0.30), parent=adapter, segments=10)

    path = os.path.join(out_dir, MODEL_FILES["obd"])
    scene.write_glb(path)
    return path
