from __future__ import annotations

import os
import sys

from panda3d.core import Filename, NodePath

from library.core.constants import IMAGE_FILES, IMAGES_DIR, MODEL_FILES, MODELS_DIR


def data_root() -> str:
    """Directory that contains the ``data/`` folder, for both modes.

    - Frozen (PyInstaller): assets are bundled under ``sys._MEIPASS``.
    - From source: the project root, three levels up from this file
      (``library/core/assets.py`` -> ``library/core`` -> ``library`` -> root).
    """
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _abs(rel: str) -> str:
    return os.path.normpath(os.path.join(data_root(), rel))


def load_model(key: str) -> NodePath:
    """Load a generated .glb by its key in constants.MODEL_FILES."""
    import gltf
    from gltf import GltfSettings

    path = _abs(os.path.join(MODELS_DIR, MODEL_FILES[key]))
    return NodePath(gltf.load_model(path, GltfSettings(skip_axis_conversion=True)))


def image_path(key: str) -> str:
    """Panda-style path string for a generated .png (OnscreenImage/TexturePool)."""
    return str(Filename.fromOsSpecific(_abs(os.path.join(IMAGES_DIR, IMAGE_FILES[key]))))
