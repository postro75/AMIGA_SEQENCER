"""Export drum patterns to Standard MIDI File (GM channel 10)."""

from __future__ import annotations

from pathlib import Path
from typing import List, Sequence

import mido

from synth import DRUM_DEFS

# step velocity: 0 = off, 1..4 velocity tiers
VELOCITY_MAP = {1: 55, 2: 80, 3: 100, 4: 127}


def pattern_to_midi(
    pattern: Sequence[Sequence[int]],
    bpm: float,
    steps: int,
    path: str | Path,
    track_names: Sequence[str] | None = None,
) -> Path:
    """
    pattern[track][step] -> velocity tier 0..4
    Writes Type-1 SMF, channel 9 (0-indexed) = GM drums.
    """
    path = Path(path)
    mid = mido.MidiFile(type=1, ticks_per_beat=480)
    meta = mido.MidiTrack()
    mid.tracks.append(meta)
    meta.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm), time=0))
    meta.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
    meta.append(mido.MetaMessage("track_name", name="DRUMSEQ", time=0))

    drum_track = mido.MidiTrack()
    mid.tracks.append(drum_track)
    drum_track.append(mido.MetaMessage("track_name", name="Drums", time=0))

    names = track_names or [d["name"] for d in DRUM_DEFS]
    note_for_track = {d["name"]: d["midi"] for d in DRUM_DEFS}

    # Collect absolute-time events
    events: List[tuple[int, str, int, int]] = []  # tick, type, note, vel
    ticks_per_step = mid.ticks_per_beat // 4  # 16th notes

    for ti, tname in enumerate(names):
        if ti >= len(pattern):
            break
        note = note_for_track.get(tname, 36 + ti)
        for step in range(min(steps, len(pattern[ti]))):
            tier = int(pattern[ti][step])
            if tier <= 0:
                continue
            vel = VELOCITY_MAP.get(tier, 100)
            tick = step * ticks_per_step
            events.append((tick, "on", note, vel))
            events.append((tick + ticks_per_step // 2, "off", note, 0))

    events.sort(key=lambda e: (e[0], 0 if e[1] == "off" else 1))

    last = 0
    for tick, etype, note, vel in events:
        delta = tick - last
        last = tick
        if etype == "on":
            drum_track.append(
                mido.Message("note_on", note=note, velocity=vel, channel=9, time=delta)
            )
        else:
            drum_track.append(
                mido.Message("note_off", note=note, velocity=0, channel=9, time=delta)
            )

    # End of track after last bar
    end_tick = steps * ticks_per_step
    drum_track.append(mido.MetaMessage("end_of_track", time=max(0, end_tick - last)))
    meta.append(mido.MetaMessage("end_of_track", time=0))

    path.parent.mkdir(parents=True, exist_ok=True)
    mid.save(str(path))
    return path
