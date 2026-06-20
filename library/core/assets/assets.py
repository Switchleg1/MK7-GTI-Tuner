from __future__ import annotations

import glob
import os
import sys

from panda3d.core import Filename, NodePath, TexturePool

from library.core.constants import (
    AUDIO, AUDIO_DIR, IMAGE_FILES, IMAGES_DIR, MODELS_DIR, MUSIC_DIR, MUSIC_EXTS, SOUND_FILES,
)

from library.core.assets.model_types import ModelType

_MODEL_CACHE: dict[tuple[ModelType, str], NodePath] = {}
_IMAGE_CACHE: dict[str, object] = {}
_SOUND_CACHE: dict[tuple[int, str, bool], list] = {}
_LOOPING_SOUND_KEYS = {"engine", "intake", "turbo"}


def _abs(rel: str) -> str:
    return os.path.normpath(os.path.join(data_root(), rel))


def _panda_path(rel: str) -> str:
    return str(Filename.fromOsSpecific(_abs(rel)))


def data_root() -> str:
    """Directory that contains the ``data/`` folder, for both modes.

    - Frozen (PyInstaller): assets are bundled under ``sys._MEIPASS``.
    - From source: the project root, three levels up from this file
      (``library/core/assets.py`` -> ``library/core`` -> ``library`` -> root).
    """
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def preload_assets(app=None) -> None:
    """Load all non-music assets into memory.

    Music is intentionally excluded so stage tracks still stream/load on demand.
    """
    preload_models()
    preload_images()
    preload_sounds(app)


def preload_models() -> None:
    for model_type in ModelType:
        for key in model_type.value.dictionary:
            _cached_model(model_type, key)


def preload_images() -> None:
    for key in IMAGE_FILES:
        load_image(key)


def preload_sounds(app=None) -> None:
    mgr = _sound_manager(app)
    if mgr is None:
        return
    for key in SOUND_FILES:
        bucket = _sound_bucket(mgr, key, False)
        target = _sound_preload_count(key)
        while len(bucket) < target:
            sound = _load_sound_from_disk(mgr, key, False)
            if sound is None:
                break
            bucket.append(sound)


def load_model(type: ModelType, key: str) -> NodePath:
    """Return a copy of a cached generated .glb by its key."""
    return _copy_model(_cached_model(type, key))


def _copy_model(model: NodePath) -> NodePath:
    parent = NodePath("asset-copy")
    copy = model.copyTo(parent)
    copy.detachNode()
    return copy


def _cached_model(type: ModelType, key: str) -> NodePath:
    cache_key = (type, key)
    model = _MODEL_CACHE.get(cache_key)
    if model is None:
        model = _load_model_from_disk(type, key)
        _MODEL_CACHE[cache_key] = model
    return model


def _load_model_from_disk(type: ModelType, key: str) -> NodePath:
    import gltf
    from gltf import GltfSettings

    path = _abs(os.path.join(f"{MODELS_DIR}/{type.value.directory}", type.value.dictionary[key]))
    return NodePath(gltf.load_model(path, GltfSettings(skip_axis_conversion=True)))


def load_image(key: str):
    """Return a cached generated texture by key."""
    texture = _IMAGE_CACHE.get(key)
    if texture is None:
        texture = TexturePool.loadTexture(Filename.fromOsSpecific(_abs(os.path.join(IMAGES_DIR, IMAGE_FILES[key]))))
        if texture is None:
            raise FileNotFoundError(image_path(key))
        _IMAGE_CACHE[key] = texture
    return texture


def image_path(key: str) -> str:
    """Panda-style path string for a generated .png (OnscreenImage/TexturePool)."""
    return _panda_path(os.path.join(IMAGES_DIR, IMAGE_FILES[key]))


def load_sound(manager, key: str, positional: bool = False):
    """Return a preloaded sound instance when available; otherwise load one."""
    bucket = _sound_bucket(manager, key, positional)
    if bucket:
        return bucket.pop()
    return _load_sound_from_disk(manager, key, positional)


def _load_sound_from_disk(manager, key: str, positional: bool):
    sound = manager.getSound(sound_path(key), positional)
    return sound if sound is not None and sound.length() > 0 else None


def _sound_manager(app):
    if app is None:
        return None
    managers = getattr(app, "sfxManagerList", None)
    if not managers:
        return None
    manager = managers[0]
    return manager if manager is not None and manager.isValid() else None


def _sound_bucket(manager, key: str, positional: bool) -> list:
    return _SOUND_CACHE.setdefault((id(manager), key, positional), [])


def _sound_preload_count(key: str) -> int:
    if key in _LOOPING_SOUND_KEYS:
        return 1
    return AUDIO["pool_size"]


def sound_path(key: str) -> str:
    """Panda-style path string for a generated .wav in constants.SOUND_FILES."""
    return _panda_path(os.path.join(AUDIO_DIR, SOUND_FILES[key]))


def music_paths(key: str) -> list[str]:
    """Panda-style path strings for every song under data/music/<key>/.

    Whatever the user dropped in (any MUSIC_EXTS), sorted. Empty/missing -> []."""
    folder = _abs(os.path.join(MUSIC_DIR, key))
    if not os.path.isdir(folder):
        return []
    found: list[str] = []
    for ext in MUSIC_EXTS:
        found += glob.glob(os.path.join(folder, "*" + ext))
    return [str(Filename.fromOsSpecific(path)) for path in sorted(found)]
