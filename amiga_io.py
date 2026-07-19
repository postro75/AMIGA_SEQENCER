"""Load classic Amiga audio: IFF 8SVX, raw 8-bit PCM, ProTracker MOD instruments."""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# Default Paula-ish rate when header lacks one (common mid-range ST sample pitch)
DEFAULT_AMIGA_RATE = 16726


def _u16be(b: bytes, off: int = 0) -> int:
    return struct.unpack_from(">H", b, off)[0]


def _u32be(b: bytes, off: int = 0) -> int:
    return struct.unpack_from(">I", b, off)[0]


def _s8_to_float(pcm: bytes | np.ndarray) -> np.ndarray:
    if isinstance(pcm, bytes):
        arr = np.frombuffer(pcm, dtype=np.int8).astype(np.float32)
    else:
        arr = pcm.astype(np.float32)
    return arr / 128.0


def _resample_linear(wave: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    if src_rate <= 0 or dst_rate <= 0 or len(wave) == 0:
        return wave
    if src_rate == dst_rate:
        return wave.astype(np.float32)
    n_out = max(1, int(round(len(wave) * dst_rate / src_rate)))
    x_old = np.linspace(0.0, 1.0, num=len(wave), endpoint=False)
    x_new = np.linspace(0.0, 1.0, num=n_out, endpoint=False)
    return np.interp(x_new, x_old, wave).astype(np.float32)


def parse_iff_8svx(data: bytes) -> Tuple[np.ndarray, int]:
    """
    Parse IFF 8SVX sample → (float32 mono -1..1, sample_rate).
    Falls back carefully if structure is incomplete.
    """
    if len(data) < 12 or data[0:4] != b"FORM":
        raise ValueError("not IFF FORM")

    # Walk chunks inside FORM
    # FORM size at 4, type at 8
    form_type = data[8:12]
    if form_type not in (b"8SVX", b"16SV"):
        # some files still have BODY later
        pass

    pos = 12
    sample_rate = DEFAULT_AMIGA_RATE
    body = b""
    oneshot = 0

    while pos + 8 <= len(data):
        chunk_id = data[pos : pos + 4]
        chunk_size = _u32be(data, pos + 4)
        pos += 8
        chunk = data[pos : pos + chunk_size]
        # IFF chunks are word-aligned
        pos += chunk_size + (chunk_size & 1)

        if chunk_id == b"VHDR" and len(chunk) >= 14:
            oneshot = _u32be(chunk, 0)
            # samplesPerSec at offset 12 (UWORD)
            if len(chunk) >= 14:
                rate = _u16be(chunk, 12)
                if 1000 <= rate <= 56000:
                    sample_rate = rate
        elif chunk_id == b"BODY":
            body = chunk
        elif chunk_id == b"NAME":
            pass

    if not body:
        # maybe raw after header failure — treat remaining as PCM
        raise ValueError("no BODY chunk")

    # 8SVX is signed 8-bit
    wave = _s8_to_float(body)
    # Prefer oneshot length if present and sane
    if 16 < oneshot < len(wave):
        wave = wave[:oneshot]
    return wave, sample_rate


def load_amiga_sample(path: Path | str, target_rate: int = 44100) -> np.ndarray:
    """Load Amiga sample file (IFF 8SVX or raw signed 8-bit) → float32 @ target_rate."""
    path = Path(path)
    data = path.read_bytes()
    wave: np.ndarray
    rate = DEFAULT_AMIGA_RATE

    if len(data) >= 12 and data[0:4] == b"FORM":
        try:
            wave, rate = parse_iff_8svx(data)
        except Exception:
            # corrupted IFF — try BODY hunt
            idx = data.find(b"BODY")
            if idx >= 0 and idx + 8 < len(data):
                size = _u32be(data, idx + 4)
                body = data[idx + 8 : idx + 8 + size]
                wave = _s8_to_float(body)
            else:
                wave = _s8_to_float(data)
    else:
        # RAW signed 8-bit PCM (common on ST disks)
        wave = _s8_to_float(data)

    # strip leading silence-ish zeros
    if len(wave) > 32:
        thr = 0.02
        nz = np.where(np.abs(wave) > thr)[0]
        if len(nz):
            start = max(0, int(nz[0]) - 2)
            wave = wave[start:]

    # soft fade-out to avoid click
    if len(wave) > 64:
        fade = min(128, len(wave) // 8)
        env = np.ones(len(wave), dtype=np.float32)
        env[-fade:] = np.linspace(1.0, 0.0, fade, dtype=np.float32)
        wave = wave * env

    wave = _resample_linear(wave, rate, target_rate)
    # light Amiga grit: re-quantize to 8-bit and back (optional authenticity)
    wave = np.clip(wave, -1.0, 1.0)
    wave = (np.round(wave * 127.0) / 127.0).astype(np.float32)
    peak = float(np.max(np.abs(wave))) or 1.0
    if peak > 0.05:
        wave = wave * (0.95 / peak)
    return wave


# ── ProTracker MOD sample extraction ───────────────────────────────────────

def _mod_sample_count(data: bytes) -> int:
    """31 samples for M.K./etc, 15 for old Soundtracker."""
    if len(data) < 1084:
        return 15
    tag = data[1080:1084]
    if tag in (
        b"M.K.",
        b"M!K!",
        b"FLT4",
        b"FLT8",
        b"4CHN",
        b"6CHN",
        b"8CHN",
        b"CD81",
        b"OKTA",
        b"16CN",
        b"32CN",
    ):
        return 31
    # numeric channel tags e.g. '12CH'
    if tag[2:4] == b"CH" and tag[0:2].isdigit():
        return 31
    return 15


def extract_mod_samples(path: Path | str) -> List[Dict]:
    """
    Extract instruments from a classic ProTracker .mod file.
    Returns list of dicts: name, length, volume, finetune, wave (float32 @ 44100).
    """
    path = Path(path)
    data = path.read_bytes()
    if len(data) < 1084:
        return []

    n_samples = _mod_sample_count(data)
    # sample headers start at 20
    headers = []
    for i in range(n_samples):
        off = 20 + i * 30
        name = data[off : off + 22].split(b"\x00")[0].decode("latin-1", errors="replace").strip()
        length_words = _u16be(data, off + 22)
        length = length_words * 2
        finetune = data[off + 24] & 0x0F
        volume = data[off + 25]
        loop_start = _u16be(data, off + 26) * 2
        loop_len = _u16be(data, off + 28) * 2
        headers.append(
            {
                "index": i + 1,
                "name": name or f"sample{i+1}",
                "length": length,
                "finetune": finetune,
                "volume": volume,
                "loop_start": loop_start,
                "loop_len": loop_len,
            }
        )

    # order table
    if n_samples == 31:
        song_len = data[950]
        # restart = data[951]
        order = list(data[952:1080])
        pattern_offset = 1084
    else:
        song_len = data[470]
        order = list(data[472:600])
        pattern_offset = 600

    n_patterns = max(order[:song_len]) + 1 if song_len else 0
    # channels
    if n_samples == 31:
        tag = data[1080:1084]
        if tag in (b"6CHN",):
            ch = 6
        elif tag in (b"8CHN", b"CD81", b"OKTA"):
            ch = 8
        elif tag[2:4] == b"CH" and tag[0:2].isdigit():
            ch = int(tag[0:2])
        else:
            ch = 4
    else:
        ch = 4

    pattern_size = 64 * ch * 4
    samples_offset = pattern_offset + n_patterns * pattern_size

    results = []
    cursor = samples_offset
    for h in headers:
        length = h["length"]
        if length <= 2 or cursor + length > len(data):
            # skip empty
            if length > 0 and cursor + length <= len(data):
                cursor += length
            continue
        raw = data[cursor : cursor + length]
        cursor += length
        # first 2 bytes often null in PT
        pcm = raw[2:] if len(raw) > 2 else raw
        wave = _s8_to_float(pcm)
        # ProTracker C-2 base ≈ 8287 Hz (PAL)
        rate = 8287
        wave = _resample_linear(wave, rate, 44100)
        vol = max(1, h["volume"]) / 64.0
        wave = np.clip(wave * vol * 1.2, -1.0, 1.0).astype(np.float32)
        if len(wave) > 64:
            fade = min(256, len(wave) // 6)
            env = np.ones(len(wave), dtype=np.float32)
            env[-fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
            wave *= env
        results.append({**h, "wave": wave, "source": path.name})
    return results


def list_sample_files(folder: Path) -> List[Path]:
    if not folder.is_dir():
        return []
    files = []
    for p in sorted(folder.iterdir()):
        if p.is_file() and not p.name.startswith("."):
            # skip readmes
            if p.suffix.lower() in {".txt", ".readme", ".md", ".lha", ".zip"}:
                continue
            files.append(p)
    return files
