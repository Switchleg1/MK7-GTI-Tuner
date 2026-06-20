from __future__ import annotations

import os
import random

from library.core.assets import assets
from library.core.constants import MUSIC_VOLUME, TOAST_SECONDS
from library.core.utils import clamp


class MusicPlayer:
    """Per-stage background music. ``set_track(key)`` switches to the songs in
    ``data/music/<key>/`` and starts a random one; when a song finishes another
    random track from the same folder plays. Each start raises a "now playing"
    toast on the app. Empty/missing folder -> silence.

    Finish-driven (Panda's ``setFinishedEvent``), so ``update(dt)`` is just a hook
    in the game render loop; nothing to poll."""

    def __init__(self, app):
        self.app = app
        self.key = None
        self.current = None
        self.song = ""
        self.token = 0
        self.volume = MUSIC_VOLUME
        self.paused = False
        self.pause_time = 0.0

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
        """Render-loop hook. Music advances on the finished event, not per frame."""

    def pause(self):
        """Pause the current song without changing the active stage music key."""
        if self.current is None or self.paused:
            return
        try:
            self.pause_time = self.current.getTime()
        except Exception:  # noqa: BLE001
            self.pause_time = 0.0
        self.app.ignore(f"music-finished-{self.token}")
        self.current.stop()
        self.paused = True

    def resume(self):
        """Resume a song paused by ``pause``. No-op if music was already silent."""
        if not self.paused:
            return
        self.paused = False
        if self.current is None:
            return
        event = f"music-finished-{self.token}"
        self.current.setFinishedEvent(event)
        self.app.acceptOnce(event, self._play_random)
        try:
            self.current.setTime(self.pause_time)
        except Exception:  # noqa: BLE001
            pass
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
        self.token += 1
        event = f"music-finished-{self.token}"
        music.setFinishedEvent(event)
        self.app.acceptOnce(event, self._play_random)  # next song when this one ends
        music.play()
        self.current = music
        self.song = self._title(path)
        toast = getattr(self.app, "toast", None)
        if toast is not None:
            toast.show("NOW PLAYING", self.song, TOAST_SECONDS)

    def _stop(self):
        if self.current is not None:
            self.app.ignore(f"music-finished-{self.token}")  # don't chain on manual stop
            self.current.stop()
            self.current = None
        self.paused = False
        self.pause_time = 0.0

    @staticmethod
    def _title(path):
        return os.path.splitext(os.path.basename(path))[0].replace("_", " ")
