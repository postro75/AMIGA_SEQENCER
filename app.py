"""Ableton-inspired drum step sequencer with retro neon visuals."""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import pygame

from midi_export import pattern_to_midi
from patterns import RHYTHM_PRESETS, clone_pattern, default_pattern
from sample_kit import KitInfo, build_kit_for, discover_kits
from synth import DRUM_DEFS

# ── Theme ──────────────────────────────────────────────────────────────────
BG = (8, 8, 14)
PANEL = (16, 16, 26)
PANEL2 = (22, 22, 36)
GRID_LINE = (35, 35, 55)
BEAT_LINE = (55, 55, 90)
TEXT = (220, 225, 240)
MUTED = (120, 125, 150)
ACCENT = (0, 230, 255)
ACCENT2 = (255, 60, 180)
PLAYHEAD = (255, 255, 255)
GLOW_PLAY = (0, 255, 180)
DROPDOWN_BG = (18, 18, 32)
DROPDOWN_HOVER = (40, 50, 80)
DROPDOWN_SEL = (0, 90, 100)

STEPS = 16
NUM_TRACKS = len(DRUM_DEFS)


@dataclass
class SequencerState:
    pattern: List[List[int]] = field(default_factory=default_pattern)
    bpm: float = 124.0
    playing: bool = False
    step: int = 0
    swing: float = 0.0  # 0..0.4 fraction of 16th
    mute: List[bool] = field(default_factory=lambda: [False] * NUM_TRACKS)
    solo: List[bool] = field(default_factory=lambda: [False] * NUM_TRACKS)
    status: str = "Ready — SPACE play · click pads · S save MIDI"
    last_saved: Optional[str] = None
    rhythm_index: int = 0  # index into RHYTHM_PRESETS
    kit_index: int = 0  # index into kit list


class DrumSequencerApp:
    def __init__(self, screen: pygame.Surface, clock: pygame.time.Clock):
        self.screen = screen
        self.clock = clock
        self.w, self.h = screen.get_size()
        self.state = SequencerState()
        self.kits: List[KitInfo] = discover_kits()
        # Prefer ST-01 if present
        for i, k in enumerate(self.kits):
            if k.id == "st:ST-01":
                self.state.kit_index = i
                break
        self.kit = build_kit_for(self.kits[self.state.kit_index])
        self.fonts = {
            "title": pygame.font.SysFont("menlo,consolas,helvetica", 28, bold=True),
            "ui": pygame.font.SysFont("menlo,consolas,helvetica", 15, bold=True),
            "small": pygame.font.SysFont("menlo,consolas,helvetica", 12, bold=True),
            "tiny": pygame.font.SysFont("menlo,consolas,helvetica", 10),
            "pad": pygame.font.SysFont("menlo,consolas,helvetica", 11, bold=True),
        }
        self.particles: List[dict] = []
        self.flash: List[float] = [0.0] * NUM_TRACKS  # pad hit glow decay
        self.step_flash = 0.0
        self._last_step_time = 0.0
        self._accum = 0.0
        self._running = True
        self._export_dir = Path(__file__).resolve().parent / "exports"
        self._export_dir.mkdir(exist_ok=True)

        # Dropdowns: rhythm + sample kit
        self.dropdown_open = False  # rhythm
        self.kit_dropdown_open = False
        self.dropdown_hover = -1
        self.kit_dropdown_hover = -1
        self.dropdown_item_h = 30

        # Layout
        self.margin = 24
        self.top_bar_h = 72
        self.transport_h = 64
        self.bottom_h = 48
        self.track_label_w = 110
        self.ctrl_w = 72  # mute/solo

        self._layout()

    def _layout(self) -> None:
        self.grid_x = self.margin + self.track_label_w + self.ctrl_w
        self.grid_y = self.top_bar_h + self.transport_h + 12
        self.grid_w = self.w - self.grid_x - self.margin
        self.grid_h = self.h - self.grid_y - self.bottom_h - self.margin
        self.cell_w = self.grid_w / STEPS
        self.cell_h = self.grid_h / NUM_TRACKS
        self.pad_rects: List[List[pygame.Rect]] = []
        pad_pad = 3
        for ti in range(NUM_TRACKS):
            row = []
            for si in range(STEPS):
                x = self.grid_x + si * self.cell_w + pad_pad
                y = self.grid_y + ti * self.cell_h + pad_pad
                row.append(
                    pygame.Rect(int(x), int(y), int(self.cell_w - pad_pad * 2), int(self.cell_h - pad_pad * 2))
                )
            self.pad_rects.append(row)

        # Transport buttons
        by = self.top_bar_h + 14
        self.btn_play = pygame.Rect(self.margin, by, 100, 36)
        self.btn_stop = pygame.Rect(self.margin + 110, by, 80, 36)
        self.btn_clear = pygame.Rect(self.margin + 200, by, 80, 36)
        self.btn_save = pygame.Rect(self.margin + 290, by, 110, 36)
        # Rhythm + sample kit dropdowns
        self.dropdown_w = 168
        self.kit_dropdown_w = 168
        self.btn_rhythm = pygame.Rect(self.margin + 410, by, self.dropdown_w, 36)
        self.btn_kit = pygame.Rect(self.margin + 588, by, self.kit_dropdown_w, 36)
        self.bpm_minus = pygame.Rect(self.w - self.margin - 200, by, 36, 36)
        self.bpm_plus = pygame.Rect(self.w - self.margin - 36, by, 36, 36)
        self.bpm_rect = pygame.Rect(self.w - self.margin - 158, by, 116, 36)
        self._layout_dropdown_items()

        # Mute / solo hit zones
        self.mute_rects: List[pygame.Rect] = []
        self.solo_rects: List[pygame.Rect] = []
        for ti in range(NUM_TRACKS):
            y = self.grid_y + ti * self.cell_h + self.cell_h / 2 - 12
            mx = self.margin + self.track_label_w
            self.mute_rects.append(pygame.Rect(int(mx), int(y), 28, 24))
            self.solo_rects.append(pygame.Rect(int(mx + 32), int(y), 28, 24))

    def _layout_dropdown_items(self) -> None:
        self.dropdown_item_rects: List[pygame.Rect] = []
        x, y = self.btn_rhythm.x, self.btn_rhythm.bottom + 2
        for i in range(len(RHYTHM_PRESETS)):
            self.dropdown_item_rects.append(
                pygame.Rect(x, y + i * self.dropdown_item_h, self.dropdown_w, self.dropdown_item_h)
            )
        n = len(RHYTHM_PRESETS)
        self.dropdown_panel = pygame.Rect(
            x, y, self.dropdown_w, n * self.dropdown_item_h + 4
        )

        self.kit_item_rects: List[pygame.Rect] = []
        kx, ky = self.btn_kit.x, self.btn_kit.bottom + 2
        for i in range(len(self.kits)):
            self.kit_item_rects.append(
                pygame.Rect(kx, ky + i * self.dropdown_item_h, self.kit_dropdown_w, self.dropdown_item_h)
            )
        kn = max(1, len(self.kits))
        self.kit_dropdown_panel = pygame.Rect(
            kx, ky, self.kit_dropdown_w, kn * self.dropdown_item_h + 4
        )

    def _current_rhythm_label(self) -> str:
        idx = max(0, min(self.state.rhythm_index, len(RHYTHM_PRESETS) - 1))
        return RHYTHM_PRESETS[idx]["label"]

    def _current_kit_label(self) -> str:
        if not self.kits:
            return "SYNTH"
        idx = max(0, min(self.state.kit_index, len(self.kits) - 1))
        return self.kits[idx].label

    def _load_rhythm(self, index: int) -> None:
        if index < 0 or index >= len(RHYTHM_PRESETS):
            return
        preset = RHYTHM_PRESETS[index]
        self.state.rhythm_index = index
        self.state.pattern = clone_pattern(preset["pattern"])
        self.state.bpm = float(preset["bpm"])
        self.state.swing = float(preset["swing"])
        self.state.step = 0
        self._accum = 0.0
        self.dropdown_open = False
        swing_pct = int(self.state.swing * 100)
        self.state.status = (
            f"Loaded {preset['label']}  ·  {self.state.bpm:.0f} BPM"
            + (f"  ·  swing {swing_pct}%" if swing_pct else "")
        )
        if self.state.playing:
            self._trigger_step(0)

    def _load_kit(self, index: int) -> None:
        if index < 0 or index >= len(self.kits):
            return
        info = self.kits[index]
        self.state.kit_index = index
        self.kit_dropdown_open = False
        self.dropdown_open = False
        try:
            self.kit = build_kit_for(info)
            self.state.status = f"Sample kit: {info.label}"
            # audition kick
            if "KICK" in self.kit:
                self.kit["KICK"].set_volume(0.85)
                self.kit["KICK"].play()
                self.flash[0] = 1.0
        except Exception as e:
            self.state.status = f"Kit load failed: {e}"

    # ── Audio / timing ────────────────────────────────────────────────────
    def _step_duration(self) -> float:
        # 16th note duration
        base = 60.0 / self.state.bpm / 4.0
        return base

    def _should_play_track(self, ti: int) -> bool:
        if any(self.state.solo):
            return self.state.solo[ti] and not self.state.mute[ti]
        return not self.state.mute[ti]

    def _trigger_step(self, step: int) -> None:
        self.step_flash = 1.0
        for ti, drum in enumerate(DRUM_DEFS):
            vel = self.state.pattern[ti][step]
            if vel <= 0 or not self._should_play_track(ti):
                continue
            sound = self.kit[drum["name"]]
            # volume tiers
            vol = 0.35 + 0.16 * vel
            sound.set_volume(min(1.0, vol))
            sound.play()
            self.flash[ti] = 1.0
            # particles
            rect = self.pad_rects[ti][step]
            col = drum["color"]
            for _ in range(4 + vel):
                self.particles.append(
                    {
                        "x": rect.centerx + random.uniform(-8, 8),
                        "y": rect.centery + random.uniform(-8, 8),
                        "vx": random.uniform(-60, 60),
                        "vy": random.uniform(-90, -20),
                        "life": random.uniform(0.25, 0.55),
                        "col": col,
                    }
                )

    def _update_transport(self, dt: float) -> None:
        if not self.state.playing:
            return
        step_dur = self._step_duration()
        # simple swing: delay odd steps
        if self.state.step % 2 == 1:
            step_dur *= 1.0 + self.state.swing
        else:
            step_dur *= 1.0 - self.state.swing * 0.5

        self._accum += dt
        while self._accum >= step_dur:
            self._accum -= step_dur
            self.state.step = (self.state.step + 1) % STEPS
            self._trigger_step(self.state.step)

    # ── Input ─────────────────────────────────────────────────────────────
    def _cycle_pad(self, ti: int, si: int, reverse: bool = False) -> None:
        cur = self.state.pattern[ti][si]
        if reverse:
            self.state.pattern[ti][si] = (cur - 1) % 5
        else:
            self.state.pattern[ti][si] = (cur + 1) % 5
        # audition
        if self.state.pattern[ti][si] > 0:
            s = self.kit[DRUM_DEFS[ti]["name"]]
            s.set_volume(0.35 + 0.16 * self.state.pattern[ti][si])
            s.play()
            self.flash[ti] = 0.7

    def _handle_click(self, pos: Tuple[int, int], button: int) -> None:
        # Kit dropdown priority
        if self.kit_dropdown_open:
            for i, rect in enumerate(self.kit_item_rects):
                if rect.collidepoint(pos):
                    self._load_kit(i)
                    return
            if self.btn_kit.collidepoint(pos):
                self.kit_dropdown_open = False
                return
            self.kit_dropdown_open = False
            # fall through

        # Rhythm dropdown priority
        if self.dropdown_open:
            for i, rect in enumerate(self.dropdown_item_rects):
                if rect.collidepoint(pos):
                    self._load_rhythm(i)
                    return
            if self.btn_rhythm.collidepoint(pos):
                self.dropdown_open = False
                return
            self.dropdown_open = False
            # fall through

        if self.btn_kit.collidepoint(pos):
            self.kit_dropdown_open = not self.kit_dropdown_open
            self.dropdown_open = False
            return
        if self.btn_rhythm.collidepoint(pos):
            self.dropdown_open = not self.dropdown_open
            self.kit_dropdown_open = False
            return

        # pads
        for ti in range(NUM_TRACKS):
            for si in range(STEPS):
                if self.pad_rects[ti][si].collidepoint(pos):
                    self._cycle_pad(ti, si, reverse=(button == 3))
                    return
            if self.mute_rects[ti].collidepoint(pos):
                self.state.mute[ti] = not self.state.mute[ti]
                return
            if self.solo_rects[ti].collidepoint(pos):
                self.state.solo[ti] = not self.state.solo[ti]
                return

        if self.btn_play.collidepoint(pos):
            self._toggle_play()
        elif self.btn_stop.collidepoint(pos):
            self._stop()
        elif self.btn_clear.collidepoint(pos):
            self.state.pattern = [[0] * STEPS for _ in range(NUM_TRACKS)]
            self.state.status = "Pattern cleared"
        elif self.btn_save.collidepoint(pos):
            self._save_midi()
        elif self.bpm_minus.collidepoint(pos):
            self.state.bpm = max(40.0, self.state.bpm - (5 if pygame.key.get_mods() & pygame.KMOD_SHIFT else 1))
        elif self.bpm_plus.collidepoint(pos):
            self.state.bpm = min(220.0, self.state.bpm + (5 if pygame.key.get_mods() & pygame.KMOD_SHIFT else 1))

    def _toggle_play(self) -> None:
        if self.state.playing:
            self.state.playing = False
            self.state.status = "Stopped"
        else:
            self.state.playing = True
            self._accum = 0.0
            # trigger current step immediately
            self._trigger_step(self.state.step)
            self.state.status = f"Playing @ {self.state.bpm:.0f} BPM"

    def _stop(self) -> None:
        self.state.playing = False
        self.state.step = 0
        self._accum = 0.0
        self.state.status = "Stopped · head at 1"

    def _save_midi(self) -> None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self._export_dir / f"drumseq_{ts}.mid"
        names = [d["name"] for d in DRUM_DEFS]
        pattern_to_midi(self.state.pattern, self.state.bpm, STEPS, path, names)
        self.state.last_saved = str(path)
        self.state.status = f"Saved MIDI → {path.name}"

    def _handle_key(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            if self.dropdown_open or self.kit_dropdown_open:
                self.dropdown_open = False
                self.kit_dropdown_open = False
            else:
                self._running = False
            return
        if key == pygame.K_q:
            self._running = False
        elif key == pygame.K_SPACE:
            self._toggle_play()
        elif key == pygame.K_s:
            self._save_midi()
        elif key == pygame.K_r:
            self._stop()
        elif key == pygame.K_c:
            self.state.pattern = [[0] * STEPS for _ in range(NUM_TRACKS)]
            self.state.status = "Pattern cleared"
        elif key == pygame.K_d:
            self._load_rhythm(0)  # demo groove
        elif key == pygame.K_k:
            # cycle sample kits
            if self.kits:
                self._load_kit((self.state.kit_index + 1) % len(self.kits))
        elif key == pygame.K_TAB:
            self.dropdown_open = not self.dropdown_open
            self.kit_dropdown_open = False
        elif key == pygame.K_F2:
            self.kit_dropdown_open = not self.kit_dropdown_open
            self.dropdown_open = False
        elif key == pygame.K_UP and self.dropdown_open:
            ni = (self.state.rhythm_index - 1) % len(RHYTHM_PRESETS)
            self._load_rhythm(ni)
            self.dropdown_open = True
        elif key == pygame.K_DOWN and self.dropdown_open:
            ni = (self.state.rhythm_index + 1) % len(RHYTHM_PRESETS)
            self._load_rhythm(ni)
            self.dropdown_open = True
        elif key == pygame.K_UP and self.kit_dropdown_open:
            self._load_kit((self.state.kit_index - 1) % len(self.kits))
            self.kit_dropdown_open = True
        elif key == pygame.K_DOWN and self.kit_dropdown_open:
            self._load_kit((self.state.kit_index + 1) % len(self.kits))
            self.kit_dropdown_open = True
        elif key == pygame.K_RETURN and (self.dropdown_open or self.kit_dropdown_open):
            self.dropdown_open = False
            self.kit_dropdown_open = False
        elif pygame.K_1 <= key <= pygame.K_8:
            self._load_rhythm(key - pygame.K_1)
        elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self.state.bpm = min(220.0, self.state.bpm + 1)
        elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.state.bpm = max(40.0, self.state.bpm - 1)
        elif key == pygame.K_LEFT:
            self.state.step = (self.state.step - 1) % STEPS
        elif key == pygame.K_RIGHT:
            self.state.step = (self.state.step + 1) % STEPS
        elif key == pygame.K_LEFTBRACKET:
            self.state.swing = max(0.0, self.state.swing - 0.05)
            self.state.status = f"Swing {self.state.swing * 100:.0f}%"
        elif key == pygame.K_RIGHTBRACKET:
            self.state.swing = min(0.4, self.state.swing + 0.05)
            self.state.status = f"Swing {self.state.swing * 100:.0f}%"

    # ── Drawing helpers ───────────────────────────────────────────────────
    def _draw_rounded(self, rect: pygame.Rect, color, radius: int = 6, width: int = 0) -> None:
        pygame.draw.rect(self.screen, color, rect, width, border_radius=radius)

    def _button(self, rect: pygame.Rect, label: str, active: bool = False, color=None) -> None:
        base = color or (ACCENT if active else PANEL2)
        border = ACCENT if active else (70, 70, 100)
        self._draw_rounded(rect, base, 8)
        self._draw_rounded(rect, border, 8, 2)
        txt = self.fonts["ui"].render(label, True, BG if active and color is None else TEXT)
        self.screen.blit(txt, txt.get_rect(center=rect.center))

    def _draw_scanlines(self) -> None:
        overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        for y in range(0, self.h, 3):
            pygame.draw.line(overlay, (0, 0, 0, 28), (0, y), (self.w, y))
        # vignette corners
        self.screen.blit(overlay, (0, 0))

    def _draw_header(self) -> None:
        # top bar
        bar = pygame.Rect(0, 0, self.w, self.top_bar_h)
        self._draw_rounded(bar, PANEL, 0)
        pygame.draw.line(self.screen, ACCENT, (0, self.top_bar_h - 1), (self.w, self.top_bar_h - 1), 2)

        title = self.fonts["title"].render("DRUMSEQ", True, ACCENT)
        self.screen.blit(title, (self.margin, 18))
        sub = self.fonts["small"].render("RETRO RACK  ·  ABLETON-STYLE STEP SEQUENCER", True, ACCENT2)
        self.screen.blit(sub, (self.margin + title.get_width() + 16, 28))

        # live LED
        led_col = GLOW_PLAY if self.state.playing else (60, 60, 80)
        pygame.draw.circle(self.screen, led_col, (self.w - self.margin - 12, 36), 8)
        if self.state.playing:
            pygame.draw.circle(self.screen, (180, 255, 220), (self.w - self.margin - 12, 36), 4)

    def _draw_transport(self) -> None:
        y0 = self.top_bar_h
        pygame.draw.rect(self.screen, (12, 12, 20), (0, y0, self.w, self.transport_h))

        self._button(self.btn_play, "▶ PLAY" if not self.state.playing else "⏸ PAUSE", self.state.playing)
        self._button(self.btn_stop, "■ STOP")
        self._button(self.btn_clear, "CLEAR")
        self._button(self.btn_save, "💾 MIDI", color=(40, 80, 70))
        self._draw_dropdown_header(self.btn_rhythm, self._current_rhythm_label(), self.dropdown_open, "RHYTHM")
        self._draw_dropdown_header(self.btn_kit, self._current_kit_label(), self.kit_dropdown_open, "SAMPLES")

        self._button(self.bpm_minus, "−")
        self._button(self.bpm_plus, "+")
        self._draw_rounded(self.bpm_rect, PANEL2, 8)
        self._draw_rounded(self.bpm_rect, (70, 70, 100), 8, 1)
        bpm_txt = self.fonts["ui"].render(f"{self.state.bpm:.0f} BPM", True, ACCENT)
        self.screen.blit(bpm_txt, bpm_txt.get_rect(center=self.bpm_rect.center))

    def _draw_dropdown_header(self, rect: pygame.Rect, label: str, active: bool, caption: str) -> None:
        base = (30, 40, 70) if active else PANEL2
        border = ACCENT if active else (70, 70, 100)
        if caption == "SAMPLES" and active:
            border = ACCENT2
        self._draw_rounded(rect, base, 8)
        self._draw_rounded(rect, border, 8, 2)
        arrow = "▲" if active else "▼"
        col = ACCENT if active else TEXT
        txt = self.fonts["small"].render(f"{label} {arrow}", True, col)
        if txt.get_width() > rect.w - 14:
            # truncate label
            short = label[:12] + "…" if len(label) > 12 else label
            txt = self.fonts["small"].render(f"{short} {arrow}", True, col)
        self.screen.blit(txt, txt.get_rect(midleft=(rect.x + 8, rect.centery)))
        cap = self.fonts["tiny"].render(caption, True, MUTED)
        self.screen.blit(cap, (rect.x + 8, rect.y - 12))

    def _draw_list_dropdown(
        self,
        panel: pygame.Rect,
        item_rects: List[pygame.Rect],
        labels: List[str],
        metas: List[str],
        selected: int,
        accent_col=ACCENT,
    ) -> int:
        shadow = panel.inflate(6, 6)
        sh = pygame.Surface(shadow.size, pygame.SRCALPHA)
        sh.fill((0, 0, 0, 100))
        self.screen.blit(sh, shadow.topleft)
        self._draw_rounded(panel, DROPDOWN_BG, 8)
        self._draw_rounded(panel, accent_col, 8, 2)

        mx, my = pygame.mouse.get_pos()
        hover = -1
        for i, rect in enumerate(item_rects):
            is_sel = i == selected
            is_hov = rect.collidepoint(mx, my)
            if is_hov:
                hover = i
            if is_sel:
                fill = DROPDOWN_SEL if accent_col == ACCENT else (90, 30, 70)
            elif is_hov:
                fill = DROPDOWN_HOVER
            else:
                fill = DROPDOWN_BG
            inner = rect.inflate(-4, -2)
            self._draw_rounded(inner, fill, 4)
            col = accent_col if is_sel or is_hov else TEXT
            label = self.fonts["small"].render(labels[i], True, col)
            self.screen.blit(label, (rect.x + 10, rect.centery - label.get_height() // 2))
            if i < len(metas) and metas[i]:
                meta = self.fonts["tiny"].render(metas[i], True, MUTED)
                self.screen.blit(
                    meta, (rect.right - meta.get_width() - 8, rect.centery - meta.get_height() // 2)
                )
        return hover

    def _draw_rhythm_dropdown_menu(self) -> None:
        if not self.dropdown_open:
            return
        labels = [p["label"] for p in RHYTHM_PRESETS]
        metas = [f"{p['bpm']:.0f}" for p in RHYTHM_PRESETS]
        self.dropdown_hover = self._draw_list_dropdown(
            self.dropdown_panel,
            self.dropdown_item_rects,
            labels,
            metas,
            self.state.rhythm_index,
            ACCENT,
        )

    def _draw_kit_dropdown_menu(self) -> None:
        if not self.kit_dropdown_open:
            return
        labels = [k.label for k in self.kits]
        metas = []
        for k in self.kits:
            if k.kind == "synth":
                metas.append("PCM")
            elif k.kind == "st":
                metas.append("8SVX")
            elif k.kind == "mod":
                metas.append("MOD")
            else:
                metas.append("DIR")
        self.kit_dropdown_hover = self._draw_list_dropdown(
            self.kit_dropdown_panel,
            self.kit_item_rects,
            labels,
            metas,
            self.state.kit_index,
            ACCENT2,
        )

    def _draw_grid(self) -> None:
        # background panel
        panel = pygame.Rect(
            self.margin - 4,
            self.grid_y - 8,
            self.w - 2 * self.margin + 8,
            self.grid_h + 16,
        )
        self._draw_rounded(panel, PANEL, 12)
        self._draw_rounded(panel, (40, 40, 70), 12, 1)

        for ti, drum in enumerate(DRUM_DEFS):
            y = self.grid_y + ti * self.cell_h
            # alternating row tint
            if ti % 2 == 0:
                row_bg = pygame.Rect(self.grid_x, int(y), int(self.grid_w), int(self.cell_h))
                s = pygame.Surface((row_bg.w, row_bg.h), pygame.SRCALPHA)
                s.fill((255, 255, 255, 6))
                self.screen.blit(s, row_bg)

            # track color strip + label
            strip = pygame.Rect(self.margin, int(y + 4), 6, int(self.cell_h - 8))
            self._draw_rounded(strip, drum["color"], 3)
            name = self.fonts["ui"].render(drum["name"], True, TEXT)
            self.screen.blit(name, (self.margin + 14, int(y + self.cell_h / 2 - name.get_height() / 2)))

            # mute / solo
            mcol = ACCENT2 if self.state.mute[ti] else PANEL2
            scol = ACCENT if self.state.solo[ti] else PANEL2
            self._draw_rounded(self.mute_rects[ti], mcol, 4)
            self._draw_rounded(self.solo_rects[ti], scol, 4)
            mt = self.fonts["tiny"].render("M", True, TEXT)
            st = self.fonts["tiny"].render("S", True, TEXT)
            self.screen.blit(mt, mt.get_rect(center=self.mute_rects[ti].center))
            self.screen.blit(st, st.get_rect(center=self.solo_rects[ti].center))

            # hit flash on label
            if self.flash[ti] > 0:
                glow = pygame.Surface((self.track_label_w, int(self.cell_h)), pygame.SRCALPHA)
                a = int(80 * self.flash[ti])
                glow.fill((*drum["color"], a))
                self.screen.blit(glow, (self.margin, int(y)))

            for si in range(STEPS):
                rect = self.pad_rects[ti][si]
                vel = self.state.pattern[ti][si]
                is_beat = si % 4 == 0
                is_playhead = self.state.playing and si == self.state.step

                # empty pad
                if vel == 0:
                    base = (28, 28, 42) if is_beat else (20, 20, 32)
                    self._draw_rounded(rect, base, 5)
                    border = BEAT_LINE if is_beat else GRID_LINE
                    self._draw_rounded(rect, border, 5, 1)
                else:
                    col = drum["color"]
                    # velocity → brightness
                    factor = 0.35 + 0.16 * vel
                    fill = tuple(min(255, int(c * factor + 40)) for c in col)
                    self._draw_rounded(rect, fill, 5)
                    # inner brightness tier
                    inner = rect.inflate(-6, -6)
                    if inner.w > 0 and inner.h > 0:
                        bright = tuple(min(255, int(c * (0.5 + 0.12 * vel))) for c in col)
                        self._draw_rounded(inner, bright, 3)
                    self._draw_rounded(rect, (255, 255, 255), 5, 1)

                # playhead highlight
                if is_playhead:
                    glow_rect = rect.inflate(2, 2)
                    self._draw_rounded(glow_rect, PLAYHEAD, 6, 2)
                    if vel > 0:
                        flash_s = pygame.Surface(rect.size, pygame.SRCALPHA)
                        flash_s.fill((255, 255, 255, int(60 * self.step_flash)))
                        self.screen.blit(flash_s, rect)

            # step numbers (top only)
            if ti == 0:
                for si in range(STEPS):
                    cx = self.pad_rects[0][si].centerx
                    num = self.fonts["tiny"].render(str(si + 1), True, MUTED if si % 4 else ACCENT)
                    self.screen.blit(num, (cx - num.get_width() // 2, self.grid_y - 16))

        # playhead vertical line
        if self.state.playing or True:
            px = self.grid_x + self.state.step * self.cell_w + self.cell_w / 2
            col = GLOW_PLAY if self.state.playing else (80, 80, 100)
            pygame.draw.line(
                self.screen,
                col,
                (int(px), self.grid_y),
                (int(px), self.grid_y + self.grid_h),
                2,
            )

    def _draw_particles(self, dt: float) -> None:
        alive = []
        for p in self.particles:
            p["life"] -= dt
            if p["life"] <= 0:
                continue
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vy"] += 180 * dt
            a = max(0, min(255, int(255 * (p["life"] / 0.5))))
            r = max(1, int(3 * p["life"] / 0.4))
            # pygame circle no alpha easily — approximate
            pygame.draw.circle(self.screen, p["col"], (int(p["x"]), int(p["y"])), r)
            alive.append(p)
        self.particles = alive

    def _draw_footer(self) -> None:
        y = self.h - self.bottom_h
        pygame.draw.rect(self.screen, PANEL, (0, y, self.w, self.bottom_h))
        pygame.draw.line(self.screen, ACCENT2, (0, y), (self.w, y), 1)
        status = self.fonts["small"].render(self.state.status, True, TEXT)
        self.screen.blit(status, (self.margin, y + 16))
        help_txt = self.fonts["tiny"].render(
            "SAMPLES F2/K · RHYTHM Tab/1-8 · LMB pad · SPACE play · S MIDI · C clear · [ ] swing · +/- bpm · Q quit",
            True,
            MUTED,
        )
        self.screen.blit(help_txt, (self.margin, y + 32))
        rhythm = self._current_rhythm_label()
        kit = self._current_kit_label()
        step_info = self.fonts["small"].render(
            f"{kit}  ·  {rhythm}  ·  STEP {self.state.step + 1:02d}/{STEPS}  SW {self.state.swing * 100:.0f}%",
            True,
            ACCENT,
        )
        self.screen.blit(step_info, (self.w - self.margin - step_info.get_width(), y + 18))

    def run(self) -> None:
        # auto-start current rhythm
        self.state.playing = True
        self._accum = 0.0
        self._trigger_step(0)
        self.state.status = (
            f"{self._current_kit_label()} · {self._current_rhythm_label()} — "
            "SAMPLES menu = Amiga ST-xx / MOD · S = MIDI"
        )

        prev = time.perf_counter()
        while self._running:
            now = time.perf_counter()
            dt = min(0.05, now - prev)
            prev = now

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                elif event.type == pygame.KEYDOWN:
                    self._handle_key(event.key)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
                    self._handle_click(event.pos, event.button)
                elif event.type == pygame.MOUSEWHEEL and self.dropdown_open:
                    if event.y > 0:
                        ni = (self.state.rhythm_index - 1) % len(RHYTHM_PRESETS)
                    elif event.y < 0:
                        ni = (self.state.rhythm_index + 1) % len(RHYTHM_PRESETS)
                    else:
                        ni = self.state.rhythm_index
                    self._load_rhythm(ni)
                    self.dropdown_open = True
                elif event.type == pygame.MOUSEWHEEL and self.kit_dropdown_open and self.kits:
                    if event.y > 0:
                        ni = (self.state.kit_index - 1) % len(self.kits)
                    elif event.y < 0:
                        ni = (self.state.kit_index + 1) % len(self.kits)
                    else:
                        ni = self.state.kit_index
                    self._load_kit(ni)
                    self.kit_dropdown_open = True
                elif event.type == pygame.VIDEORESIZE:
                    self.w, self.h = event.size
                    self.screen = pygame.display.set_mode((self.w, self.h), pygame.RESIZABLE)
                    self._layout()

            self._update_transport(dt)
            # decay flashes
            for i in range(NUM_TRACKS):
                self.flash[i] = max(0.0, self.flash[i] - dt * 4)
            self.step_flash = max(0.0, self.step_flash - dt * 6)

            self.screen.fill(BG)
            # subtle bg grid
            for x in range(0, self.w, 40):
                pygame.draw.line(self.screen, (14, 14, 24), (x, 0), (x, self.h))
            for y in range(0, self.h, 40):
                pygame.draw.line(self.screen, (14, 14, 24), (0, y), (self.w, y))

            self._draw_header()
            self._draw_transport()
            self._draw_grid()
            self._draw_particles(dt)
            self._draw_footer()
            self._draw_rhythm_dropdown_menu()  # on top of grid
            self._draw_kit_dropdown_menu()
            self._draw_scanlines()

            # outer neon frame
            pygame.draw.rect(self.screen, ACCENT, self.screen.get_rect().inflate(-4, -4), 1)

            pygame.display.flip()
            self.clock.tick(60)
