#!/usr/bin/env python3
"""Download classic Amiga ST-xx sample disks from Aminet + optional MOD demo.

Sources (public archives / demoscene culture):
  - Aminet mods/inst/st-0N.lha  (original Soundtracker/ProTracker sample disks)
  - Internet Archive: https://archive.org/details/AmigaSTXX  (Public Domain Mark)
  - MOD demo from The Mod Archive

Usage:
  python fetch_amiga_samples.py
  python fetch_amiga_samples.py --disks 1,2,3,4,5
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

try:
    import lhafile
except ImportError:
    print("Need lhafile:  pip install lhafile")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent / "samples"
AMINET = "https://aminet.net/mods/inst/st-{n:02d}.lha"
# Classic free MOD with drums (elekfunk / moby) — for instrument ripping demo
MOD_URLS = [
    ("elekfunk.mod", "https://api.modarchive.org/downloads.php?moduleid=41529"),
]


def download(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  GET {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DRUMSEQ/1.0 (Amiga sample fetch)"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        if len(data) < 1000:
            print(f"  ! too small ({len(data)} bytes)")
            return False
        dest.write_bytes(data)
        print(f"  → {dest} ({len(data)} bytes)")
        return True
    except Exception as e:
        print(f"  ! {e}")
        return False


def extract_lha(lha_path: Path, out_root: Path) -> int:
    lf = lhafile.Lhafile(str(lha_path))
    n = 0
    for info in lf.infolist():
        fname = info.filename.replace("\\", "/")
        if fname.endswith("/"):
            continue
        out = out_root / fname
        # normalize top-level to ST-0N
        parts = Path(fname).parts
        if parts:
            top = parts[0]
            if top.upper().startswith("ST"):
                # ST-01 or st-01
                fixed = top.upper() if top.upper().startswith("ST-") else top
                if not fixed.startswith("ST-") and fixed.startswith("ST"):
                    fixed = "ST-" + fixed[2:]
                out = out_root / fixed / Path(*parts[1:]) if len(parts) > 1 else out_root / fixed
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(lf.read(info.filename))
        n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch Amiga ST-xx sample disks")
    ap.add_argument("--disks", default="1,2,3", help="Comma list of ST disk numbers (default 1,2,3)")
    ap.add_argument("--skip-mod", action="store_true")
    args = ap.parse_args()

    disks = [int(x.strip()) for x in args.disks.split(",") if x.strip()]
    dl = ROOT / "_download"
    dl.mkdir(parents=True, exist_ok=True)
    (ROOT / "MOD").mkdir(parents=True, exist_ok=True)

    print("=== Amiga ST-xx sample fetch ===")
    print("Archive: Aminet mods/inst + archive.org/details/AmigaSTXX")
    for n in disks:
        url = AMINET.format(n=n)
        dest = dl / f"st-{n:02d}.lha"
        if dest.exists() and dest.stat().st_size > 10000:
            print(f"ST-{n:02d}: cached {dest.name}")
        else:
            if not download(url, dest):
                continue
        count = extract_lha(dest, ROOT)
        print(f"ST-{n:02d}: extracted {count} samples")

    if not args.skip_mod:
        print("=== MOD demo (instrument source) ===")
        for name, url in MOD_URLS:
            dest = ROOT / "MOD" / name
            if dest.exists() and dest.stat().st_size > 1000:
                # verify not HTML
                head = dest.read_bytes()[:4]
                if head not in (b"<!", b"<ht", b"<!D"):
                    print(f"MOD cached: {name}")
                    continue
            download(url, dest)

    print("Done. Kits available under samples/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
