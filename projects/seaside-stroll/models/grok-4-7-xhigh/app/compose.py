"""Compose and render Seaside Stroll.

Original anime-style music for a walk by the water, in A major and 4/4.
The opening tempo is 88 BPM and eases to 72 BPM across the last four bars.
This script writes a Standard MIDI File, synthesizes it with NumPy
(no samples or soundfonts), and encodes an MP3 with ffmpeg.

Seeds, all NumPy PCG64 generators:
  47021  score timing and velocity
  47022  synthesis noise and reverb impulse
  47023  16-bit dither
"""

from __future__ import annotations

import json
import math
import re
import struct
import subprocess
import wave
import zlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SR = 44100
PPQ = 480
SWING = 14
BARS = 40
SCORE_SEED = 47021
RENDER_SEED = 47022
DITHER_SEED = 47023
TAIL = 2.8

APP = Path(__file__).resolve().parent
MIDI_PATH = APP / "seaside_stroll.mid"
MP3_PATH = APP / "seaside_stroll.mp3"
WAV_PATH = APP / "seaside_stroll.wav"
PNG_PATH = APP.parent / "screenshots" / "preview.png"

CH_FLUTE = 0
CH_GUITAR = 1
CH_EP = 2
CH_CELESTA = 3
CH_STRINGS = 4
CH_BASS = 5
CH_BOX = 6
CH_VIBE = 7
CH_DRUMS = 9

# Program, volume, pan. Pan 0 is left, 64 center, 127 right.
SETUP = {
    CH_FLUTE: (73, 104, 64),
    CH_GUITAR: (24, 88, 42),
    CH_EP: (4, 74, 86),
    CH_CELESTA: (8, 70, 98),
    CH_STRINGS: (48, 72, 64),
    CH_BASS: (33, 96, 64),
    CH_BOX: (10, 62, 34),
    CH_VIBE: (11, 66, 80),
}
DRUM_VOLUME = 80
DRUM_PAN = 64

NAMES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
PITCH_RE = re.compile(r"^([A-G])([#b]?)(-?\d)$")


def pitch(name: str) -> int:
    match = PITCH_RE.fullmatch(name)
    if not match:
        raise ValueError(f"bad pitch {name}")
    pc = NAMES[match.group(1)]
    accidental = match.group(2)
    if accidental == "#":
        pc += 1
    elif accidental == "b":
        pc -= 1
    midi = (int(match.group(3)) + 1) * 12 + pc
    if not 0 <= midi <= 127:
        raise ValueError(f"pitch out of range {name}")
    return midi


def ticks(bar: int, beat: float) -> int:
    return int(round((bar * 4 + beat) * PPQ))


def section(bar: int) -> str:
    if bar < 4:
        return "intro"
    if bar < 12:
        return "a"
    if bar < 20:
        return "b"
    if bar < 28:
        return "c"
    if bar < 36:
        return "a2"
    return "outro"


@dataclass
class Note:
    channel: int
    inst: str
    pitch: int
    start: int
    dur: int
    vel: int
    bar: int


def vlq(value: int) -> bytes:
    if value < 0:
        raise ValueError("negative vlq")
    out = [value & 0x7F]
    value >>= 7
    while value:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(out))


def meta(kind: int, payload: bytes = b"") -> bytes:
    return bytes([0xFF, kind]) + vlq(len(payload)) + payload


def meta_text(kind: int, text: str) -> bytes:
    return meta(kind, text.encode("utf-8"))


def meta_tempo(bpm: float) -> bytes:
    micros = int(round(60_000_000 / bpm))
    return meta(0x51, micros.to_bytes(3, "big"))


def read_vlq(data: bytes, pos: int) -> tuple[int, int]:
    value = 0
    for _ in range(4):
        byte = data[pos]
        pos += 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            return value, pos
    raise ValueError("bad vlq")


CHART_TEXT = """
Amaj9 Dmaj9 F#m7 Esus4|E
Amaj7 Dmaj7 F#m7 E
Amaj7 Dmaj7 F#m7 Amaj7
Amaj7 E9 F#m7 Dmaj7
Amaj7 C#m7 Bm7 E7
F#m9 Dmaj7 Bm7 E
C#m7 F#m7 Dmaj7 Esus4|E
Amaj7 Dmaj7 F#m7 E
Amaj7 Dmaj7 F#m7 Amaj7
Amaj7 Dmaj7 A/E A
"""

CHORDS = {
    "Amaj9": ("A2", ["A3", "C#4", "E4", "G#4", "B4"], ["C#4", "E4", "B4"], ["E4", "B4"]),
    "Dmaj9": ("D2", ["D3", "F#3", "A3", "C#4", "E4"], ["F#4", "A4", "C#5"], ["F#4", "C#5"]),
    "F#m7": ("F#2", ["F#3", "A3", "C#4", "E4", "A4"], ["A3", "C#4", "E4"], ["E4", "A4"]),
    "F#m9": ("F#2", ["F#3", "A3", "C#4", "E4", "G#4"], ["A3", "C#4", "G#4"], ["E4", "G#4"]),
    "Esus4": ("E2", ["E3", "A3", "B3", "E4", "A4"], ["A3", "B3", "E4"], ["E4", "A4"]),
    "E": ("E2", ["E3", "G#3", "B3", "E4", "G#4"], ["G#3", "B3", "E4"], ["E4", "B4"]),
    "E9": ("E2", ["E3", "G#3", "B3", "D4", "F#4"], ["G#3", "D4", "F#4"], ["D4", "F#4"]),
    "E7": ("E2", ["E3", "G#3", "B3", "D4"], ["G#3", "B3", "D4"], ["D4", "G#4"]),
    "Amaj7": ("A2", ["A3", "C#4", "E4", "G#4", "A4"], ["C#4", "E4", "G#4"], ["C#4", "G#4"]),
    "Dmaj7": ("D2", ["D3", "F#3", "A3", "C#4", "F#4"], ["F#3", "A3", "C#4"], ["A4", "C#5"]),
    "C#m7": ("C#2", ["C#3", "E3", "G#3", "B3", "E4"], ["E4", "G#4", "B4"], ["E4", "G#4"]),
    "Bm7": ("B1", ["B3", "D4", "F#4", "A4"], ["D4", "F#4", "A4"], ["D4", "F#4"]),
    "A/E": ("E2", ["A3", "C#4", "E4", "A4"], ["A3", "C#4", "E4"], ["C#4", "E4"]),
    "A": ("A2", ["A3", "C#4", "E4", "A4", "E5"], ["A3", "C#4", "E4"], ["E4", "A4"]),
}

# bar beat duration pitch velocity. "-" is a rest, kept so each bar sums to 4.
FLUTE_TEXT = """
4 0 1 E5 86
4 1 0.5 F#5 84
4 1.5 0.5 E5 82
4 2 1 C#5 84
4 3 1 B4 80
5 0 2 A4 78
5 2 1 - 0
5 3 0.5 C#5 76
5 3.5 0.5 D5 78
6 0 1 E5 88
6 1 1 A5 90
6 2 0.5 F#5 84
6 2.5 0.5 E5 82
6 3 1 C#5 84
7 0 1.5 B4 86
7 1.5 0.5 A4 80
7 2 2 G#4 82
8 0 1 C#5 84
8 1 0.5 D5 80
8 1.5 0.5 E5 82
8 2 1 F#5 86
8 3 1 E5 82
9 0 2 D5 84
9 2 1 C#5 80
9 3 1 B4 78
10 0 1 A4 80
10 1 1 C#5 84
10 2 0.5 E5 82
10 2.5 0.5 F#5 80
10 3 1 E5 82
11 0 0.5 D5 78
11 0.5 0.5 C#5 80
11 1 1 B4 76
11 2 2 A4 82
12 0 0.5 - 0
12 0.5 0.5 C#5 86
12 1 1 E5 90
12 2 2 A5 92
13 0 1 G#5 88
13 1 0.5 F#5 84
13 1.5 0.5 E5 82
13 2 1 D5 80
13 3 1 B4 78
14 0 1 C#5 86
14 1 0.5 E5 84
14 1.5 0.5 F#5 86
14 2 1 A5 90
14 3 1 F#5 84
15 0 2 E5 88
15 2 1 D5 82
15 3 1 C#5 80
16 0 0.5 E5 84
16 0.5 0.5 F#5 86
16 1 1 G#5 88
16 2 1 A5 90
16 3 1 E5 84
17 0 2 G#5 86
17 2 1 E5 82
17 3 1 C#5 80
18 0 1 D5 82
18 1 0.5 C#5 78
18 1.5 0.5 D5 80
18 2 1 F#5 84
18 3 1 B4 78
19 0 0.5 B4 76
19 0.5 0.5 C#5 78
19 1 1 B4 76
19 2 2 G#4 74
20 0 2 C#5 70
20 2 2 A4 68
21 0 1.5 D5 72
21 1.5 0.5 C#5 68
21 2 2 B4 66
22 0 1 B4 68
22 1 1 C#5 70
22 2 2 A4 66
23 0 2 G#4 66
23 2 2 B4 68
24 0 1 C#5 70
24 1 1 E5 72
24 2 2 G#4 64
25 0 2 A4 68
25 2 1 C#5 70
25 3 1 A4 66
26 0 1.5 D5 70
26 1.5 0.5 C#5 66
26 2 1 B4 64
26 3 1 A4 66
27 0 2 A4 68
27 2 2 G#4 66
28 0 1 E5 88
28 1 0.5 F#5 84
28 1.5 0.5 E5 82
28 2 1 C#5 86
28 3 0.5 B4 80
28 3.5 0.5 C#5 82
29 0 2 A4 80
29 2 0.5 C#5 78
29 2.5 0.5 D5 80
29 3 1 E5 84
30 0 1 E5 90
30 1 1 A5 92
30 2 0.5 F#5 84
30 2.5 0.5 E5 82
30 3 1 C#5 86
31 0 1.5 B4 86
31 1.5 0.5 A4 80
31 2 2 G#4 84
32 0 1 C#5 86
32 1 0.5 D5 82
32 1.5 0.5 E5 84
32 2 1 F#5 88
32 3 1 E5 84
33 0 2 D5 84
33 2 0.5 C#5 80
33 2.5 0.5 B4 76
33 3 1 A4 78
34 0 1 A4 82
34 1 1 C#5 86
34 2 0.5 E5 84
34 2.5 0.5 F#5 82
34 3 1 E5 84
35 0 0.5 D5 80
35 0.5 0.5 C#5 82
35 1 1 B4 78
35 2 2 A4 86
36 0 1 E5 82
36 1 0.5 F#5 78
36 1.5 0.5 E5 76
36 2 2 C#5 80
37 0 2 A4 74
37 2 2 - 0
38 0 1 C#5 76
38 1 1 B4 72
38 2 2 A4 78
39 0 2 E5 70
39 2 2 A4 74
"""

BOX_TEXT = """
20 0 2 - 0
20 2 1 E6 58
20 3 1 C#6 54
21 0 1 - 0
21 1 1 F#6 56
21 2 0.5 A6 52
21 2.5 0.5 F#6 50
21 3 1 - 0
22 0 2 - 0
22 2 1 D6 56
22 3 1 B5 52
23 0 1 - 0
23 1 2 E6 54
23 3 1 B5 50
24 0 2 - 0
24 2 1 G#5 52
24 3 1 E6 56
25 0 1 - 0
25 1 1 C#6 54
25 2 2 A5 52
26 0 2 - 0
26 2 1 F#6 56
26 3 1 D6 52
27 0 1 - 0
27 1 2 B5 54
27 3 1 G#5 50
"""

MARKERS = (
    (0, "Intro"),
    (4, "The path"),
    (12, "Horizon"),
    (20, "Quiet water"),
    (28, "Return"),
    (36, "Shore"),
)

LEVEL = {
    "intro": {"guitar": 0.88, "ep": 0.72, "strings": 0.68},
    "a": {"guitar": 1.0, "ep": 0.92, "strings": 0.9},
    "b": {"guitar": 1.04, "ep": 0.96, "strings": 1.0},
    "c": {"guitar": 0.76, "ep": 0.74, "strings": 0.82},
    "a2": {"guitar": 1.06, "ep": 1.0, "strings": 1.04},
    "outro": {"guitar": 0.66, "ep": 0.6, "strings": 0.78},
}

PICK_A = (0, 2, 4, 1, 3, 2, 4, 1)
PICK_B = (0, 1, 3, 4, 2, 4, 1, 3)
PICK_VEL = (82, 60, 72, 56, 70, 54, 66, 52)
SHAKE_VEL = (64, 42, 50, 36, 60, 42, 48, 34)


def parse_chart(text: str) -> list[tuple[int, float, float, str]]:
    chart = []
    bar = 0
    for line in text.strip().splitlines():
        for cell in line.split():
            if "|" in cell:
                first, second = cell.split("|")
                chart.append((bar, 0.0, 2.0, first))
                chart.append((bar, 2.0, 2.0, second))
            else:
                chart.append((bar, 0.0, 4.0, cell))
            bar += 1
    if bar != BARS:
        raise SystemExit(f"chart has {bar} bars, expected {BARS}")
    return chart


def parse_line(text: str, channel: int, inst: str) -> list[Note]:
    notes = []
    coverage: dict[int, float] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        bar_s, beat_s, dur_s, name, vel_s = line.split()
        bar = int(bar_s)
        beat = float(beat_s)
        dur = float(dur_s)
        coverage[bar] = coverage.get(bar, 0.0) + dur
        if name == "-":
            continue
        start = ticks(bar, beat)
        end = ticks(bar, beat + dur)
        notes.append(
            Note(channel, inst, pitch(name), start, max(1, end - start), int(vel_s), bar)
        )
    for bar, total in sorted(coverage.items()):
        if abs(total - 4.0) > 0.02:
            raise SystemExit(f"{inst} bar {bar} covers {total} beats")
    return notes


def add_note(notes: list[Note], channel: int, inst: str, name: str, bar: int, beat: float, dur: float, vel: int) -> None:
    vel = max(1, min(127, int(round(vel))))
    start = ticks(bar, beat)
    end = ticks(bar, beat + dur)
    if inst in {"guitar", "shaker", "hat", "tamb"} and int(round(beat * 2)) % 2 == 1:
        start += SWING
        end += SWING
    notes.append(Note(channel, inst, pitch(name) if isinstance(name, str) and name[0].isalpha() else int(name), start, max(1, end - start), vel, bar))


def compose() -> list[Note]:
    notes: list[Note] = []
    notes.extend(parse_line(FLUTE_TEXT, CH_FLUTE, "flute"))
    notes.extend(parse_line(BOX_TEXT, CH_BOX, "box"))
    for note in list(notes):
        if note.inst == "flute" and 28 <= note.bar < 36 and note.dur >= PPQ:
            notes.append(
                Note(
                    CH_CELESTA,
                    "celesta",
                    note.pitch,
                    note.start + PPQ // 2,
                    note.dur,
                    max(1, int(note.vel * 0.55)),
                    note.bar,
                )
            )
    for bar, beat, name, dur, vel in (
        (0, 0.5, "E6", 1.6, 40),
        (1, 2.0, "F#5", 1.2, 34),
        (2, 1.0, "C#6", 1.6, 38),
        (39, 0.0, "A5", 0.5, 52),
        (39, 0.5, "C#6", 0.5, 54),
        (39, 1.0, "E6", 0.5, 56),
        (39, 1.5, "A6", 1.8, 48),
    ):
        add_note(notes, CH_CELESTA, "celesta", name, bar, beat, dur, vel)
    for bar, beat, name, dur, vel in (
        (12, 2.5, "C#6", 1.2, 52),
        (14, 2.5, "A5", 1.2, 50),
        (16, 2.0, "C#6", 1.5, 54),
        (18, 2.5, "D6", 1.0, 46),
        (30, 2.5, "A5", 1.2, 48),
        (32, 2.0, "C#6", 1.4, 50),
    ):
        add_note(notes, CH_VIBE, "vibe", name, bar, beat, dur, vel)

    for bar, beat, length, name in parse_chart(CHART_TEXT):
        bass, guitar, ep, strings = CHORDS[name]
        level = LEVEL[section(bar)]
        steps = int(round(length / 0.5))
        pattern = PICK_A if bar % 2 == 0 else PICK_B
        for index in range(steps):
            tone = guitar[pattern[index % 8] % len(guitar)]
            vel = PICK_VEL[index % 8] * level["guitar"]
            add_note(notes, CH_GUITAR, "guitar", tone, bar, beat + index * 0.5, 0.92, vel)
        if bar >= 2:
            root = pitch(bass)
            add_note(notes, CH_BASS, "bass", str(root), bar, beat, min(1.7, length * 0.86), 82 * (0.8 if section(bar) == "c" else 1))
            if length >= 4:
                add_note(notes, CH_BASS, "bass", str(root + 7), bar, beat + 2, 0.85, 66 * (0.85 if section(bar) == "c" else 1))
                if section(bar) not in {"intro", "outro", "c"}:
                    add_note(notes, CH_BASS, "bass", str(min(64, root + 12)), bar, beat + 3.5, 0.4, 50)
        ep_dur = length * 0.94 + (2.0 if bar == 39 else 0.0)
        for tone in ep:
            add_note(notes, CH_EP, "ep", tone, bar, beat, ep_dur, 60 * level["ep"])
        string_dur = length * 0.98 + (2.4 if bar == 39 else 0.0)
        for tone in strings:
            add_note(notes, CH_STRINGS, "strings", tone, bar, beat, string_dur, 62 * level["strings"])

    for bar in range(37):
        shake = {"intro": 0.8, "a": 1.0, "b": 1.08, "c": 0.55, "a2": 1.05, "outro": 0.45}[section(bar)]
        for index in range(8):
            add_note(notes, CH_DRUMS, "shaker", "82", bar, index * 0.5, 0.28, SHAKE_VEL[index] * shake)
    for bar in range(BARS):
        sec = section(bar)
        if sec in {"a", "b", "a2"}:
            add_note(notes, CH_DRUMS, "kick", "36", bar, 0, 0.7, 58 if sec != "b" else 62)
            add_note(notes, CH_DRUMS, "kick", "36", bar, 2, 0.55, 40)
            add_note(notes, CH_DRUMS, "hat", "42", bar, 1, 0.28, 36)
            add_note(notes, CH_DRUMS, "hat", "42", bar, 3, 0.28, 32)
        elif bar in {36, 38}:
            add_note(notes, CH_DRUMS, "kick", "36", bar, 0, 0.6, 52)
        if sec == "b":
            add_note(notes, CH_DRUMS, "tamb", "54", bar, 1, 0.55, 44)
            add_note(notes, CH_DRUMS, "tamb", "54", bar, 3, 0.5, 38)
    add_note(notes, CH_DRUMS, "openhat", "46", 12, 0, 1.1, 48)
    add_note(notes, CH_DRUMS, "openhat", "46", 28, 0, 1.0, 44)

    rng = np.random.default_rng(SCORE_SEED)
    for note in notes:
        downbeat = note.start % (PPQ * 4) < 2
        spread = 2 if downbeat else 4 if note.inst in {"flute", "bass", "celesta", "box", "vibe"} else 8
        note.start = max(0, note.start + int(rng.integers(-spread, spread + 1)))
        note.vel = int(min(127, max(1, note.vel + int(rng.integers(-3, 4)))))
    return notes


def track_bytes(events: list[tuple[int, int, bytes]]) -> bytes:
    events = sorted(events, key=lambda item: (item[0], item[1]))
    body = bytearray()
    last = 0
    for tick, _priority, data in events:
        if tick < last:
            raise RuntimeError("MIDI delta went backwards")
        body += vlq(tick - last)
        body += data
        last = tick
    return b"MTrk" + struct.pack(">I", len(body)) + bytes(body)


def write_midi(notes: list[Note], path: Path) -> None:
    conductor = [
        (0, 0, meta_text(0x03, "Seaside Stroll")),
        (0, 0, meta(0x58, bytes([4, 2, 24, 8]))),
        (0, 0, meta(0x59, bytes([3, 0]))),
        (0, 0, meta_tempo(88)),
    ]
    for step in range(1, 16):
        amount = step / 15
        bpm = 80 + 8 * math.cos(math.pi * amount)
        conductor.append((ticks(36, step), 0, meta_tempo(bpm)))
    for bar, text in MARKERS:
        conductor.append((ticks(bar, 0), 0, meta_text(0x06, text)))
    last_tick = max(note.start + note.dur for note in notes)
    conductor.append((max(last_tick, ticks(BARS, 0)), 9, meta(0x2F)))

    grouped: dict[int, list[tuple[int, int, bytes]]] = {}
    names = {
        CH_FLUTE: "Flute",
        CH_GUITAR: "Nylon Guitar",
        CH_EP: "Electric Piano",
        CH_CELESTA: "Celesta",
        CH_STRINGS: "Strings",
        CH_BASS: "Finger Bass",
        CH_BOX: "Music Box",
        CH_VIBE: "Vibraphone",
        CH_DRUMS: "Percussion",
    }
    for channel, name in names.items():
        events = [(0, 0, meta_text(0x03, name))]
        if channel in SETUP:
            program, volume, pan = SETUP[channel]
            events.append((0, 1, bytes([0xC0 | channel, program])))
            events.append((0, 1, bytes([0xB0 | channel, 7, volume])))
            events.append((0, 1, bytes([0xB0 | channel, 10, pan])))
        else:
            events.append((0, 1, bytes([0xB0 | channel, 7, DRUM_VOLUME])))
            events.append((0, 1, bytes([0xB0 | channel, 10, DRUM_PAN])))
        grouped[channel] = events
    for note in notes:
        grouped[note.channel].append((note.start, 3, bytes([0x90 | note.channel, note.pitch, note.vel])))
        grouped[note.channel].append((note.start + note.dur, 2, bytes([0x80 | note.channel, note.pitch, 0])))
    chunks = [track_bytes(conductor)]
    for channel in names:
        end = max(tick for tick, _priority, _data in grouped[channel])
        grouped[channel].append((end, 9, meta(0x2F)))
        chunks.append(track_bytes(grouped[channel]))
    header = b"MThd" + struct.pack(">IHHH", 6, 1, len(chunks), PPQ)
    path.write_bytes(header + b"".join(chunks))


def parse_midi(data: bytes) -> dict:
    if data[:4] != b"MThd":
        raise ValueError("not a MIDI file")
    header_len = struct.unpack(">I", data[4:8])[0]
    fmt, track_count, division = struct.unpack(">HHH", data[8:14])
    pos = 8 + header_len
    notes = []
    tempos = []
    programs: dict[int, int] = {}
    volumes: dict[int, list[tuple[int, int]]] = {}
    pans: dict[int, list[tuple[int, int]]] = {}
    time_sig = None
    key = None
    markers = []
    for _track in range(track_count):
        if data[pos : pos + 4] != b"MTrk":
            raise ValueError("missing track")
        length = struct.unpack(">I", data[pos + 4 : pos + 8])[0]
        pos += 8
        end = pos + length
        tick = 0
        status = 0
        open_notes: dict[tuple[int, int], list[tuple[int, int]]] = {}
        while pos < end:
            delta, pos = read_vlq(data, pos)
            tick += delta
            if data[pos] & 0x80:
                status = data[pos]
                pos += 1
            if status == 0xFF:
                kind = data[pos]
                pos += 1
                size, pos = read_vlq(data, pos)
                payload = data[pos : pos + size]
                pos += size
                if kind == 0x51 and size == 3:
                    tempos.append((tick, int.from_bytes(payload, "big")))
                elif kind == 0x58 and time_sig is None:
                    time_sig = f"{payload[0]}/{2 ** payload[1]}"
                elif kind == 0x59 and key is None:
                    sharps = struct.unpack("b", payload[:1])[0]
                    key = (sharps, "minor" if payload[1] else "major")
                elif kind == 0x06:
                    markers.append((tick, payload.decode("utf-8")))
                elif kind == 0x2F:
                    break
                status = 0
            elif status in (0xF0, 0xF7):
                size, pos = read_vlq(data, pos)
                pos += size
                status = 0
            else:
                kind = status & 0xF0
                channel = status & 0x0F
                if kind in (0xC0, 0xD0):
                    value = data[pos]
                    pos += 1
                    if kind == 0xC0 and channel not in programs:
                        programs[channel] = value
                else:
                    first = data[pos]
                    second = data[pos + 1]
                    pos += 2
                    if kind == 0x90 and second:
                        open_notes.setdefault((channel, first), []).append((tick, second))
                    elif kind in (0x80, 0x90):
                        stack = open_notes.get((channel, first))
                        if stack:
                            start, velocity = stack.pop(0)
                            notes.append((start, tick, channel, first, velocity))
                    elif kind == 0xB0 and first in (7, 10):
                        target = volumes if first == 7 else pans
                        target.setdefault(channel, []).append((tick, second))
        for (channel, note_pitch), stack in open_notes.items():
            for start, velocity in stack:
                notes.append((start, tick, channel, note_pitch, velocity))
        pos = end
    if not tempos or tempos[0][0] != 0:
        tempos = [(0, 500000), *tempos]
    segments = []
    seconds = 0.0
    for tick, micros in tempos:
        if segments:
            prev_tick, prev_micros, prev_seconds = segments[-1]
            seconds = prev_seconds + (tick - prev_tick) * prev_micros / 1e6 / division
        segments.append((tick, micros, seconds))

    def to_seconds(tick: int) -> float:
        chosen = segments[0]
        for segment in segments:
            if segment[0] <= tick:
                chosen = segment
            else:
                break
        start_tick, micros, start_seconds = chosen
        return start_seconds + (tick - start_tick) * micros / 1e6 / division

    sounded = []
    for start, stop, channel, note_pitch, velocity in notes:
        sounded.append(
            {
                "start": to_seconds(start),
                "end": to_seconds(stop),
                "channel": channel,
                "pitch": note_pitch,
                "vel": velocity,
                "program": programs.get(channel),
            }
        )
    return {
        "format": fmt,
        "division": division,
        "time": time_sig,
        "key": key,
        "markers": [(to_seconds(tick), text) for tick, text in markers],
        "tempos": tempos,
        "programs": programs,
        "volumes": volumes,
        "pans": pans,
        "notes": sounded,
        "count": len(sounded),
    }


def control_at(events: list[tuple[int, int]] | None, tick: int, default: int) -> int:
    current = default
    for event_tick, value in events or []:
        if event_tick <= tick:
            current = value
        else:
            break
    return current


def edge_fade(sig: np.ndarray) -> np.ndarray:
    fade = min(16, len(sig) // 4)
    if fade:
        sig[:fade] *= np.linspace(0, 1, fade)
        sig[-fade:] *= np.linspace(1, 0, fade)
    peak = float(np.max(np.abs(sig))) if len(sig) else 0.0
    if peak > 1e-8:
        sig /= peak
    return sig


def flute(freq: float, n: int, vel: int, rng: np.random.Generator) -> np.ndarray:
    t = np.arange(n) / SR
    scoop = -0.016 * np.exp(-t / 0.05)
    vibrato = 0.0075 * np.clip((t - 0.32) / 0.4, 0, 1) * np.sin(2 * np.pi * 5.1 * t)
    phase = 2 * np.pi * freq * np.cumsum(1 + scoop + vibrato) / SR
    tone = np.sin(phase)
    tone += 0.2 * np.sin(2 * phase) * np.exp(-t * 1.3)
    tone += 0.05 * np.sin(3 * phase) * np.exp(-t * 2.2)
    breath = rng.standard_normal(n) * (0.03 + 0.02 * (1 - vel / 127))
    breath = np.convolve(breath, [0.2, 0.6, -0.8], mode="same")
    attack = min(int(0.075 * SR), n // 2)
    release = min(int(0.13 * SR), n // 2)
    envelope = np.ones(n)
    envelope[:attack] = np.linspace(0, 1, attack) ** 1.35
    envelope[-release:] *= np.linspace(1, 0, release)
    return edge_fade((tone * 0.92 + breath) * envelope)


def guitar(freq: float, n: int, vel: int, rng: np.random.Generator) -> np.ndarray:
    t = np.arange(n) / SR
    detune = 1 + float(rng.uniform(-0.0018, 0.0018))
    brightness = 0.75 + 0.25 * vel / 127
    sig = np.zeros(n)
    for partial in range(1, 8):
        amp = brightness * partial ** -1.18
        sig += amp * np.sin(2 * np.pi * freq * detune * partial * t) * np.exp(-t * (1.6 + 1.5 * partial))
    sig += 0.16 * np.sin(2 * np.pi * freq * detune * t) * np.exp(-t * 0.9)
    click = min(int(0.004 * SR), n)
    sig[:click] += rng.standard_normal(click) * np.linspace(0.18, 0, click)
    return edge_fade(sig)


def epiano(freq: float, n: int, vel: int, _rng: np.random.Generator) -> np.ndarray:
    t = np.arange(n) / SR
    index = (1.35 + 0.8 * vel / 127) * np.exp(-t * 3.4) + 0.1
    modulator = index * np.sin(2 * np.pi * freq * 2.0 * t)
    sig = np.sin(2 * np.pi * freq * t + modulator)
    sig += 0.06 * np.sin(2 * np.pi * freq * 7.04 * t) * np.exp(-t * 16)
    tremolo = 1 - 0.07 * np.clip((t - 0.2) / 0.3, 0, 1) * (0.5 - 0.5 * np.sin(2 * np.pi * 4.6 * t))
    attack = min(int(0.012 * SR), n // 2)
    release = min(int(0.2 * SR), n // 2)
    envelope = np.ones(n)
    envelope[:attack] = np.linspace(0, 1, attack)
    envelope[-release:] *= np.linspace(1, 0, release) ** 1.2
    return edge_fade(sig * tremolo * envelope)


def mallet(freq: float, n: int, decay: float, bright: float) -> np.ndarray:
    t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * freq * t) * np.exp(-t * decay)
    sig += bright * np.sin(2 * np.pi * freq * 2.005 * t) * np.exp(-t * decay * 1.7)
    sig += bright * 0.35 * np.sin(2 * np.pi * freq * 3.03 * t) * np.exp(-t * decay * 2.3)
    sig += 0.04 * np.sin(2 * np.pi * freq * 6.4 * t) * np.exp(-t * decay * 4.2)
    return edge_fade(sig)


def celesta(freq: float, n: int, _vel: int, _rng: np.random.Generator) -> np.ndarray:
    return mallet(freq, n, 3.1, 0.42)


def music_box(freq: float, n: int, _vel: int, rng: np.random.Generator) -> np.ndarray:
    sig = mallet(freq, n, 5.4, 0.7)
    click = min(int(0.003 * SR), n)
    noise = np.zeros(n)
    noise[:click] = rng.standard_normal(click) * np.linspace(0.25, 0, click)
    return edge_fade(sig + noise)


def vibraphone(freq: float, n: int, _vel: int, _rng: np.random.Generator) -> np.ndarray:
    t = np.arange(n) / SR
    sig = np.sin(2 * np.pi * freq * t) * np.exp(-t * 1.35)
    sig += 0.32 * np.sin(2 * np.pi * freq * 4 * t) * np.exp(-t * 2.8)
    motor = 0.7 + 0.3 * np.sin(2 * np.pi * 5.7 * t)
    return edge_fade(sig * motor)


def strings(freq: float, n: int, _vel: int, _rng: np.random.Generator) -> np.ndarray:
    t = np.arange(n) / SR
    sig = np.zeros(n)
    for detune in (-0.0045, 0.0, 0.0038):
        phase = 2 * np.pi * freq * (1 + detune) * t
        sig += np.sin(phase) + 0.38 * np.sin(2 * phase) + 0.16 * np.sin(3 * phase)
    sig /= 3
    attack = min(int(0.28 * SR), max(1, n // 3))
    release = min(int(0.36 * SR), max(1, n // 3))
    envelope = np.ones(n)
    envelope[:attack] = np.linspace(0, 1, attack) ** 1.15
    envelope[-release:] *= np.linspace(1, 0, release)
    return edge_fade(sig * envelope)


def bass(freq: float, n: int, _vel: int, _rng: np.random.Generator) -> np.ndarray:
    t = np.arange(n) / SR
    ratio = 1 - 0.012 * np.exp(-t / 0.035)
    phase = 2 * np.pi * freq * np.cumsum(ratio) / SR
    sig = np.sin(phase)
    sig += 0.42 * np.sin(2 * phase) * np.exp(-t * 3.2)
    sig += 0.12 * np.sin(3 * phase) * np.exp(-t * 6.5)
    attack = min(int(0.008 * SR), max(1, n // 3))
    release = min(int(0.08 * SR), max(1, n // 3))
    envelope = np.ones(n)
    envelope[:attack] = np.linspace(0, 1, attack)
    envelope[-release:] *= np.linspace(1, 0, release)
    return edge_fade(sig * envelope)


def kick(n: int, _vel: int, rng: np.random.Generator) -> np.ndarray:
    t = np.arange(n) / SR
    freq = 46 + 130 * np.exp(-t / 0.04)
    phase = 2 * np.pi * np.cumsum(freq) / SR
    sig = np.sin(phase) * np.exp(-t * 7.5)
    sig += rng.standard_normal(n) * np.exp(-t * 160) * 0.35
    return edge_fade(sig)


def noise_hit(n: int, rng: np.random.Generator, decay: float, color: float) -> np.ndarray:
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    noise = np.convolve(noise, [1, -color], mode="same")
    return edge_fade(noise * np.exp(-t * decay))


def hat(n: int, _vel: int, rng: np.random.Generator) -> np.ndarray:
    return noise_hit(n, rng, 55, 0.85)


def open_hat(n: int, _vel: int, rng: np.random.Generator) -> np.ndarray:
    return noise_hit(n, rng, 14, 0.8)


def shaker(n: int, _vel: int, rng: np.random.Generator) -> np.ndarray:
    return noise_hit(n, rng, 70, 0.55)


def tambourine(n: int, _vel: int, rng: np.random.Generator) -> np.ndarray:
    t = np.arange(n) / SR
    sig = noise_hit(n, rng, 16, 0.7)
    for freq in (1890, 2470, 3280):
        sig += 0.18 * np.sin(2 * np.pi * freq * t) * np.exp(-t * 18)
    return edge_fade(sig)


PROGRAMS = {
    73: ("flute", flute, 0.34, 0.34),
    24: ("guitar", guitar, 0.20, 0.16),
    4: ("ep", epiano, 0.18, 0.18),
    8: ("celesta", celesta, 0.18, 0.38),
    48: ("strings", strings, 0.20, 0.30),
    33: ("bass", bass, 0.26, 0.05),
    10: ("box", music_box, 0.16, 0.34),
    11: ("vibe", vibraphone, 0.16, 0.28),
}
DRUMS = {
    36: ("kick", kick, 0.32, 0.04),
    42: ("hat", hat, 0.08, 0.12),
    46: ("openhat", open_hat, 0.11, 0.16),
    82: ("shaker", shaker, 0.08, 0.10),
    54: ("tamb", tambourine, 0.10, 0.15),
}


def pan_gains(pan: int) -> tuple[float, float]:
    angle = (pan / 127) * (math.pi / 2)
    return math.cos(angle), math.sin(angle)


def highpass(channel: np.ndarray, win: int = 1400) -> np.ndarray:
    values = channel.astype(np.float64)
    cumulative = np.cumsum(np.concatenate([np.zeros(1), values]))
    index = np.arange(win, len(values))
    average = (cumulative[index + 1] - cumulative[index + 1 - win]) / win
    values[win:] -= average
    values[:win] *= np.linspace(0, 1, win)
    return values


def impulse(rng: np.random.Generator, reflections: tuple[tuple[float, float], ...]) -> np.ndarray:
    seconds = 2.15
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal(n)
    ir = np.convolve(ir, np.ones(7) / 7, mode="same")
    ir *= np.exp(-t * 2.15)
    ir[0] = 0
    for delay, gain in reflections:
        ir[min(n - 1, int(delay * SR))] += gain
    ir /= np.sqrt(np.sum(ir**2) + 1e-12)
    return (ir * 0.32).astype(np.float64)


def convolve(channel: np.ndarray, ir: np.ndarray) -> np.ndarray:
    n = len(channel) + len(ir) - 1
    size = 1 << (n - 1).bit_length()
    wet = np.fft.irfft(np.fft.rfft(channel, size) * np.fft.rfft(ir, size), size)
    return wet[: len(channel)]


def render(parsed: dict) -> tuple[np.ndarray, dict]:
    notes = sorted(parsed["notes"], key=lambda note: (note["start"], note["channel"], note["pitch"]))
    end = max(note["end"] for note in notes) + TAIL
    total = int(end * SR) + 8
    mix = np.zeros((2, total), dtype=np.float64)
    send = np.zeros((2, total), dtype=np.float64)
    peaks: dict[str, float] = {}
    rng = np.random.default_rng(RENDER_SEED)
    left_ir = impulse(rng, ((0.019, 0.46), (0.037, 0.30), (0.063, 0.22), (0.091, 0.14), (0.128, 0.09)))
    right_ir = impulse(rng, ((0.023, 0.42), (0.041, 0.28), (0.073, 0.20), (0.104, 0.13), (0.151, 0.08)))
    for note in notes:
        start = int(round(note["start"] * SR))
        stop = int(round(note["end"] * SR))
        if stop - start < 32 or start >= total:
            continue
        stop = min(total, stop)
        n = stop - start
        vel = note["vel"]
        if note["channel"] == CH_DRUMS:
            spec = DRUMS.get(note["pitch"])
            if spec is None:
                continue
            name, fn, gain, send_amount = spec
            voice = fn(n, vel, rng)
            freq = 0
        else:
            spec = PROGRAMS.get(note["program"])
            if spec is None:
                continue
            name, fn, gain, send_amount = spec
            freq = 440 * 2 ** ((note["pitch"] - 69) / 12)
            voice = fn(freq, n, vel, rng)
        amount = gain * (vel / 127) ** 1.25
        # Volumes were stored against ticks; approximate with the note start in seconds
        # by reusing the initial CC, which this score never changes after tick 0.
        volume = control_at(parsed["volumes"].get(note["channel"]), 0, 100) / 127
        pan = control_at(parsed["pans"].get(note["channel"]), 0, 64)
        left, right = pan_gains(pan)
        stereo = np.vstack((voice * amount * volume * left, voice * amount * volume * right))
        mix[:, start:stop] += stereo
        send[:, start:stop] += stereo * send_amount
        peaks[name] = max(peaks.get(name, 0.0), float(np.max(np.abs(stereo))))
    wet_l = convolve(send[0], left_ir)
    wet_r = convolve(send[1], right_ir)
    mix[0] += wet_l
    mix[1] += wet_r
    mix[0] = highpass(mix[0])
    mix[1] = highpass(mix[1])
    rms = float(np.sqrt(np.mean(mix**2)))
    peak = float(np.max(np.abs(mix)))
    gain = 0.10 / max(rms, 1e-9)
    if peak * gain > 1.7:
        gain = 1.7 / peak
    mix *= gain
    mix = np.tanh(mix)
    peak = float(np.max(np.abs(mix)))
    mix *= 0.891 / peak
    fade = int(0.05 * SR)
    mix[:, -fade:] *= np.linspace(1, 0, fade)
    report = {
        "seconds": round(end, 3),
        "rms": round(float(np.sqrt(np.mean(mix**2))), 5),
        "peak": round(float(np.max(np.abs(mix))), 5),
        "stem_peaks": {name: round(value, 4) for name, value in sorted(peaks.items())},
    }
    return mix.astype(np.float32), report


def write_wav(mix: np.ndarray, path: Path) -> None:
    dither = np.random.default_rng(DITHER_SEED).uniform(-1 / 32768, 1 / 32768, mix.shape).astype(np.float32)
    pcm = np.clip(mix + dither, -1, 1)
    interleaved = np.round(pcm.T * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(SR)
        handle.writeframes(interleaved.tobytes())


def write_mp3(wav_path: Path, mp3_path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(wav_path),
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-metadata",
            "title=Seaside Stroll",
            "-metadata",
            "artist=Grok 4.7",
            "-metadata",
            "comment=Original MIDI composition synthesized by compose.py",
            str(mp3_path),
        ],
        check=True,
    )


def write_png(path: Path, mix: np.ndarray, markers: list[tuple[float, str]]) -> None:
    width, height = 1280, 720
    image = np.zeros((height, width, 3), dtype=np.uint8)
    image[:] = (243, 239, 230)
    left_margin, right_margin = 46, 46
    top, bottom = 70, 650
    mid = (top + bottom) // 2
    image[mid - 1 : mid + 1, left_margin:width - right_margin] = (214, 206, 192)
    span = width - left_margin - right_margin
    usable = mix[:, : int(mix.shape[1] - TAIL * SR)]
    if usable.shape[1] < 2:
        usable = mix
    buckets = np.array_split(usable, span, axis=1)
    duration = usable.shape[1] / SR
    for index, bucket in enumerate(buckets):
        if bucket.size == 0:
            continue
        x = left_margin + index
        for channel, color in ((0, np.array([31, 78, 92])), (1, np.array([184, 106, 78]))):
            amp = min(1.0, float(np.max(np.abs(bucket[channel]))) * 1.05)
            reach = int(amp * (bottom - top) / 2)
            y0 = max(top, mid - reach)
            y1 = min(bottom, mid + reach + 1)
            column = image[y0:y1, x].astype(np.int16)
            image[y0:y1, x] = np.clip((column * 2 + color) // 3, 0, 255)
    for seconds, _text in markers:
        x = left_margin + int(seconds / duration * (span - 1))
        if left_margin <= x < width - right_margin:
            image[top:bottom, x] = (image[top:bottom, x].astype(np.int16) * 3 + np.array([168, 132, 96])) // 4
    raw = b"".join(b"\x00" + image[row].tobytes() for row in range(height))

    def chunk(tag: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def main() -> None:
    notes = compose()
    if len(notes) < 400:
        raise SystemExit(f"score is too small: {len(notes)} notes")
    write_midi(notes, MIDI_PATH)
    parsed = parse_midi(MIDI_PATH.read_bytes())
    if parsed["count"] != len(notes):
        raise SystemExit(f"MIDI note count {parsed['count']} != score {len(notes)}")
    if parsed["time"] != "4/4" or parsed["key"] != (3, "major"):
        raise SystemExit(f"unexpected meter or key: {parsed['time']} {parsed['key']}")
    mix, report = render(parsed)
    write_wav(mix, WAV_PATH)
    try:
        write_mp3(WAV_PATH, MP3_PATH)
    finally:
        WAV_PATH.unlink(missing_ok=True)
    write_png(PNG_PATH, mix, parsed["markers"])
    summary = {
        "midi": str(MIDI_PATH.name),
        "mp3": str(MP3_PATH.name),
        "notes": parsed["count"],
        "tracks": 10,
        "time": parsed["time"],
        "key": "A major",
        "markers": parsed["markers"],
        "programs": parsed["programs"],
        **report,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
