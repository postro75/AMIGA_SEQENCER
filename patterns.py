"""Classic genre drum patterns for DRUMSEQ (16 steps, velocity 0..4).

Track order (matches synth.DRUM_DEFS):
  0 KICK  1 SNARE  2 CLAP  3 RIM  4 CHH  5 OHH  6 TOM LO  7 TOM HI  8 CRASH  9 COWBELL
"""

from __future__ import annotations

from copy import deepcopy
from typing import Dict, List, TypedDict

STEPS = 16
NUM_TRACKS = 10


class RhythmPreset(TypedDict):
    name: str
    label: str
    bpm: float
    swing: float
    pattern: List[List[int]]


def _empty() -> List[List[int]]:
    return [[0] * STEPS for _ in range(NUM_TRACKS)]


def _set(p: List[List[int]], track: int, steps: dict[int, int]) -> None:
    for step, vel in steps.items():
        p[track][step % STEPS] = vel


def _hats_8ths(p: List[List[int]], vel: int = 2, accent_on_beats: bool = True) -> None:
    for s in range(0, STEPS, 2):
        p[4][s] = vel + 1 if (accent_on_beats and s % 4 == 0) else vel


def _hats_16ths(p: List[List[int]], strong: int = 2, weak: int = 1) -> None:
    for s in range(STEPS):
        p[4][s] = strong if s % 2 == 0 else weak


# ── Genre builders ─────────────────────────────────────────────────────────

def pattern_demo() -> List[List[int]]:
    p = _empty()
    for s in (0, 4, 8, 12):
        p[0][s] = 4
    p[0][10] = 2
    p[1][4] = 4
    p[1][12] = 4
    p[1][14] = 1
    p[2][4] = 3
    p[2][12] = 3
    p[3][6] = 2
    p[3][14] = 2
    _hats_16ths(p, 2, 1)
    p[4][7] = 3
    p[5][6] = 3
    p[5][14] = 2
    p[6][13] = 3
    p[7][14] = 3
    p[7][15] = 2
    p[8][0] = 3
    p[9][8] = 2
    p[9][11] = 1
    return p


def pattern_rock() -> List[List[int]]:
    """Classic rock backbeat — kick 1+3, snare 2+4, 8th hats, crash on 1."""
    p = _empty()
    _set(p, 0, {0: 4, 7: 2, 8: 4, 10: 2})  # kick with slight push
    _set(p, 1, {4: 4, 12: 4})  # snare 2 & 4
    _hats_8ths(p, vel=2)
    p[4][2] = 2
    p[4][6] = 2
    p[4][10] = 2
    p[4][14] = 2
    p[5][14] = 3  # open hat into turnaround
    p[6][13] = 2
    p[7][14] = 3
    p[7][15] = 2
    p[8][0] = 3
    return p


def pattern_blues() -> List[List[int]]:
    """Shuffle-feel blues (use with swing) — rim + snare backbeat, sparse kick."""
    p = _empty()
    _set(p, 0, {0: 4, 6: 2, 8: 3, 14: 2})
    _set(p, 1, {4: 3, 12: 4})
    _set(p, 3, {4: 2, 7: 2, 12: 2, 15: 2})  # rim chatter
    # triplet-ish hats on swing: strong-weak pattern
    for s in (0, 3, 4, 7, 8, 11, 12, 15):
        p[4][s] = 2 if s % 4 == 0 else 1
    p[5][10] = 2
    p[9][2] = 1
    p[9][10] = 2
    p[8][0] = 2
    return p


def pattern_modern_pop() -> List[List[int]]:
    """Four-on-floor-ish pop with clap layer, busy 16th hats."""
    p = _empty()
    for s in (0, 4, 8, 12):
        p[0][s] = 4
    p[0][6] = 1
    p[0][14] = 2
    _set(p, 1, {4: 3, 12: 4, 15: 1})
    _set(p, 2, {4: 3, 12: 3})  # stacked clap
    _hats_16ths(p, 2, 1)
    p[4][7] = 3
    p[4][11] = 3
    p[5][6] = 2
    p[5][14] = 3
    p[8][0] = 2
    return p


def pattern_disco_80s() -> List[List[int]]:
    """Disco / 80s — four-on-floor, offbeat open hats, claps on 2+4."""
    p = _empty()
    for s in range(0, STEPS, 4):
        p[0][s] = 4  # four on the floor
    _set(p, 1, {4: 3, 12: 3})
    _set(p, 2, {4: 4, 12: 4})  # disco clap
    # closed on downbeats, open on offbeats (classic disco)
    for s in range(0, STEPS, 2):
        p[4][s] = 2
    for s in (2, 6, 10, 14):
        p[5][s] = 3
        p[4][s] = 0
    p[9][0] = 2
    p[9][4] = 2
    p[9][8] = 2
    p[9][12] = 2  # cowbell pulse
    p[8][0] = 2
    return p


def pattern_synthpop() -> List[List[int]]:
    """Synthpop / new wave — tight kick, snare, gated hats, occasional rim."""
    p = _empty()
    _set(p, 0, {0: 4, 3: 2, 4: 3, 8: 4, 11: 2, 12: 3})
    _set(p, 1, {4: 4, 12: 4, 14: 1})
    _set(p, 2, {12: 2})
    _set(p, 3, {6: 2, 10: 1, 14: 2})
    _hats_16ths(p, 2, 1)
    for s in (1, 5, 9, 13):
        p[4][s] = 0  # more space
    p[5][6] = 3
    p[5][14] = 2
    p[8][0] = 3
    p[9][8] = 2
    return p


def pattern_hip_hop() -> List[List[int]]:
    """Boom-bap hip hop — syncopated kick, snare 2+4, swung hats."""
    p = _empty()
    _set(p, 0, {0: 4, 3: 2, 7: 3, 8: 2, 10: 4, 14: 2})
    _set(p, 1, {4: 4, 12: 4, 11: 1, 15: 1})  # ghost snares
    _set(p, 3, {6: 1, 14: 2})
    # hat with swing character (odd steps lighter)
    for s in range(STEPS):
        if s % 2 == 0:
            p[4][s] = 2
        else:
            p[4][s] = 1
    p[4][7] = 3
    p[5][10] = 2
    p[6][13] = 2
    p[7][15] = 2
    return p


def pattern_rap() -> List[List[int]]:
    """Modern trap-leaning rap — 808 kick pattern, snare/clap 3, rolling hats."""
    p = _empty()
    _set(p, 0, {0: 4, 5: 3, 8: 2, 10: 4, 13: 3})
    _set(p, 1, {4: 2, 12: 3})
    _set(p, 2, {4: 3, 12: 4})  # clap on 2 & 4
    # rolling 16th hats + stutters
    _hats_16ths(p, 2, 1)
    p[4][6] = 3
    p[4][7] = 3
    p[4][14] = 3
    p[4][15] = 2
    p[5][11] = 2
    p[3][9] = 1
    p[9][2] = 1
    return p


# ── Registry (order = dropdown order) ──────────────────────────────────────

RHYTHM_PRESETS: List[RhythmPreset] = [
    {
        "name": "demo",
        "label": "DEMO GROOVE",
        "bpm": 124.0,
        "swing": 0.0,
        "pattern": pattern_demo(),
    },
    {
        "name": "rock",
        "label": "ROCK",
        "bpm": 118.0,
        "swing": 0.0,
        "pattern": pattern_rock(),
    },
    {
        "name": "blues",
        "label": "BLUES",
        "bpm": 92.0,
        "swing": 0.28,
        "pattern": pattern_blues(),
    },
    {
        "name": "modern_pop",
        "label": "MODERN POP",
        "bpm": 120.0,
        "swing": 0.0,
        "pattern": pattern_modern_pop(),
    },
    {
        "name": "disco_80s",
        "label": "DISCO 80s",
        "bpm": 120.0,
        "swing": 0.0,
        "pattern": pattern_disco_80s(),
    },
    {
        "name": "synthpop",
        "label": "SYNTHPOP",
        "bpm": 128.0,
        "swing": 0.0,
        "pattern": pattern_synthpop(),
    },
    {
        "name": "hip_hop",
        "label": "HIP HOP",
        "bpm": 90.0,
        "swing": 0.18,
        "pattern": pattern_hip_hop(),
    },
    {
        "name": "rap",
        "label": "RAP / TRAP",
        "bpm": 140.0,
        "swing": 0.08,
        "pattern": pattern_rap(),
    },
]

PRESET_BY_NAME: Dict[str, RhythmPreset] = {p["name"]: p for p in RHYTHM_PRESETS}


def get_preset(name: str) -> RhythmPreset:
    return PRESET_BY_NAME[name]


def clone_pattern(pattern: List[List[int]]) -> List[List[int]]:
    return deepcopy(pattern)


def default_pattern() -> List[List[int]]:
    return clone_pattern(pattern_demo())
