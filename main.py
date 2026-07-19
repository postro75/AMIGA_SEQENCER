#!/usr/bin/env python3
"""
DRUMSEQ — Retro Rack
Ableton-style drum step sequencer with Atari demoscene intro,
procedural synth drums, and MIDI export.

Usage:
    python main.py
    python main.py --skip-demo
    python main.py --bpm 128
"""

from __future__ import annotations

import argparse
import sys

import pygame


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DRUMSEQ Retro Rack — drum step sequencer")
    parser.add_argument("--skip-demo", action="store_true", help="Skip Atari-style intro")
    parser.add_argument("--bpm", type=float, default=124.0, help="Initial BPM (default 124)")
    parser.add_argument("--width", type=int, default=1280, help="Window width")
    parser.add_argument("--height", type=int, default=800, help="Window height")
    parser.add_argument("--demo-ms", type=int, default=8500, help="Intro duration in ms")
    args = parser.parse_args(argv)

    # Mixer may be missing on some pygame builds — audio uses sounddevice fallback.
    try:
        pygame.mixer.pre_init(44100, -16, 2, 512)
    except Exception:
        pass
    pygame.init()
    try:
        pygame.mixer.init(44100, -16, 2, 512)
    except Exception:
        pass

    from audio_engine import get_engine, shutdown_engine

    engine = get_engine()
    print(f"[DRUMSEQ] audio backend: {engine.backend}")

    pygame.display.set_caption("DRUMSEQ — Retro Rack")

    flags = pygame.RESIZABLE | pygame.DOUBLEBUF
    screen = pygame.display.set_mode((args.width, args.height), flags)
    clock = pygame.time.Clock()

    try:
        icon = pygame.Surface((32, 32))
        icon.fill((0, 230, 255))
        pygame.draw.rect(icon, (255, 60, 180), (6, 6, 8, 20))
        pygame.draw.rect(icon, (255, 195, 75), (16, 10, 8, 16))
        pygame.display.set_icon(icon)
    except Exception:
        pass

    try:
        if not args.skip_demo:
            from demo import run_demo

            run_demo(screen, clock, duration_ms=args.demo_ms)

        from app import DrumSequencerApp

        app = DrumSequencerApp(screen, clock)
        app.state.bpm = max(40.0, min(220.0, args.bpm))
        app.run()
    finally:
        shutdown_engine()
        pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
