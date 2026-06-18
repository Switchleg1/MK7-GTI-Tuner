from __future__ import annotations

from library.core import storage
from library.core.constants import FX_VOLUME, MUSIC_VOLUME
from library.core.utils import clamp


class Config:
    """Player options, persisted to ``options.cfg`` between runs (loaded at startup,
    saved whenever changed in the menu). Sound is wired now; ``graphics`` is a
    forward-compatible bag for resolution / vsync / etc. later.

    ``apply(app)`` pushes the live values into the music player and audio service."""

    def __init__(self):
        self.music_volume = MUSIC_VOLUME
        self.fx_volume = FX_VOLUME
        self.graphics: dict = {}  # resolution / vsync / ... (not used yet)

    # -- persistence -------------------------------------------------------
    @classmethod
    def load(cls) -> "Config":
        config = cls()
        data = storage.read_json(storage.config_path())
        if data:
            config.from_dict(data)
        return config

    def save(self) -> bool:
        return storage.write_json(storage.config_path(), self.to_dict())

    def to_dict(self) -> dict:
        return {"music_volume": self.music_volume, "fx_volume": self.fx_volume, "graphics": self.graphics}

    def from_dict(self, data: dict):
        self.music_volume = clamp(float(data.get("music_volume", self.music_volume)), 0.0, 1.0)
        self.fx_volume = clamp(float(data.get("fx_volume", self.fx_volume)), 0.0, 1.0)
        self.graphics = dict(data.get("graphics", {}))

    # -- runtime -----------------------------------------------------------
    def apply(self, app):
        app.music.set_volume(self.music_volume)
        app.audio.set_fx_volume(self.fx_volume)
