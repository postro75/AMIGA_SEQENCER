# AMIGA_SEQENCER (DRUMSEQ — Retro Rack)

Perkusyjny **step sequencer** w Pythonie z brzmieniem Amigi, UI w stylu Ableton i retro demoscene intro.

[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## Features

- **Intro Atari / demoscene** — starfield, plasma, copper bars, scroller, chip beeps, CRT scanlines
- **UI Ableton-style** — 10 tracków × 16 kroków, velocity, mute/solo, playhead, transport
- **Sample kits Amiga ST-xx** — oryginalne dyski Soundtracker (IFF 8SVX) z Aminetu
- **ProTracker MOD** — ekstrakcja instrumentów z plików `.mod`
- **Synteza proceduralna** — fallback bez sampli
- **Presety gatunków** — Rock, Blues, Modern Pop, Disco 80s, Synthpop, Hip Hop, Rap/Trap
- **Eksport MIDI** — GM channel 10 (Standard MIDI File)

## Quick start

```bash
git clone https://github.com/postro75/AMIGA_SEQENCER.git
cd AMIGA_SEQENCER
pip install -r requirements.txt
python main.py
```

```bash
python main.py --skip-demo      # bez intro
python main.py --bpm 128
python main.py --demo-ms 12000  # długość intro (ms)
python main.py --width 1280 --height 800
```

> Na nowszych Pythonach (**3.12+**) używaj **pygame-ce** z `requirements.txt` — pełny `font` i `mixer` (zwykły wheel `pygame` bywa niekompletny).

## Sample kits (Amiga)

Menu **SAMPLES** w UI — wykrywa foldery `samples/ST-*` i pliki `.mod` automatycznie:

| Źródło | Opis |
|--------|------|
| SYNTH | proceduralne bębny |
| **ST-xx** | dyski Soundtracker w `samples/ST-01`, `ST-02`, … (dowolny numer) |
| **MOD:…** | instrumenty z każdego `.mod` w `samples/MOD/` |

W repo domyślnie są ST-01…03 (+ demo MOD). Kolejne dyski:

```bash
pip install lhafile
python fetch_amiga_samples.py                 # ST-01..03 + demo MOD
python fetch_amiga_samples.py --disks 1,2,3,4,5   # też ST-04, ST-05, …
```

Źródła: [Aminet mods/inst](https://aminet.net/mods/inst), [Archive.org AmigaSTXX](https://archive.org/details/AmigaSTXX) (Public Domain Mark).  
Własne sample: folder `samples/ST-NN/` albo `samples/MOD/*.mod` (albo inny podfolder w `samples/`).  
Zobacz też `samples/SOURCES.md`.

## Controls

| Akcja | Sterowanie |
|--------|------------|
| Play / Pause | `Space` |
| Stop (krok 1) | `R` |
| Velocity pada | LPM cykl / PPM wstecz |
| Zapisz MIDI | `S` (klawisz) |
| Clear pattern | `C` |
| Menu rytmów | **RHYTHM** / `Tab` / `1`–`8` |
| Menu kitów | **SAMPLES** / `F2` / `K` (cykl kitów) |
| BPM | `+` / `-` · Shift+klik przycisku ±5 |
| Swing | `[` / `]` |
| Mute / Solo track | **klik w przyciski M / S** przy nazwie tracka (nie skróty klawiszowe — `S` zapisuje MIDI) |
| Quit | `Q` / `Esc` (Esc zamyka też menu) |

### Genre presets

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

## MIDI export

Pliki: `exports/drumseq_YYYYMMDD_HHMMSS.mid`

- SMF Type 1, 480 PPQ, 16th grid  
- Kanał **10** (GM drums)  
- Velocity tiers: 55 / 80 / 100 / 127  

GM: Kick 36, Snare 38, Clap 39, Rim 37, CHH 42, OHH 46, Tom Lo 41, Tom Hi 45, Crash 49, Cowbell 56.

## Stack

| Lib | Rola |
|-----|------|
| pygame-ce | UI, demo, audio |
| sounddevice | fallback audio |
| numpy | synteza / resample |
| mido | MIDI |
| lhafile | rozpakowanie ST-xx z Aminetu |

## Layout

```
.
├── main.py                 # entrypoint
├── demo.py                 # Atari intro
├── app.py                  # DAW UI + transport + dropdowns
├── patterns.py             # genre presets
├── synth.py                # procedural drums
├── sample_kit.py           # ST / MOD kit loader
├── amiga_io.py             # IFF 8SVX + MOD instruments
├── midi_export.py          # SMF writer
├── audio_engine.py         # pygame / sounddevice
├── fetch_amiga_samples.py  # Aminet downloader
├── samples/
│   ├── ST-01/ ST-02/ …     # dowolne ST-xx
│   ├── MOD/
│   └── SOURCES.md
└── exports/
```

## License

MIT — kod aplikacji. Sample ST-xx: historyczne materiały demoscene / tracker (zob. `samples/SOURCES.md`).
