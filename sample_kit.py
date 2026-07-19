"""Amiga ST-xx / MOD sample banks for DRUMSEQ tracks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from amiga_io import extract_mod_samples, list_sample_files, load_amiga_sample
from audio_engine import Sound, get_engine
from synth import DRUM_DEFS, build_kit as build_synth_kit

SAMPLES_ROOT = Path(__file__).resolve().parent / "samples"

# Preferred filename stems per drum track (case-insensitive match, order = priority)
ST_DRUM_CANDIDATES: Dict[str, List[str]] = {
    "KICK": [
        "BassDrum3",
        "BassDrum2",
        "BassDrum1",
        "BassDrum4",
        "BassDrum5",
        "bassdrum8",
        "BassDrum",
        "bdrum",
        "bd",
    ],
    "SNARE": [
        "Snare3",
        "Snare2",
        "Snare1",
        "PopSnare2",
        "PopSnare1",
        "PopSnare3",
        "Snare4",
        "Snare5",
        "Snare6",
        "Snare7",
        "snare10",
        "snare",
        "sdrum",
        "sd",
    ],
    "CLAP": ["Claps1", "Claps2", "theclaps", "Jarreclaps", "Clap", "claps"],
    "RIM": ["SynClaves", "Claves", "Rim", "WoodBlock", "Chink", "stick"],
    "CHH": [
        "CloseHiHat",
        "thehihatclosed",
        "HiHat1",
        "HiHat2",
        "HiHat3",
        "HiHat4",
        "hihat",
        "closed",
    ],
    "OHH": [
        "thehihatopen",
        "HiHat2",
        "HiHat4",
        "HiHat1",
        "HiHat3",
        "Shaker",
        "openhat",
        "open",
    ],
    "TOM LO": [
        "DxTom",
        "ElecTom",
        "thetom1",
        "perc-drytom",
        "Perc-HandDrum",
        "Perc-Taiko",
        "tom",
    ],
    "TOM HI": ["ElecTom", "DxTom", "thetom2", "Perc-Timbale", "Perc-Bongo", "tom"],
    "CRASH": ["Smash1", "Smash2", "Cymbal1", "Cymbal", "Blast", "blast", "crash", "cymbal"],
    "COWBELL": ["CowBell", "Cowbell2", "cowbell", "cow"],
}


@dataclass
class KitInfo:
    id: str
    label: str
    kind: str  # synth | st | mod | folder
    path: Optional[Path] = None


def discover_kits() -> List[KitInfo]:
    kits = [
        KitInfo(id="synth", label="SYNTH (proc)", kind="synth"),
    ]
    if SAMPLES_ROOT.is_dir():
        for d in sorted(SAMPLES_ROOT.iterdir()):
            if d.is_dir() and d.name.upper().startswith("ST-"):
                n = len(list_sample_files(d))
                if n:
                    kits.append(
                        KitInfo(id=f"st:{d.name}", label=f"{d.name.upper()} ({n})", kind="st", path=d)
                    )
        mod_dir = SAMPLES_ROOT / "MOD"
        if mod_dir.is_dir():
            for mod in sorted(mod_dir.glob("*.mod")) + sorted(mod_dir.glob("*.MOD")):
                kits.append(
                    KitInfo(id=f"mod:{mod.name}", label=f"MOD:{mod.stem[:12]}", kind="mod", path=mod)
                )
        # custom folders that aren't ST- / MOD / _download
        for d in sorted(SAMPLES_ROOT.iterdir()):
            if not d.is_dir():
                continue
            if d.name.startswith("_") or d.name.upper().startswith("ST-") or d.name.upper() == "MOD":
                continue
            n = len(list_sample_files(d))
            if n:
                kits.append(
                    KitInfo(id=f"folder:{d.name}", label=f"DIR:{d.name[:14]}", kind="folder", path=d)
                )
    return kits


def _norm(s: str) -> str:
    return "".join(c.lower() for c in s if c.isalnum())


def _match_file(files: Sequence[Path], candidates: Sequence[str]) -> Optional[Path]:
    """Match preferred sample names. Exact stem first, then prefix/contains (min 3 chars)."""
    by_norm = {_norm(p.stem): p for p in files}
    # 1) exact stem / name
    for cand in candidates:
        key = _norm(cand)
        if not key:
            continue
        if key in by_norm:
            return by_norm[key]
    # 2) candidate is prefix of stem (BassDrum → BassDrum5)
    for cand in candidates:
        key = _norm(cand)
        if len(key) < 3:
            continue
        hits = [(nk, p) for nk, p in by_norm.items() if nk.startswith(key)]
        if hits:
            hits.sort(key=lambda t: len(t[0]))
            return hits[0][1]
    # 3) candidate contained in stem (snare in PopSnare1) — require len>=4
    for cand in candidates:
        key = _norm(cand)
        if len(key) < 4:
            continue
        hits = [(nk, p) for nk, p in by_norm.items() if key in nk]
        if hits:
            # prefer shorter names (more specific drum one-shots)
            hits.sort(key=lambda t: (len(t[0]), t[0]))
            return hits[0][1]
    return None


def _sound_from_wave(wave) -> Sound:
    return get_engine().make_sound(wave)


def build_st_kit(folder: Path) -> Dict[str, Sound]:
    files = list_sample_files(folder)
    kit: Dict[str, Sound] = {}
    used: set[Path] = set()
    for drum in DRUM_DEFS:
        name = drum["name"]
        cands = ST_DRUM_CANDIDATES.get(name, [name])
        path = _match_file(files, cands)
        if path is None or path in used:
            # leave for synth fallback — don't grab random melodic samples
            continue
        try:
            wave = load_amiga_sample(path)
            kit[name] = _sound_from_wave(wave)
            used.add(path)
            print(f"  [{folder.name}] {name:8} ← {path.name}")
        except Exception as e:
            print(f"  ! failed {path.name}: {e}")
    # fill missing from synth so sequencer never silent
    missing = [d["name"] for d in DRUM_DEFS if d["name"] not in kit]
    if missing:
        synth = build_synth_kit()
        for name in missing:
            kit[name] = synth[name]
            print(f"  [{folder.name}] {name:8} ← (synth fallback)")
    return kit


def build_mod_kit(mod_path: Path) -> Dict[str, Sound]:
    samples = extract_mod_samples(mod_path)
    print(f"  MOD {mod_path.name}: {len(samples)} instruments")
    kit: Dict[str, Sound] = {}
    # Rank by duration buckets — classic MOD drums are short one-shots
    ranked = sorted(samples, key=lambda s: len(s["wave"]))
    # Use distinct instruments: shortest → hats/rim, mid → snare/clap, longer → kick/tom
    picked = []
    for s in ranked:
        if len(s["wave"]) < 200:
            continue
        picked.append(s)
        if len(picked) >= 12:
            break
    if not picked:
        picked = ranked[:10]

    # Assign by name first
    used_idx: set[int] = set()

    def by_name(*keys: str, max_dur: float = 2.0) -> Optional[dict]:
        keys_n = [_norm(k) for k in keys if len(_norm(k)) >= 3]
        best, score = None, 0
        for s in samples:
            if s["index"] in used_idx:
                continue
            nm = _norm(s["name"])
            dur = len(s["wave"]) / 44100.0
            if dur > max_dur or dur < 0.01:
                continue
            sc = sum(3 for k in keys_n if k in nm)
            if sc > score:
                score, best = sc, s
        return best if score > 0 else None

    def by_duration(lo: float, hi: float) -> Optional[dict]:
        for s in ranked:
            if s["index"] in used_idx:
                continue
            dur = len(s["wave"]) / 44100.0
            if lo <= dur <= hi:
                return s
        return None

    plan = [
        ("KICK", ["kick", "bassdrum", "bass"], 0.05, 0.9),
        ("SNARE", ["snare", "snr"], 0.04, 0.7),
        ("CLAP", ["clap"], 0.04, 0.6),
        ("RIM", ["rim", "clave", "stick"], 0.02, 0.35),
        ("CHH", ["hihat", "hat", "close"], 0.02, 0.4),
        ("OHH", ["open"], 0.05, 0.8),
        ("TOM LO", ["tom", "low"], 0.05, 0.8),
        ("TOM HI", ["tom", "hi"], 0.04, 0.7),
        ("CRASH", ["crash", "cym", "smash"], 0.1, 2.0),
        ("COWBELL", ["cow", "bell", "perc"], 0.03, 0.5),
    ]
    # duration fallbacks (seconds) when name fails
    dur_fb = {
        "KICK": (0.12, 0.55),
        "SNARE": (0.08, 0.35),
        "CLAP": (0.06, 0.3),
        "RIM": (0.02, 0.12),
        "CHH": (0.02, 0.12),
        "OHH": (0.08, 0.4),
        "TOM LO": (0.1, 0.45),
        "TOM HI": (0.08, 0.35),
        "CRASH": (0.2, 1.5),
        "COWBELL": (0.04, 0.25),
    }

    for track, keys, _lo, maxd in plan:
        s = by_name(*keys, max_dur=maxd)
        if s is None:
            lo, hi = dur_fb.get(track, (0.05, 0.5))
            s = by_duration(lo, hi)
        if s is None:
            s = by_duration(0.02, 2.0)
        if s is None:
            continue
        kit[track] = _sound_from_wave(s["wave"])
        used_idx.add(s["index"])
        print(f"  [MOD] {track:8} ← #{s['index']} {s['name']!r} ({len(s['wave'])/44100:.2f}s)")

    synth = build_synth_kit()
    for d in DRUM_DEFS:
        kit.setdefault(d["name"], synth[d["name"]])
    return kit


def build_kit_for(info: KitInfo) -> Dict[str, Sound]:
    print(f"[kit] loading {info.label}…")
    if info.kind == "synth" or info.path is None:
        return build_synth_kit()
    if info.kind == "st" or info.kind == "folder":
        return build_st_kit(info.path)
    if info.kind == "mod":
        return build_mod_kit(info.path)
    return build_synth_kit()
