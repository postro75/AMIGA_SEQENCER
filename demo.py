"""Atari / demoscene-style intro — starfield, plasma, scroller, chip beeps."""

from __future__ import annotations

import math
import random
from typing import List

import numpy as np
import pygame

from audio_engine import get_engine

# Retro palette
BLACK = (0, 0, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 200)
YELLOW = (255, 230, 0)
ORANGE = (255, 140, 0)
LIME = (100, 255, 50)
WHITE = (255, 255, 255)
PURPLE = (140, 60, 255)


def _chip_wave(freq: float, duration: float = 0.08, vol: float = 0.12) -> np.ndarray:
    sr = 44100
    n = int(duration * sr)
    t = np.linspace(0, duration, n, endpoint=False)
    wave = np.sign(np.sin(2 * math.pi * freq * t)).astype(np.float32)
    env = np.linspace(1.0, 0.0, n).astype(np.float32) ** 0.5
    return wave * env * vol


def _make_logo_surface(font_big: pygame.font.Font, font_sm: pygame.font.Font) -> pygame.Surface:
    lines = [
        (font_big, "DRUMSEQ", CYAN),
        (font_sm, "RETRO RACK v1.0", MAGENTA),
        (font_sm, "ATARI DEMO MODE", YELLOW),
    ]
    surfs = [f.render(txt, True, col) for f, txt, col in lines]
    w = max(s.get_width() for s in surfs) + 40
    h = sum(s.get_height() for s in surfs) + 30
    logo = pygame.Surface((w, h), pygame.SRCALPHA)
    y = 8
    for s in surfs:
        logo.blit(s, ((w - s.get_width()) // 2, y))
        y += s.get_height() + 4
    pygame.draw.rect(logo, CYAN, logo.get_rect().inflate(-4, -4), 2, border_radius=6)
    pygame.draw.rect(logo, MAGENTA, logo.get_rect().inflate(-10, -10), 1, border_radius=4)
    return logo


def run_demo(screen: pygame.Surface, clock: pygame.time.Clock, duration_ms: int = 8500) -> None:
    """Play a short demoscene intro, skippable with any key / click / ESC."""
    w, h = screen.get_size()
    font_big = pygame.font.SysFont("menlo,consolas,courier", 64, bold=True)
    font_sm = pygame.font.SysFont("menlo,consolas,courier", 22, bold=True)
    font_tiny = pygame.font.SysFont("menlo,consolas,courier", 16, bold=True)
    logo = _make_logo_surface(font_big, font_sm)
    engine = get_engine()

    stars: List[List[float]] = [
        [random.uniform(0, w), random.uniform(0, h), random.uniform(0.4, 3.2)] for _ in range(160)
    ]

    pw, ph = 80, 50
    plasma = pygame.Surface((pw, ph))

    scroll_text = (
        "  *** DRUMSEQ RETRO RACK ***  "
        "16-STEP ABLETON-STYLE SEQUENCER  "
        "PROCEDURAL SYNTH DRUMS  "
        "MIDI EXPORT  "
        "CLICK PADS TO PROGRAM  "
        "SPACE = PLAY/STOP  "
        "S = SAVE MIDI  "
        "PRESS ANY KEY TO START  "
        "GREETZ TO ALL BEATMAKERS  "
        "MADE WITH PYTHON + PYGAME  ***  "
    )
    scroll_surf = font_sm.render(scroll_text, True, LIME)
    scroll_x = float(w)

    notes = [220, 277, 330, 440, 330, 277, 220, 165]
    note_i = 0
    last_beep = 0
    beeps = [_chip_wave(f) for f in notes]
    bar_colors = [MAGENTA, CYAN, YELLOW, LIME, ORANGE, PURPLE]

    start = pygame.time.get_ticks()
    running = True
    while running:
        now = pygame.time.get_ticks()
        elapsed = now - start
        if elapsed >= duration_ms:
            break

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                running = False
                break

        t = elapsed / 1000.0

        screen.fill((5, 0, 12))
        for s in stars:
            s[0] -= s[2] * 2.2
            if s[0] < 0:
                s[0] = w
                s[1] = random.uniform(0, h)
            bright = min(255, int(80 + s[2] * 55))
            size = 1 if s[2] < 1.5 else 2
            pygame.draw.circle(
                screen, (bright, bright, min(255, bright + 40)), (int(s[0]), int(s[1])), size
            )

        xs = np.arange(pw, dtype=np.float32)
        ys = np.arange(ph, dtype=np.float32)
        xx, yy = np.meshgrid(xs, ys)
        v = (
            np.sin(xx / 8.0 + t * 2.2)
            + np.sin(yy / 6.0 + t * 1.7)
            + np.sin((xx + yy) / 10.0 + t)
            + np.sin(np.hypot(xx - pw / 2, yy - ph / 2) / 6.0 - t * 2)
        )
        r = (128 + 127 * np.sin(v * np.pi + t)).astype(np.uint8) // 3
        g = (128 + 127 * np.sin(v * np.pi + t + 2)).astype(np.uint8) // 4
        b = (128 + 127 * np.sin(v * np.pi + t + 4)).astype(np.uint8)
        rgb = np.dstack([r, g, b])
        pygame.surfarray.blit_array(plasma, np.transpose(rgb, (1, 0, 2)))
        scaled = pygame.transform.scale(plasma, (w, h))
        scaled.set_alpha(90)
        screen.blit(scaled, (0, 0))

        for i, col in enumerate(bar_colors):
            by = int(h * 0.55 + math.sin(t * 3 + i * 0.7) * 40 + i * 14)
            bar = pygame.Surface((w, 10), pygame.SRCALPHA)
            for yy in range(10):
                a = int(180 * (1 - abs(yy - 5) / 5))
                pygame.draw.line(bar, (*col, a), (0, yy), (w, yy))
            screen.blit(bar, (0, by))

        lx = w // 2 - logo.get_width() // 2
        ly = int(h * 0.22 + math.sin(t * 2.4) * 28)
        screen.blit(logo, (lx + 3, ly + 3))
        screen.blit(logo, (lx, ly))

        for y in range(0, h, 3):
            pygame.draw.line(screen, (0, 0, 0), (0, y), (w, y))

        scroll_x -= 3.5
        if scroll_x < -scroll_surf.get_width():
            scroll_x = float(w)
        for i in range(0, scroll_surf.get_width(), 4):
            slice_rect = pygame.Rect(i, 0, 4, scroll_surf.get_height())
            sy = int(h - 70 + math.sin(t * 6 + i * 0.04) * 10)
            screen.blit(scroll_surf, (int(scroll_x) + i, sy), slice_rect)

        progress = min(1.0, elapsed / duration_ms)
        pygame.draw.rect(screen, (40, 20, 60), (40, h - 28, w - 80, 8), border_radius=4)
        pygame.draw.rect(screen, CYAN, (40, h - 28, int((w - 80) * progress), 8), border_radius=4)
        hint = font_tiny.render("PRESS ANY KEY / CLICK TO SKIP", True, WHITE)
        screen.blit(hint, (w // 2 - hint.get_width() // 2, h - 48))

        pygame.draw.rect(screen, CYAN, screen.get_rect().inflate(-6, -6), 2)

        if now - last_beep > 140:
            engine.play_wave(beeps[note_i % len(beeps)], 1.0)
            note_i += 1
            last_beep = now

        pygame.display.flip()
        clock.tick(60)

    fade = pygame.Surface((w, h))
    fade.fill(BLACK)
    for a in range(0, 255, 18):
        fade.set_alpha(a)
        screen.blit(fade, (0, 0))
        pygame.display.flip()
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
