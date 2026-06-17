#!/usr/bin/env python3
"""Procedurally synthesize the game's sound effects as 16-bit PCM .wav files.

Offline and dependency-free (standard library ``wave``/``struct``/``math`` only,
matching ``asset_images`` which avoids PIL). Output lands in ``data/audio/`` and is
loaded at runtime by ``library.core.audio.GameAudio`` through Panda3D's audio
manager. The looping engine note is rendered at ``AUDIO['engine_base_rpm']`` and
pitched in-game with ``setPlayRate``; pops/bangs are short one-shots played from a
pool so bursts overlap.

    python -m library.assetgen.asset_audio        # writes data/audio/*.wav
"""
from __future__ import annotations

import math
import os
import random
import struct
import wave

from library.core.constants import AUDIO, SOUND_FILES

SR = 44100  # sample rate


# -- low-level DSP helpers --------------------------------------------------
def _white(n):
    return [random.uniform(-1.0, 1.0) for _ in range(n)]


def _biquad_bandpass(x, f0, q):
    """RBJ resonant band-pass (constant skirt gain). Direct-form II transposed."""
    w0 = 2 * math.pi * f0 / SR
    cosw, sinw = math.cos(w0), math.sin(w0)
    alpha = sinw / (2 * q)
    a0 = 1 + alpha
    b0, b1, b2 = alpha / a0, 0.0, -alpha / a0
    a1, a2 = (-2 * cosw) / a0, (1 - alpha) / a0
    y = [0.0] * len(x)
    x1 = x2 = y1 = y2 = 0.0
    for i, xi in enumerate(x):
        yi = b0 * xi + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1 = x1, xi
        y2, y1 = y1, yi
        y[i] = yi
    return y


def _normalize(samples, peak=0.9):
    hi = max((abs(s) for s in samples), default=0.0) or 1.0
    k = peak / hi
    return [s * k for s in samples]


def _crossfade_loop(samples, xf):
    """Blend the head into the tail so a looped buffer has no seam click."""
    n = len(samples)
    xf = min(xf, n // 2)
    out = list(samples)
    for i in range(xf):
        a = i / xf
        out[i] = samples[i] * a + samples[n - xf + i] * (1 - a)
    return out[: n - xf]  # drop the blended tail; loop point is now seamless


def _write(path, samples):
    ints = [max(-32767, min(32767, int(max(-1.0, min(1.0, s)) * 32767))) for s in samples]
    data = struct.pack("<%dh" % len(ints), *ints)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data)
    return path


# -- voices -----------------------------------------------------------------
def _engine_loop():
    """Seamless EA888-ish exhaust note at the base RPM (order-2 fundamental).

    Everything is a harmonic of 100 Hz / 50 Hz over an integer number of cycles,
    so the buffer loops perfectly; tanh adds the combustion grit. No noise here so
    the loop stays click-free -- the intake loop carries the broadband rush.
    """
    f0 = AUDIO["engine_base_rpm"] / 30.0  # 3000 rpm -> 100 Hz
    n = int(SR * 0.40)                     # 40 cycles of 100 Hz, 20 of 50 Hz
    amps = [1.0, 0.85, 0.92, 0.55, 0.6, 0.42, 0.32, 0.26, 0.2, 0.16, 0.12, 0.09]
    out = [0.0] * n
    for i in range(n):
        t = i / SR
        s = 0.5 * math.sin(2 * math.pi * (f0 / 2) * t)  # sub octave (50 Hz)
        for h, a in enumerate(amps, start=1):
            s += a * math.sin(2 * math.pi * f0 * h * t)
        s *= 0.65 + 0.35 * abs(math.sin(math.pi * f0 * t))  # firing-pulse emphasis
        out[i] = math.tanh(s * 0.9)
    return _normalize(out, 0.85)


def _intake_loop():
    """Broadband induction rush -- band-passed noise, cross-faded to loop clean."""
    n = int(SR * 0.5)
    bp = _biquad_bandpass(_white(n), 700, 0.7)
    return _normalize(_crossfade_loop(bp, 2200), 0.8)


def _turbo_loop():
    """Spool whistle: a high tone (+ fifth) with slight shimmer; pitched in-game."""
    f = 3000.0
    n = int(SR * 0.10)  # 300 cycles of 3 kHz, 5 of 50 Hz -> seamless
    out = []
    for i in range(n):
        t = i / SR
        s = math.sin(2 * math.pi * f * t) + 0.4 * math.sin(2 * math.pi * f * 1.5 * t)
        s *= 0.85 + 0.15 * math.sin(2 * math.pi * 50 * t)
        out.append(s)
    return _normalize(out, 0.7)


def _pop(center):
    """A short overrun crackle: band-passed noise transient + a metallic tick."""
    n = int(SR * 0.12)
    bp = _biquad_bandpass(_white(n), center, 8.0)
    tick_f = random.uniform(260, 520)
    out = [0.0] * n
    for i in range(n):
        t = i / SR
        out[i] = bp[i] * math.exp(-t / 0.025) + 0.5 * math.sin(2 * math.pi * tick_f * t) * math.exp(-t / 0.04)
    return _normalize(out, 0.9)


def _bang():
    """A backfire: low thump (135->46 Hz sweep) + distorted crack + pipe ring + tail."""
    n = int(SR * 0.34)
    crack = _biquad_bandpass(_white(n), random.uniform(700, 1500), 1.2)
    tail = _biquad_bandpass(_white(n), 200, 0.5)
    out = [0.0] * n
    phase = 0.0
    for i in range(n):
        t = i / SR
        f = 135 * math.exp(math.log(46 / 135) * min(1.0, t / 0.2))  # thump pitch sweep
        phase += 2 * math.pi * f / SR
        thump = math.sin(phase) * math.exp(-t / 0.12)
        crk = math.tanh(crack[i] * 3.0) * math.exp(-t / 0.06)
        ring = math.sin(2 * math.pi * 180 * t) * math.exp(-t / 0.10)
        rumble = tail[i] * math.exp(-t / 0.18)
        out[i] = 1.1 * thump + 0.8 * crk + 0.5 * ring + 0.35 * rumble
    return _normalize(out, 0.95)


def _bov():
    """Blow-off 'pshhh': broadband noise with a fast attack and a soft decay tail."""
    n = int(SR * 0.32)
    bp = _biquad_bandpass(_white(n), 900, 0.8)
    out = [0.0] * n
    for i in range(n):
        t = i / SR
        out[i] = bp[i] * min(1.0, t / 0.02) * math.exp(-t / 0.12)
    return _normalize(out, 0.75)


# -- orchestration ----------------------------------------------------------
def _voice(key):
    if key == "engine":
        return _engine_loop()
    if key == "intake":
        return _intake_loop()
    if key == "turbo":
        return _turbo_loop()
    if key.startswith("pop_"):
        return _pop({"pop_1": 2000, "pop_2": 2800, "pop_3": 3600}[key])
    if key.startswith("bang_"):
        return _bang()
    if key == "bov":
        return _bov()
    raise KeyError(key)


def build(out_dir):
    """Synthesize every sound in SOUND_FILES into out_dir; return the paths."""
    random.seed(7)  # deterministic re-generation
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for key, filename in SOUND_FILES.items():
        paths.append(_write(os.path.join(out_dir, filename), _voice(key)))
    return paths


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from library.core.constants import AUDIO_DIR

    for path in build(os.path.join(root, AUDIO_DIR)):
        print(f"  {os.path.basename(path):<18} {os.path.getsize(path):>7} bytes")
