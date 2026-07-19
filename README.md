# DRUMSEQ — Retro Rack

Perkusyjny **step sequencer** w Pythonie z:

- intro w stylu **Atari / demoscene** (starfield, plasma, copper bars, scroller, chip beeps)
- UI wzorowanym na **Ableton** (tracki, pady 16 kroków, mute/solo, playhead, transport)
- estetyką **retro neon + CRT scanlines**
- **proceduralnymi** bębnami **oraz oryginalnymi samplami Amiga ST-xx** (IFF 8SVX)
- odczytem instrumentów z plików **ProTracker .MOD**
- **eksportem do pliku MIDI** (GM channel 10)

### Sample kit (Amiga)

Menu **SAMPLES** w UI:

| Źródło | Opis |
|--------|------|
| SYNTH | proceduralne bębny |
| **ST-01 / ST-02 / ST-03** | klasyczne dyski Soundtracker z Aminetu |
| **MOD:…** | instrumenty wyciągnięte z `.mod` w `samples/MOD/` |

Pobierz / odśwież dyski:

```bash
pip install lhafile
python fetch_amiga_samples.py            # ST-01..03 + demo MOD
python fetch_amiga_samples.py --disks 1,2,3,4,5
```

Źródła: [Aminet mods/inst](https://aminet.net/mods/inst), [Archive.org AmigaSTXX](https://archive.org/details/AmigaSTXX) (Public Domain Mark).  
Własne sample: wrzuć folder do `samples/` albo pliki `.mod` do `samples/MOD/`.

## Start

```bash
cd drum_sequencer
pip install -r requirements.txt   # uses pygame-ce (best on Python 3.12+)
python main.py
```

> Na Pythonie 3.14 zwykły `pygame` bywa bez `font`/`mixer` — dlatego w requirements jest **pygame-ce**.

Opcje:

```bash
python main.py --skip-demo      # od razu sequencer
python main.py --bpm 128
python main.py --demo-ms 12000  # dłuższe intro
```

## Sterowanie

| Akcja | Klawisz / mysz |
|--------|----------------|
| Play / Pause | `Space` lub przycisk PLAY |
| Stop (krok 1) | `R` lub STOP |
| Cykl velocity pada (0→1→2→3→4→0) | LPM |
| Cofnij velocity | PPM |
| Zapisz MIDI | `S` lub SAVE MIDI |
| Wyczyść pattern | `C` |
| Menu rytmów (dropdown) | klik **RHYTHM** / `Tab` |
| Preset 1–8 | klawisze `1`…`8` |
| Załaduj demo groove | `D` |
| BPM ±1 | `+` / `-` (Shift+klik ±5) |
| Swing | `[` / `]` |
| Mute / Solo track | przyciski **M** / **S** |
| Wyjście | `Q` / `Esc` (Esc zamyka też menu) |

### Presety gatunków

| # | Rytm | BPM | Swing |
|---|------|-----|-------|
| 1 | Demo Groove | 124 | — |
| 2 | Rock | 118 | — |
| 3 | Blues | 92 | 28% |
| 4 | Modern Pop | 120 | — |
| 5 | Disco 80s | 120 | — |
| 6 | Synthpop | 128 | — |
| 7 | Hip Hop | 90 | 18% |
| 8 | Rap / Trap | 140 | 8% |

## MIDI

Pliki lądują w `exports/drumseq_YYYYMMDD_HHMMSS.mid`.

- Format: Standard MIDI File Type 1  
- Kanał: **10** (GM drums)  
- Resolution: 480 PPQ, 16th-note grid  
- Velocity tiers: 55 / 80 / 100 / 127  

Mapa GM: Kick 36, Snare 38, Clap 39, Rim 37, CHH 42, OHH 46, Tom Lo 41, Tom Hi 45, Crash 49, Cowbell 56.

## Stack

- **pygame** — UI + demo visuals  
- **sounddevice** — audio (fallback gdy `pygame.mixer` niedostępny)  
- **numpy** — synteza bębnów  
- **mido** — zapis MIDI  

## Struktura

```
drum_sequencer/
  main.py          # entrypoint
  demo.py          # Atari intro
  app.py           # DAW UI + transport
  patterns.py      # classic genre presets
  synth.py         # procedural drums
  midi_export.py   # SMF writer
  exports/         # zapisane .mid
```
