from __future__ import annotations

import random

from library.core.assets.assets import sound_path
from library.core.constants import AUDIO, FX_VOLUME
from library.core.utils import clamp


class GameAudio:
    """Runtime sound service: a pitched engine loop plus pooled pop/bang one-shots.

    The engine/intake/turbo are looping sounds whose play-rate (pitch) tracks RPM and
    whose volume tracks throttle load -- so one rendered loop covers the whole rev
    range. Pops and bangs are short samples loaded as a small pool of independent
    voices and round-robined, so an overrun burst overlaps instead of cutting itself
    off. Everything degrades gracefully: if Panda has no audio backend the whole
    service no-ops and the game runs silently.

    Created once on the app shell (``MK7Tuner3D``); tasks drive it via ``app.audio``.
    """

    def __init__(self, base):
        self.base = base
        self.enabled = False
        self.fx_volume = FX_VOLUME  # master gain for all SFX (engine/pops/bangs)
        self.engine = self.intake = self.turbo = None
        self.pops: list = []
        self.bangs: list = []
        self.bovs: list = []
        self._pi = self._bi = self._vi = 0
        try:
            mgr = base.sfxManagerList[0] if getattr(base, "sfxManagerList", None) else None
            if mgr is None or not mgr.isValid():
                return
            self.mgr = mgr
            mgr.setConcurrentSoundLimit(AUDIO["concurrent_limit"])
            mgr.setVolume(self.fx_volume)  # master SFX gain (options menu adjusts it)
            self.engine = self._loop("engine")
            self.intake = self._loop("intake")
            self.turbo = self._loop("turbo")
            n = AUDIO["pool_size"]
            self.pops = self._pool(("pop_1", "pop_2", "pop_3"), n)
            self.bangs = self._pool(("bang_1", "bang_2", "bang_3"), n)
            self.bovs = self._pool(("bov",), n)
            self.enabled = self.engine is not None
        except Exception:  # noqa: BLE001 - never let audio setup crash the game
            self.enabled = False

    # -- loading -----------------------------------------------------------
    def _sound(self, key):
        sound = self.mgr.getSound(sound_path(key), False)
        return sound if sound is not None and sound.length() > 0 else None

    def _loop(self, key):
        sound = self._sound(key)
        if sound is not None:
            sound.setLoop(True)
            sound.setVolume(0.0)
            sound.play()
        return sound

    def _pool(self, keys, count):
        pool = []
        for key in keys:
            for _ in range(count):
                sound = self._sound(key)
                if sound is not None:
                    sound.setLoop(False)
                    pool.append(sound)
        return pool

    # -- engine ------------------------------------------------------------
    def set_engine(self, rpm, load):
        """Pitch/level the engine layers. ``load`` is 0..1 throttle/effort."""
        if not self.enabled:
            return
        load = clamp(load, 0.0, 1.0)
        rate = clamp(rpm / AUDIO["engine_base_rpm"], AUDIO["rate_min"], AUDIO["rate_max"])
        self.engine.setPlayRate(rate)
        self.engine.setVolume(load * AUDIO["engine_volume"])
        if self.intake is not None:
            self.intake.setVolume(load * load * AUDIO["intake_volume"])
            self.intake.setPlayRate(clamp(0.8 + rpm / 9000.0, 0.8, 1.8))
        if self.turbo is not None:
            spool = clamp((rpm - 2400) / 3800.0, 0.0, 1.0)
            self.turbo.setVolume(spool * load * AUDIO["turbo_volume"])
            self.turbo.setPlayRate(clamp(rpm / 3000.0, 0.6, 3.0))

    def idle(self, rpm=950):
        self.set_engine(rpm, AUDIO["idle_load"])

    def set_fx_volume(self, volume):
        """Master gain for all sound effects (0..1) via the AudioManager -- scales the
        engine loop and every pop/bang at once. Driven by the options menu / config."""
        self.fx_volume = clamp(volume, 0.0, 1.0)
        if self.enabled:
            self.mgr.setVolume(self.fx_volume)

    def silence(self):
        if not self.enabled:
            return
        for sound in (self.engine, self.intake, self.turbo):
            if sound is not None:
                sound.setVolume(0.0)

    # -- one-shots ---------------------------------------------------------
    def _fire(self, pool, attr, volume):
        if not self.enabled or not pool:
            return
        index = getattr(self, attr)
        sound = pool[index % len(pool)]
        setattr(self, attr, (index + 1) % len(pool))
        sound.setVolume(clamp(volume, 0.0, 1.0))
        sound.setPlayRate(random.uniform(0.9, 1.15))
        sound.play()

    def pop(self, volume=None):
        base = AUDIO["pop_volume"] if volume is None else volume
        self._fire(self.pops, "_pi", base * random.uniform(0.75, 1.0))

    def bang(self, volume=None):
        base = AUDIO["bang_volume"] if volume is None else volume
        self._fire(self.bangs, "_bi", base * random.uniform(0.8, 1.0))

    def bov(self):
        self._fire(self.bovs, "_vi", AUDIO["bov_volume"])

    def overrun(self, intensity, duration=1.0):
        """Schedule a crackle burst over ``duration`` seconds. ``intensity`` 0..100."""
        if not self.enabled or intensity <= 2:
            return
        amount = clamp(intensity / 100.0, 0.0, 1.0)
        count = int(4 + amount * AUDIO["overrun_count"])
        for _ in range(count):
            delay = random.random() * duration * (0.5 + 0.5 * random.random())
            is_bang = random.random() < amount * 0.55
            name = "audio-burst-%d" % random.randint(0, 1 << 30)
            self.base.taskMgr.doMethodLater(delay, self._burst_hit, name, extraArgs=[is_bang, amount])

    def _burst_hit(self, is_bang, amount):
        if is_bang:
            self.bang(AUDIO["bang_volume"] * (0.6 + amount * 0.5))
        else:
            self.pop(AUDIO["pop_volume"] * (0.6 + amount * 0.5))
