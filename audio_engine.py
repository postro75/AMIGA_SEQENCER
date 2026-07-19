"""Audio playback engine with pygame.mixer or sounddevice fallback."""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np

SAMPLE_RATE = 44100


class Sound:
    """Simple sound buffer with volume + non-blocking play."""

    def __init__(self, wave: np.ndarray, engine: "AudioEngine"):
        # mono float32 -1..1
        if wave.ndim > 1:
            wave = wave.mean(axis=1)
        self.wave = np.ascontiguousarray(wave.astype(np.float32))
        self.engine = engine
        self.volume = 1.0
        self._pg = None  # optional pygame Sound

    def set_volume(self, v: float) -> None:
        self.volume = float(max(0.0, min(1.0, v)))
        if self._pg is not None:
            self._pg.set_volume(self.volume)

    def play(self) -> None:
        if self._pg is not None:
            self._pg.set_volume(self.volume)
            self._pg.play()
            return
        self.engine.play_wave(self.wave, self.volume)


class AudioEngine:
    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.backend = "silent"
        self._pg_ok = False
        self._sd = None
        self._stream = None
        self._lock_buf: Optional[np.ndarray] = None
        self._write_pos = 0
        self._buffer_seconds = 2.0
        self._ring: Optional[np.ndarray] = None
        self._ring_len = 0
        self._play_pos = 0
        self._active = False

        # Prefer pygame.mixer when available
        try:
            import pygame

            # Accessing pygame.mixer may raise NotImplementedError on broken builds
            mixer = getattr(pygame, "mixer", None)
            if mixer is not None:
                try:
                    import pygame.mixer as _m  # noqa: F401

                    if not pygame.mixer.get_init():
                        pygame.mixer.init(sample_rate, -16, 2, 512)
                    self._pg_ok = True
                    self.backend = "pygame"
                except Exception:
                    self._pg_ok = False
        except Exception:
            self._pg_ok = False

        if not self._pg_ok:
            try:
                import sounddevice as sd

                self._sd = sd
                self._ring_len = int(self._buffer_seconds * sample_rate)
                self._ring = np.zeros((self._ring_len, 2), dtype=np.float32)
                self._play_pos = 0

                def callback(outdata, frames, time_info, status):  # noqa: ARG001
                    if self._ring is None:
                        outdata.fill(0)
                        return
                    end = self._play_pos + frames
                    if end <= self._ring_len:
                        chunk = self._ring[self._play_pos : end].copy()
                        self._ring[self._play_pos : end] = 0
                    else:
                        first = self._ring_len - self._play_pos
                        chunk = np.vstack(
                            [
                                self._ring[self._play_pos :].copy(),
                                self._ring[: end % self._ring_len].copy(),
                            ]
                        )
                        self._ring[self._play_pos :] = 0
                        self._ring[: end % self._ring_len] = 0
                    self._play_pos = end % self._ring_len
                    # soft clip
                    np.clip(chunk, -1.0, 1.0, out=chunk)
                    outdata[:] = chunk

                self._stream = sd.OutputStream(
                    samplerate=sample_rate,
                    channels=2,
                    dtype="float32",
                    callback=callback,
                    blocksize=512,
                )
                self._stream.start()
                self.backend = "sounddevice"
                self._active = True
            except Exception as e:
                print(f"[audio] sounddevice unavailable ({e}); running silent")
                self.backend = "silent"

    def make_sound(self, wave: np.ndarray) -> Sound:
        snd = Sound(wave, self)
        if self._pg_ok:
            import pygame

            w = np.clip(wave, -1.0, 1.0)
            if w.ndim == 1:
                pcm = (w * 32767).astype(np.int16)
                stereo = np.column_stack([pcm, pcm])
            else:
                stereo = (w * 32767).astype(np.int16)
            snd._pg = pygame.sndarray.make_sound(np.ascontiguousarray(stereo))
        return snd

    def play_wave(self, wave: np.ndarray, volume: float = 1.0) -> None:
        if self._pg_ok:
            # handled via Sound._pg when present; still support raw
            import pygame

            w = np.clip(wave * volume, -1.0, 1.0)
            pcm = (w * 32767).astype(np.int16)
            stereo = np.column_stack([pcm, pcm])
            pygame.sndarray.make_sound(np.ascontiguousarray(stereo)).play()
            return

        if self.backend != "sounddevice" or self._ring is None:
            return

        mono = wave.astype(np.float32) * float(volume)
        n = len(mono)
        # mix into ring at current playhead + small latency pad
        start = (self._play_pos + 256) % self._ring_len
        for ch in (0, 1):
            if start + n <= self._ring_len:
                self._ring[start : start + n, ch] += mono
            else:
                first = self._ring_len - start
                self._ring[start:, ch] += mono[:first]
                self._ring[: n - first, ch] += mono[first:]

    def close(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None


# Module-level singleton used by synth/app
_ENGINE: Optional[AudioEngine] = None


def get_engine() -> AudioEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = AudioEngine()
    return _ENGINE


def shutdown_engine() -> None:
    global _ENGINE
    if _ENGINE is not None:
        _ENGINE.close()
        _ENGINE = None
