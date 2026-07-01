from __future__ import annotations

import os
import random

from panda3d.core import AudioSound

from library.core.assets import assets
from library.core.constants import MUSIC_VOLUME, TOAST_SECONDS
from library.core.utils import clamp


class MusicPlayer:
    """Per-stage background music. ``set_track(key)`` switches to the songs in
    ``data/music/<key>/`` and starts a random one; when a song finishes another
    random track from the same folder plays. Each start raises a "now playing"
    toast on the app. Empty/missing folder -> silence.

    Poll-driven: ``update(dt)`` (called each render frame) watches the current song's
    ``status()`` and rolls to the next when it ends. (Panda's ``setFinishedEvent`` isn't
    implemented under the FMOD backend, so polling keeps auto-advance working on every
    audio backend.)"""

    def __init__(self, app):
        self.app = app
        self.key = None
        self.current = None
        self.song = ""
        self.volume = MUSIC_VOLUME
        self.paused = False
        self.pause_time = 0.0
        self._started = False   # True once the current song has been observed PLAYING

    def set_track(self, key: str):
        if key == self.key:
            return  # same context -> let the current song keep playing
        self.key = key
        self.paused = False
        self.pause_time = 0.0
        self._play_random()

    def set_volume(self, volume: float):
        """Set the background-music level (0..1); applies to the playing song now and
        to every song that follows. Driven by the options menu / saved config."""
        self.volume = clamp(volume, 0.0, 1.0)
        if self.current is not None:
            self.current.setVolume(self.volume)

    def update(self, dt):
        """Render-loop hook: roll to the next random track once the current one ends."""
        if self.paused or self.current is None:
            return
        if self.current.status() == AudioSound.PLAYING:
            self._started = True
        elif self._started:  # was playing, now stopped on its own -> it finished
            self._play_random()

    def pause(self):
        """Pause the current song without changing the active stage music key."""
        if self.current is None or self.paused:
            return
        try:
            self.pause_time = self.current.getTime()
        except Exception:  # noqa: BLE001
            self.pause_time = 0.0
        self.current.stop()
        self.paused = True

    def resume(self):
        """Resume a song paused by ``pause``. No-op if music was already silent."""
        if not self.paused:
            return
        self.paused = False
        if self.current is None:
            return
        try:
            self.current.setTime(self.pause_time)
        except Exception:  # noqa: BLE001
            pass
        self._started = False
        self.current.play()
        self.pause_time = 0.0

    # -- internals ---------------------------------------------------------
    def _play_random(self):
        self._stop()
        songs = assets.music_paths(self.key) if self.key else []
        if not songs:
            return
        path = random.choice(songs)
        music = self.app.loader.loadMusic(path)
        if music is None:
            return
        music.setLoop(False)
        music.setVolume(self.volume)
        music.play()
        self.current = music
        self._started = False
        self.song = self._title(path)
        toast = getattr(self.app, "toast", None)
        if toast is not None:
            toast.show("NOW PLAYING", self.song, TOAST_SECONDS)

    def _stop(self):
        if self.current is not None:
            self.current.stop()
            self.current = None
        self.paused = False
        self.pause_time = 0.0
        self._started = False

    @staticmethod
    def _title(path):
        return os.path.splitext(os.path.basename(path))[0].replace("_", " ")
