"""Procedural drum synthesis — no external samples required."""

from __future__ import annotations

import math
from typing import Dict

import numpy as np

from audio_engine import SAMPLE_RATE, Sound, get_engine


def _to_sound(wave: np.ndarray, volume: float = 0.85) -> Sound:
    wave = np.clip(wave * volume, -1.0, 1.0).astype(np.float32)
    return get_engine().make_sound(wave)


def kick(duration: float = 0.38) -> Sound:
    n = int(duration * SAMPLE_RATE)
    t = np.linspace(0, duration, n, endpoint=False, dtype=np.float32)
    freq = 150 * np.exp(-t * 28) + 45
    phase = 2 * math.pi * np.cumsum(freq) / SAMPLE_RATE
    body = np.sin(phase) * np.exp(-t * 7.5)
    click = np.sin(2 * math.pi * 1800 * t) * np.exp(-t * 90) * 0.35
    sub = np.sin(2 * math.pi * 55 * t) * np.exp(-t * 5) * 0.4
    return _to_sound(body + click + sub, 0.95)


def snare(duration: float = 0.28) -> Sound:
    n = int(duration * SAMPLE_RATE)
    t = np.linspace(0, duration, n, endpoint=False, dtype=np.float32)
    tone = np.sin(2 * math.pi * 185 * t) * np.exp(-t * 18)
    noise = np.random.default_rng(42).uniform(-1, 1, n).astype(np.float32)
    noise *= np.exp(-t * 14)
    snap = np.sin(2 * math.pi * 3200 * t) * np.exp(-t * 55) * 0.25
    return _to_sound(tone * 0.45 + noise * 0.75 + snap, 0.8)


def closed_hat(duration: float = 0.09) -> Sound:
    n = int(duration * SAMPLE_RATE)
    t = np.linspace(0, duration, n, endpoint=False, dtype=np.float32)
    rng = np.random.default_rng(7)
    noise = rng.uniform(-1, 1, n).astype(np.float32)
    noise = np.diff(noise, prepend=noise[0])
    noise = noise / (np.max(np.abs(noise)) + 1e-9)
    metal = (
        np.sin(2 * math.pi * 5400 * t)
        + 0.6 * np.sin(2 * math.pi * 7800 * t)
        + 0.4 * np.sin(2 * math.pi * 10500 * t)
    )
    wave = (noise * 0.7 + metal * 0.3) * np.exp(-t * 55)
    return _to_sound(wave, 0.45)


def open_hat(duration: float = 0.45) -> Sound:
    n = int(duration * SAMPLE_RATE)
    t = np.linspace(0, duration, n, endpoint=False, dtype=np.float32)
    rng = np.random.default_rng(11)
    noise = rng.uniform(-1, 1, n).astype(np.float32)
    noise = np.diff(noise, prepend=noise[0])
    noise = noise / (np.max(np.abs(noise)) + 1e-9)
    metal = (
        np.sin(2 * math.pi * 5200 * t)
        + 0.5 * np.sin(2 * math.pi * 7600 * t)
        + 0.35 * np.sin(2 * math.pi * 9800 * t)
    )
    wave = (noise * 0.65 + metal * 0.35) * np.exp(-t * 7)
    return _to_sound(wave, 0.4)


def clap(duration: float = 0.22) -> Sound:
    n = int(duration * SAMPLE_RATE)
    t = np.linspace(0, duration, n, endpoint=False, dtype=np.float32)
    rng = np.random.default_rng(99)
    noise = rng.uniform(-1, 1, n).astype(np.float32)
    bursts = np.zeros(n, dtype=np.float32)
    for delay, amp in ((0.0, 1.0), (0.012, 0.85), (0.024, 0.7), (0.04, 0.55)):
        d = int(delay * SAMPLE_RATE)
        if d < n:
            tail = n - d
            tt = np.linspace(0, duration - delay, tail, endpoint=False)
            bursts[d:] += amp * np.exp(-tt * 28)
    wave = noise * bursts * 0.9
    return _to_sound(wave, 0.7)


def tom(freq: float = 120.0, duration: float = 0.35) -> Sound:
    n = int(duration * SAMPLE_RATE)
    t = np.linspace(0, duration, n, endpoint=False, dtype=np.float32)
    f = freq * np.exp(-t * 6) + freq * 0.35
    phase = 2 * math.pi * np.cumsum(f) / SAMPLE_RATE
    body = np.sin(phase) * np.exp(-t * 6.5)
    click = np.sin(2 * math.pi * (freq * 4) * t) * np.exp(-t * 40) * 0.2
    return _to_sound(body + click, 0.75)


def rim(duration: float = 0.08) -> Sound:
    n = int(duration * SAMPLE_RATE)
    t = np.linspace(0, duration, n, endpoint=False, dtype=np.float32)
    wave = (
        np.sin(2 * math.pi * 900 * t) * 0.6
        + np.sin(2 * math.pi * 1400 * t) * 0.3
        + np.random.default_rng(3).uniform(-1, 1, n).astype(np.float32) * 0.15
    ) * np.exp(-t * 70)
    return _to_sound(wave, 0.55)


def crash(duration: float = 1.2) -> Sound:
    n = int(duration * SAMPLE_RATE)
    t = np.linspace(0, duration, n, endpoint=False, dtype=np.float32)
    rng = np.random.default_rng(21)
    noise = rng.uniform(-1, 1, n).astype(np.float32)
    metal = sum(
        np.sin(2 * math.pi * f * t) * a
        for f, a in ((3200, 0.2), (4500, 0.15), (6700, 0.12), (8900, 0.1), (11000, 0.08))
    )
    wave = (noise * 0.55 + metal) * np.exp(-t * 2.2)
    return _to_sound(wave, 0.5)


def cowbell(duration: float = 0.2) -> Sound:
    n = int(duration * SAMPLE_RATE)
    t = np.linspace(0, duration, n, endpoint=False, dtype=np.float32)
    wave = (
        np.sin(2 * math.pi * 587 * t)
        + 0.7 * np.sin(2 * math.pi * 845 * t)
    ) * np.exp(-t * 14)
    wave = np.tanh(wave * 2.5)
    return _to_sound(wave, 0.55)


# GM channel 10 drum map
DRUM_DEFS = [
    {"name": "KICK", "short": "BD", "midi": 36, "color": (255, 95, 109), "factory": kick},
    {"name": "SNARE", "short": "SD", "midi": 38, "color": (255, 195, 75), "factory": snare},
    {"name": "CLAP", "short": "CP", "midi": 39, "color": (255, 140, 66), "factory": clap},
    {"name": "RIM", "short": "RS", "midi": 37, "color": (255, 220, 120), "factory": rim},
    {"name": "CHH", "short": "HH", "midi": 42, "color": (80, 220, 180), "factory": closed_hat},
    {"name": "OHH", "short": "OH", "midi": 46, "color": (60, 200, 255), "factory": open_hat},
    {
        "name": "TOM LO",
        "short": "TL",
        "midi": 41,
        "color": (170, 120, 255),
        "factory": lambda: tom(95),
    },
    {
        "name": "TOM HI",
        "short": "TH",
        "midi": 45,
        "color": (200, 140, 255),
        "factory": lambda: tom(145),
    },
    {"name": "CRASH", "short": "CR", "midi": 49, "color": (255, 80, 200), "factory": crash},
    {"name": "COWBELL", "short": "CB", "midi": 56, "color": (120, 255, 100), "factory": cowbell},
]


def build_kit() -> Dict[str, Sound]:
    kit: Dict[str, Sound] = {}
    for d in DRUM_DEFS:
        kit[d["name"]] = d["factory"]()
    return kit
