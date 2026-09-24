"""Seaside Stroll: an anime-style walking theme by the sea, written as MIDI.

The piece is in F major at 100 BPM with a light sixteenth-note swing, and
modulates up a whole step to G major for the last chorus:

  Waves (1 bar) - Intro (4) - Verse A (8) - Verse A' (8) - Pre-chorus (8)
  - Chorus (8) - Bridge (8) - Final chorus in G (8) - Outro (5, ritardando)

An ocarina carries the tune over nylon guitar, electric piano, strings,
finger bass, glockenspiel, and light percussion. A Seashore channel holds one
note per wave and a Bird Tweet channel places a few distant gulls.

Run `python compose.py` to write seaside_stroll.mid next to this file. The
output is deterministic: the humanization uses a fixed random seed.
"""

from dataclasses import dataclass
from itertools import product
from pathlib import Path
import random
import re

from smf import Track, write_midi

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "seaside_stroll.mid"
PPQ = 480
BPM = 100
SWING = 0.035  # beats added to every off-beat sixteenth
SEED = 20260924

rng = random.Random(SEED)

# --------------------------------------------------------------------------
# Pitches and chords
# --------------------------------------------------------------------------

STEPS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def pitch_class(name):
    return (STEPS[name[0]] + name[1:].count("#") - name[1:].count("b")) % 12


def pitch(name):
    match = re.fullmatch(r"([A-G][b#]?)(-?\d)", name)
    letter, octave = match.groups()
    return 12 * (int(octave) + 1) + STEPS[letter[0]] + letter[1:].count("#") - letter[1:].count("b")


# quality: (chord tones, guitar/strings upper voices, electric piano voicing)
QUALITIES = {
    "": ([0, 4, 7], [0, 4, 7, 0], [4, 7, 0, 2]),
    "m": ([0, 3, 7], [0, 3, 7, 0], [3, 7, 0, 2]),
    "add9": ([0, 4, 7, 2], [0, 4, 7, 2], [4, 7, 0, 2]),
    "7": ([0, 4, 7, 10], [0, 4, 7, 10], [4, 10, 2, 7]),
    "maj7": ([0, 4, 7, 11], [0, 4, 7, 11], [4, 7, 11, 2]),
    "maj9": ([0, 4, 7, 11, 2], [4, 7, 11, 2], [4, 7, 11, 2]),
    "m7": ([0, 3, 7, 10], [0, 3, 7, 10], [3, 7, 10, 2]),
    "sus4": ([0, 5, 7], [0, 5, 7, 0], [5, 7, 0, 2]),
    "7sus4": ([0, 5, 7, 10], [0, 5, 7, 10], [5, 10, 2, 7]),
    "6": ([0, 4, 7, 9], [0, 4, 7, 9], [4, 7, 9, 2]),
    "m6": ([0, 3, 7, 9], [0, 3, 7, 9], [3, 7, 9, 2]),
    "69": ([0, 4, 7, 9, 2], [4, 7, 9, 2], [4, 7, 9, 2]),
}


COLOR = {2, 7, 9, 11}  # ninth, fifth, sixth, and major seventh may give way to the tune


@dataclass
class Chord:
    symbol: str
    root: int
    bass: int
    tones: list
    upper: list
    keys: list


def chord(symbol):
    match = re.fullmatch(r"([A-G][b#]?)([^/]*)(?:/([A-G][b#]?))?", symbol)
    root_name, quality, bass_name = match.groups()
    root = pitch_class(root_name)
    tones, upper, keys = QUALITIES[quality]
    bass = pitch_class(bass_name) if bass_name else root
    return Chord(symbol, root, bass, tones, upper, keys)


def clashes(pc, avoid):
    return any((other - pc) % 12 in (1, 11) for other in avoid)


def classes(ch, intervals, avoid=()):
    """Pitch classes for a voicing; colour tones a semitone from the tune are replaced."""
    third = next(i for i in (4, 3, 5) if i in ch.tones)
    out = []
    for interval in intervals:
        pc = (ch.root + interval) % 12
        if interval in COLOR and clashes(pc, avoid):
            options = [(ch.root + alt) % 12 for alt in (0, 7, third)]
            pc = next((alt for alt in options if not clashes(alt, avoid)), None)
        if pc is not None:
            out.append(pc)
    return out


def voicing(pcs, low, high, center, previous=None):
    """Choose one pitch per class in [low, high], favouring smooth voice leading."""
    options = [[p for p in range(low, high + 1) if p % 12 == pc] for pc in pcs]
    if any(pcs.count(pc) > len(options[pcs.index(pc)]) for pc in pcs):
        return voicing(list(dict.fromkeys(pcs)), low, high, center, previous)
    best, best_score = None, float("inf")
    for combo in product(*options):
        if len(set(combo)) < len(combo):
            continue
        notes = sorted(combo)
        score = 0.35 * abs(sum(notes) / len(notes) - center)
        if previous:
            score += sum(abs(a - b) for a, b in zip(notes, previous))
        for a, b in zip(notes, notes[1:]):
            gap = b - a
            score += 6 if gap == 1 else 2 if gap == 2 and a < 60 else 0
            score += max(0, gap - 9) * 0.8
        if score < best_score:
            best, best_score = notes, score
    return best


def near(pc, low):
    """The pitch of class pc in [low, low + 12)."""
    return low + (pc - low) % 12


# --------------------------------------------------------------------------
# Form and harmony
# --------------------------------------------------------------------------

WAVES, INTRO, VERSE1, VERSE2, PRE, CHORUS, BRIDGE, FINAL, OUTRO, END = (
    0, 1, 5, 13, 21, 29, 37, 45, 53, 58)

VERSE_CHORDS = ["Fadd9", "C/E", "Dm7", "Cm7 F7", "Bbmaj7", "Am7 D7", "Gm7", "C7sus4 C7"]
CHART = [
    (INTRO, ["Fmaj9", "Bbmaj7/F", "Fmaj9", "Gm7 C7sus4"]),
    (VERSE1, VERSE_CHORDS),
    (VERSE2, VERSE_CHORDS[:7] + ["Gm7/C C7"]),
    (PRE, ["Bbmaj7", "A7", "Dm7", "Cm7 F7", "Bbmaj7", "A7", "Dm7 Dm7/C", "Gm7/C"]),
    (CHORUS, ["Bbmaj7", "Cadd9", "Am7", "Dm7", "Gm7", "Am7 D7", "Gm7", "C7sus4 C7"]),
    (BRIDGE, ["Dm7", "Bbmaj7", "Gm7", "A7sus4 A7", "Dm7", "Bbmaj7", "Ebmaj7", "D7sus4 D7"]),
    (FINAL, ["Cmaj7", "Dadd9", "Bm7", "Em7", "Am7", "Bm7 E7", "Am7", "D7sus4 D7"]),
    (OUTRO, ["Gmaj9", "Cmaj7/G", "Gmaj9", "Cmaj7 Cm6", "G69"]),
]


@dataclass
class Segment:
    start: float
    length: float
    chord: Chord
    next: "Segment" = None


SEGMENTS = []
for first_bar, bars in CHART:
    for index, text in enumerate(bars):
        symbols = text.split()
        for part, symbol in enumerate(symbols):
            length = 4 / len(symbols)
            SEGMENTS.append(Segment((first_bar + index) * 4 + part * length, length, chord(symbol)))
for current, following in zip(SEGMENTS, SEGMENTS[1:]):
    current.next = following


def segments(first_bar, last_bar):
    return [s for s in SEGMENTS if first_bar * 4 <= s.start < last_bar * 4]


def segment_at(beat):
    return next(s for s in reversed(SEGMENTS) if s.start <= beat + 1e-6)


MELODY = []  # (start, length, pitch) of every melodic line, used to keep voicings clear of it


def tune(start, end):
    """Pitch classes of melody notes that sound for at least an eighth within [start, end)."""
    return {note % 12 for s, length, note in MELODY if min(end, s + length) - max(start, s) >= 0.4}


# --------------------------------------------------------------------------
# Parts
# --------------------------------------------------------------------------


class Part:
    def __init__(self, name, channel, program, volume, pan, reverb, jitter=0.008, spread=5, swing=True):
        self.name, self.channel, self.program = name, channel, program
        self.volume, self.pan, self.reverb = volume, pan, reverb
        self.jitter, self.spread, self.swing = jitter, spread, swing
        self.notes = []
        self.controls = []

    def add(self, start, length, note, velocity):
        self.notes.append((start, length, note, velocity))

    def ramp(self, controller, start, end, first, last, step=0.25):
        count = max(1, round((end - start) / step))
        for index in range(count + 1):
            share = index / count
            self.controls.append((start + share * (end - start), controller, first + (last - first) * share))


lead = Part("Ocarina", 0, 79, 110, 0.0, 0.26)
glock = Part("Glockenspiel", 1, 9, 84, 0.3, 0.34)
guitar = Part("Nylon Guitar", 2, 24, 100, -0.35, 0.2, jitter=0.006)
keys = Part("Electric Piano", 3, 4, 90, 0.28, 0.22)
strings = Part("Strings", 4, 48, 90, -0.1, 0.36, jitter=0.01)
bass = Part("Finger Bass", 5, 33, 104, 0.0, 0.04, jitter=0.006)
sea = Part("Seashore", 6, 122, 96, 0.0, 0.12, jitter=0, spread=0, swing=False)
gulls = Part("Gulls", 7, 123, 64, 0.45, 0.6, jitter=0, spread=0, swing=False)
violins = Part("Strings Legato", 8, 49, 88, 0.12, 0.36)
drums = Part("Percussion", 9, 0, 100, 0.0, 0.12, jitter=0.004, spread=4)
PARTS = [lead, glock, guitar, keys, strings, violins, bass, drums, sea, gulls]


def line(text, start, transpose=0):
    """Parse 'A5:1.5 G5:.5 r:.5 | ...' into (start, length, pitch) notes."""
    notes, position = [], start
    for token in text.split():
        if token == "|":
            assert abs((position - start) % 4) < 1e-9, f"bar check failed at beat {position}"
            continue
        name, length = token.split(":")
        if name != "r":
            notes.append((position, float(length), pitch(name) + transpose))
        position += float(length)
    return notes


# --------------------------------------------------------------------------
# Melodies (C4 = 60, lengths in beats)
# --------------------------------------------------------------------------

MOTIF = "A5:1.5 G5:.5 F5:1 C5:1 | D5:1.5 F5:.5 A5:1 G5:1 | A5:1.5 G5:.5 F5:.5 G5:.5 A5:1 | Bb5:1 A5:.5 F5:.5 G5:2"

VERSE_OPENING = (
    "A4:.5 C5:.5 F5:1 E5:.5 C5:1.5 | D5:.5 E5:.5 G5:1 F5:.5 E5:1 r:.5 | "
    "F5:.5 E5:.5 D5:.5 C5:.5 A4:1.5 r:.5 | Bb4:.5 C5:.5 Eb5:1 D5:.5 C5:.5 A4:1 |"
)
VERSE_A = VERSE_OPENING + (
    " F5:.5 D5:.5 A5:1 G5:.5 F5:.5 D5:1 | E5:.5 C5:.5 E5:.5 G5:.5 F#5:1 D5:.5 C5:.5 | "
    "Bb4:.5 C5:.5 D5:1 F5:1 E5:.5 D5:.5 | C5:2 r:1 G4:.5 Bb4:.5"
)
VERSE_B = VERSE_OPENING + (
    " D5:.5 F5:.5 A5:1.5 G5:.5 F5:.5 G5:.5 | A5:1 E5:.5 G5:.5 F#5:1.5 A5:.5 | "
    "G5:1.5 F5:.5 D5:1 Bb4:.5 C5:.5 | C5:2 D5:.5 E5:.5 F5:.5 G5:.5"
)
PRE_MELODY = (
    "F5:1.5 D5:.5 F5:.5 G5:1.5 | E5:1.5 C#5:.5 E5:.5 G5:1.5 | "
    "F5:1.5 D5:.5 F5:.5 A5:1.5 | G5:1.5 Eb5:.5 F5:.5 A5:1.5 | "
    "Bb5:1.5 A5:.5 F5:.5 D5:.5 F5:1 | E5:1 G5:.5 A5:.5 C#6:1.5 A5:.5 | "
    "D6:2 C6:.5 A5:.5 F5:1 | G5:.5 F5:.5 G5:1 r:.5 C5:.5 F5:.5 G5:.5"
)
CHORUS_MELODY = (
    "A5:1.5 G5:.5 F5:1 D5:.5 E5:1 C5:.5 D5:.5 E5:.5 G5:1.5 r:.5 | "
    "C6:1.5 Bb5:.5 A5:1 F5:.5 G5:1 E5:.5 F5:.5 G5:.5 A5:1.5 r:.5 | "
    "D6:1.5 C6:.5 Bb5:1 A5:.5 G5:1 A5:.5 C6:1 D6:.5 C6:.5 A5:.5 F#5:.5 | "
    "G5:1.5 F5:.5 G5:.5 A5:.5 Bb5:.5 A5:.5 G5:2.5 F5:.5 E5:1"
)
BRIDGE_MELODY = (
    "A5:1 F5:.5 E5:.5 D5:2 | D5:.5 F5:.5 A5:1 C6:2 | Bb5:1 A5:.5 F5:.5 G5:2 | E5:1 D5:1 C#5:2 | "
    "A5:1 F5:.5 E5:.5 D5:1 A4:1 | D5:.5 F5:.5 A5:1 F5:1 G5:1 | G5:1.5 Bb5:.5 D6:2 | C6:1 A5:1 F#5:1 A5:1"
)
OUTRO_MELODY = "B5:1.5 A5:.5 G5:1 D5:1 | E5:1.5 G5:.5 B5:1 A5:1 | B5:1.5 A5:.5 G5:.5 A5:.5 B5:1 | G5:.5 A5:.5 B5:1 C6:1 A5:1 | B5:4"


def sing(notes, velocity, part=lead):
    """Lead phrasing: slightly detached, louder on high notes and downbeats."""
    for start, length, note in notes:
        accent = 5 if abs(start % 2) < 1e-6 else 0
        gap = min(0.06, 0.15 * length)
        part.add(start, length - gap, note, velocity + 0.7 * (note - 74) + accent + min(length, 2) * 3)


intro_tune = line(MOTIF, INTRO * 4)
verse_a = line(VERSE_A, VERSE1 * 4)
verse_b = line(VERSE_B, VERSE2 * 4)
pre_tune = line(PRE_MELODY, PRE * 4)
chorus_tune = line(CHORUS_MELODY, CHORUS * 4)
bridge_tune = line(BRIDGE_MELODY, BRIDGE * 4)
final_tune = line(CHORUS_MELODY, FINAL * 4, 2)
outro_tune = line(OUTRO_MELODY, OUTRO * 4)
for tune_notes in (intro_tune, verse_a, verse_b, pre_tune, chorus_tune, bridge_tune, final_tune, outro_tune):
    MELODY.extend(tune_notes)

sing(verse_a, 76)
sing(verse_b, 80)
sing(pre_tune, 84)
sing(chorus_tune, 92)
sing(final_tune, 96)
sing(outro_tune[:-1], 74)
lead.add(OUTRO * 4 + 16, 5.5, pitch("B5"), 70)

for start, length, note in final_tune:
    violins.add(start, length + 0.02, note - 12, 70 + 0.5 * (note - 82))

# Glockenspiel: intro motif, fills, and sparkling doubles of the tunes.
for start, length, note in intro_tune:
    glock.add(start, length, note + 12, 74 if start % 4 == 0 else 66)
FILLS = [
    (VERSE1 + 3, 3.0, ["C6", "Eb6", "F6", "A6"]),
    (VERSE1 + 7, 2.0, ["E6", "G6", "Bb6", "C7"]),
    (VERSE2 + 3, 3.0, ["A6", "F6", "Eb6", "C6"]),
    (VERSE2 + 7, 0.5, ["E6", "G6", "Bb6", "C7"]),
    (PRE + 7, 2.0, ["C6", "D6", "E6", "F6", "G6", "A6", "Bb6", "C7"]),
]
for bar, beat, names in FILLS:
    for index, name in enumerate(names):
        glock.add(bar * 4 + beat + index * 0.25, 0.5, pitch(name), 52 + 4 * index)
for start, length, note in chorus_tune:
    glock.add(start, length, note + 12, 44)
for start, length, note in bridge_tune:
    glock.add(start, length, note + 12, 48)
    keys.add(start, length * 0.95, note, 70)
for start, length, note in final_tune:
    glock.add(start, length, note + 12, 46)
for start, length, note in outro_tune[:13]:
    glock.add(start, length, note + 12, 40)
for index, name in enumerate(["D6", "G6", "A6", "B6", "D7"]):
    glock.add((END - 1) * 4 + index * 0.25, 3, pitch(name), 50 - 3 * index)

# --------------------------------------------------------------------------
# Accompaniment
# --------------------------------------------------------------------------

memory = {}
shapes = {}


def around_tune(seg, intervals):
    return classes(seg.chord, intervals, tune(seg.start, seg.start + seg.length))


def guitar_shape(seg):
    if seg.start not in shapes:
        low = near(seg.chord.bass, 45)
        upper = voicing(around_tune(seg, seg.chord.upper), max(55, low + 3), 79, 66, memory.get("guitar"))
        memory["guitar"] = upper
        shapes[seg.start] = [low] + upper
    return shapes[seg.start]


def arpeggio(first_bar, last_bar, velocity, pattern=(0, 2, 3, 4, 1, 3, 2, 4), step=0.5):
    for seg in segments(first_bar, last_bar):
        shape = guitar_shape(seg)
        for index in range(round(seg.length / step)):
            start = seg.start + index * step
            string = pattern[index % len(pattern)]
            ring = seg.start + seg.length - start if string == 0 else min(2.0, seg.start + seg.length - start)
            accent = 8 if abs(start % 1) < 1e-6 else -6
            guitar.add(start, ring, shape[string], velocity + accent - 3 * (string == 4))


STRUM = [(0, "D"), (1, "D"), (1.5, "U"), (2.5, "U"), (3, "D"), (3.5, "U")]


def strum(first_bar, last_bar, velocity):
    hits = [(bar * 4 + offset, way) for bar in range(first_bar, last_bar) for offset, way in STRUM]
    for index, (start, way) in enumerate(hits):
        shape = guitar_shape(segment_at(start))
        end = hits[index + 1][0] if index + 1 < len(hits) else start + 1
        strings_hit = shape if way == "D" else shape[:0:-1][:3]
        level = velocity + (10 if start % 4 == 0 else 0) - (18 if way == "U" else 0)
        for order, note in enumerate(strings_hit):
            offset = order * (0.018 if way == "D" else 0.014)
            guitar.add(start + offset, end - start - offset - 0.03, note, level - 2 * order)


def keys_shape(seg):
    shape = voicing(around_tune(seg, seg.chord.keys), 52, 76, 63, memory.get("keys"))
    memory["keys"] = shape
    return shape


def comp(first_bar, last_bar, velocity, rhythm):
    for seg in segments(first_bar, last_bar):
        shape = keys_shape(seg)
        for offset, length in rhythm[seg.length]:
            accent = 6 if offset == 0 else 0
            for order, note in enumerate(shape):
                keys.add(seg.start + offset + 0.006 * order, length, note, velocity + accent - 2 * order)


def pad(first_bar, last_bar, velocity, part=strings):
    for seg in segments(first_bar, last_bar):
        low = near(seg.chord.bass, 41)
        upper = voicing(around_tune(seg, seg.chord.upper), max(55, low + 7), 81, 68, memory.get("strings"))
        memory["strings"] = upper
        for note in [low] + upper:
            part.add(seg.start, seg.length + 0.05, note, velocity)


BASS_STYLES = {
    "held": {4: [(0, 3.9, "R")], 2: [(0, 1.9, "R")]},
    "walk": {4: [(0, 1.4, "R"), (1.5, 0.45, "R"), (2, 1.4, "F"), (3.5, 0.45, "A")],
             2: [(0, 1.4, "R"), (1.5, 0.45, "A")]},
    "drive": {4: [(i * 0.5, 0.42, "R") for i in range(7)] + [(3.5, 0.42, "A")],
              2: [(0, 0.42, "R"), (0.5, 0.42, "R"), (1, 0.42, "R"), (1.5, 0.42, "A")]},
    "bounce": {4: [(0, 0.9, "R"), (1.5, 0.45, "R"), (2, 0.45, "O"), (2.5, 0.9, "R"), (3.5, 0.45, "A")],
               2: [(0, 0.9, "R"), (1.5, 0.45, "A")]},
}


def bassline(first_bar, last_bar, style, velocity):
    for seg in segments(first_bar, last_bar):
        root = near(seg.chord.bass, 33)
        fifth = root + 7 if root + 7 <= 50 else root - 5
        following = near(seg.next.chord.bass, 33) if seg.next else root
        for offset, length, role in BASS_STYLES[style][seg.length]:
            start = seg.start + offset
            avoid = {note % 12 for s, n, note in MELODY if min(start + length, s + n) - max(start, s) >= 0.2}
            if role == "R":
                options = [root]
            elif role == "O":
                options = [root + 12]
            elif role == "F" or following == root:
                options = [fifth, root + 12]
            else:
                step = 1 if following > root else -1
                options = [following - step, following - 2 * step, following + step]
            note = next((option for option in options if not clashes(option % 12, avoid)), root)
            accent = 8 if abs(offset % 2) < 1e-6 else 0
            bass.add(start, length, note, velocity + accent)


# Guitar
arpeggio(INTRO, VERSE1, 64)
arpeggio(VERSE1, VERSE2, 68)
arpeggio(VERSE2, PRE, 72)
arpeggio(PRE, CHORUS - 1, 74)
strum(CHORUS - 1, CHORUS, 70)
strum(CHORUS, BRIDGE, 80)
arpeggio(BRIDGE, BRIDGE + 7, 58, pattern=(0, 3, 4, 2), step=1.0)
strum(BRIDGE + 7, FINAL, 66)
strum(FINAL, OUTRO, 84)
arpeggio(OUTRO, END - 1, 62)
for order, note in enumerate(guitar_shape(segment_at((END - 1) * 4))):
    guitar.add((END - 1) * 4 + 0.06 * order, 6, note, 70 - 3 * order)

# Electric piano
HELD = {4: [(0, 3.9)], 2: [(0, 1.9)]}
PUSH = {4: [(0, 1.4), (1.5, 0.45), (2.5, 1.4)], 2: [(0, 1.4), (1.5, 0.45)]}
LIFT = {4: [(0, 1.4), (1.5, 2.4)], 2: [(0, 1.9)]}
comp(VERSE1, VERSE2, 48, HELD)
comp(VERSE2, PRE, 56, PUSH)
comp(PRE, CHORUS, 60, PUSH)
comp(CHORUS, BRIDGE, 62, LIFT)
comp(BRIDGE, FINAL, 40, HELD)
comp(FINAL, OUTRO, 64, LIFT)
comp(OUTRO, END - 1, 46, HELD)
for order, note in enumerate(keys_shape(segment_at((END - 1) * 4))):
    keys.add((END - 1) * 4 + 0.09 * order, 6, note, 52 - 2 * order)

# Strings
pad(PRE, CHORUS, 60)
pad(CHORUS, BRIDGE, 72)
pad(BRIDGE, FINAL, 56)
pad(FINAL, END, 74)
strings.notes = [(s, 6 if s >= (END - 1) * 4 else n, p, v) for s, n, p, v in strings.notes]
strings.ramp(11, PRE * 4, CHORUS * 4 - 1, 58, 112, step=0.5)
strings.controls.append((CHORUS * 4, 11, 100))
strings.controls.append((BRIDGE * 4, 11, 72))
strings.ramp(11, (FINAL - 1) * 4, FINAL * 4 - 0.25, 72, 116)
strings.controls.append((FINAL * 4, 11, 104))
strings.ramp(11, OUTRO * 4, END * 4, 100, 58, step=0.5)

# Bass
bassline(INTRO + 2, VERSE1, "held", 66)
bassline(VERSE1, VERSE2, "walk", 76)
bassline(VERSE2, PRE, "walk", 80)
bassline(PRE, CHORUS, "drive", 76)
bassline(CHORUS, BRIDGE, "bounce", 86)
bassline(BRIDGE, BRIDGE + 4, "held", 64)
bassline(BRIDGE + 4, BRIDGE + 7, "walk", 70)
bassline(BRIDGE + 7, FINAL, "drive", 78)
bassline(FINAL, OUTRO, "bounce", 90)
bassline(OUTRO, OUTRO + 2, "walk", 70)
bassline(OUTRO + 2, END - 1, "held", 64)
bass.add((END - 1) * 4, 6, pitch("G1"), 72)

# --------------------------------------------------------------------------
# Percussion (General MIDI drum map)
# --------------------------------------------------------------------------

KIT = {"kick": 36, "side": 37, "snare": 38, "hat": 42, "open": 46, "crash": 49, "tamb": 54,
       "shaker": 70, "triangle": 81, "tom_high": 50, "tom_mid": 47, "tom_low": 45, "floor": 43}
LEVELS = {"X": 112, "x": 90, "o": 64, "g": 40}


def beat(bar, **patterns):
    for name, pattern in patterns.items():
        for step, mark in enumerate(pattern):
            if mark != ".":
                drums.add(bar * 4 + step * 0.25, 0.2, KIT[name], LEVELS[mark])


def hit(bar, offset, name, velocity):
    drums.add(bar * 4 + offset, 0.5, KIT[name], velocity)


SHAKE = "xgogxgogxgogxgog"
VERSE_BEAT = dict(kick="x.......x.....o.", side="....x.......x...", shaker=SHAKE)
VERSE2_BEAT = dict(kick="x.....o.x.....o.", side="....x.......x...", hat="x.o.x.o.x.o.x.o.",
                   shaker=SHAKE, tamb="....o.......o...")
PRE_BEAT = dict(kick="x.......x.o.....", snare="....o.......o...", hat="x.o.x.o.x.o.x.o.", shaker=SHAKE)
CHORUS_BEAT = dict(kick="x.....x.x.....o.", snare="....X.......X...", hat="x.o.x.o.x.o.x...",
                   open="..............o.", tamb=SHAKE)

for bar in range(INTRO + 2, VERSE1):
    beat(bar, shaker="ogggogggogggoggg" if bar == INTRO + 2 else "xgggxgggxgggxggg")
hit(INTRO, 0, "triangle", 54)
for bar in range(VERSE1, VERSE2):
    beat(bar, **VERSE_BEAT)
for bar in range(VERSE2, PRE):
    beat(bar, **VERSE2_BEAT)
for bar in range(PRE, CHORUS - 1):
    beat(bar, **PRE_BEAT)
beat(CHORUS - 1, kick="x.......x...x...", snare="........o.o.xoxX", hat="x.o.x.o.", shaker="xgogxgogxgog")
for bar in range(CHORUS, BRIDGE - 1):
    beat(bar, **CHORUS_BEAT)
beat(BRIDGE - 1, kick="x.....x.x.......", snare="....X.......x.g.", hat="x.o.x.o.x.o.", tamb="xgogxgogxgog")
for bar in (CHORUS, CHORUS + 4):
    hit(bar, 0, "crash", 104)
hit(BRIDGE, 0, "crash", 58)
for bar in range(BRIDGE, BRIDGE + 4):
    beat(bar, shaker="x.o.x.o.x.o.x.o.")
for bar in range(BRIDGE + 4, BRIDGE + 7):
    beat(bar, kick="x.......x.......", side="....o.......o...", shaker=SHAKE)
hit(BRIDGE, 0, "triangle", 60)
hit(BRIDGE + 4, 0, "triangle", 56)
beat(BRIDGE + 7, kick="x...x...x...x...", snare="g.g.o.o.oxoxxxXX", shaker=SHAKE)
for bar in range(FINAL, OUTRO - 1):
    beat(bar, **CHORUS_BEAT)
beat(OUTRO - 1, kick="x.....x.x.......", snare="....X...........", hat="x.o.x.o.",
     tom_high="........xo......", tom_mid="..........xo....", tom_low="............xo..",
     floor="..............xX")
for bar, level in ((FINAL, 110), (FINAL + 4, 100), (OUTRO, 72), (END - 1, 46)):
    hit(bar, 0, "crash", level)
for bar in range(OUTRO, OUTRO + 2):
    beat(bar, kick="x...............", side="....o.......o...", shaker=SHAKE)
for bar in range(OUTRO + 2, END - 1):
    beat(bar, shaker="x.o.x.o.x.o.x.o." if bar == OUTRO + 2 else "o.g.o.g.o.g.o.g.")
hit(END - 1, 0, "kick", 60)
hit(END - 1, 0, "triangle", 62)

# --------------------------------------------------------------------------
# Shoreline: one Seashore note per wave, a few distant gulls
# --------------------------------------------------------------------------

TAIL = 8  # beats of waves after the final bar
position = 0.0
while position < END * 4 + TAIL - 6:
    length = min(rng.uniform(8.5, 13.5), END * 4 + TAIL - position)
    sea.add(position, length, rng.randint(57, 64), rng.randint(58, 100))
    position += length * rng.uniform(0.55, 0.78)

sea.controls.append((0, 11, 118))
sea.ramp(11, INTRO * 4, VERSE1 * 4, 118, 94, step=1)
sea.ramp(11, VERSE1 * 4, VERSE1 * 4 + 4, 94, 80)
sea.ramp(11, VERSE2 * 4, VERSE2 * 4 + 4, 80, 72)
sea.ramp(11, PRE * 4, PRE * 4 + 4, 72, 64)
sea.ramp(11, CHORUS * 4, CHORUS * 4 + 2, 64, 56)
sea.ramp(11, BRIDGE * 4, BRIDGE * 4 + 4, 56, 100)
sea.ramp(11, (FINAL - 1) * 4, FINAL * 4, 100, 58)
sea.ramp(11, OUTRO * 4, (END - 1) * 4, 58, 106, step=1)
sea.ramp(11, END * 4 - 1, END * 4 + TAIL, 106, 0, step=0.5)

for start, length, note, velocity in [
    (1.0, 1.3, 86, 50), (10.5, 0.9, 84, 34), (BRIDGE * 4 + 1.5, 1.3, 86, 44),
    ((BRIDGE + 2) * 4 + 2, 0.9, 83, 34), ((BRIDGE + 5) * 4 + 2.5, 1.2, 85, 38),
    ((OUTRO + 1) * 4 + 1, 1.0, 84, 36), (END * 4 + 1.5, 1.4, 86, 42),
]:
    gulls.add(start, length, note, velocity)

# --------------------------------------------------------------------------
# Performance and file output
# --------------------------------------------------------------------------


def swung(position):
    sixteenth = position * 4
    if abs(sixteenth - round(sixteenth)) < 1e-6 and round(sixteenth) % 2 == 1:
        return position + SWING
    return position


def ticks(position):
    return max(0, round(position * PPQ))


def build():
    conductor = Track("Seaside Stroll")
    conductor.text(0, "Anime-style seaside stroll. Composed in code by compose.py (Claude Opus 5.5).")
    conductor.time_signature(0, 4, 4)
    conductor.key_signature(0, -1)
    conductor.key_signature(ticks(FINAL * 4), 1)
    conductor.tempo(0, BPM)
    ritardando = OUTRO + 2
    for step in range(16):
        share = (step + 1) / 16
        conductor.tempo(ticks(ritardando * 4 + step * 0.5), BPM - 30 * share ** 1.6)
    conductor.tempo(ticks((END - 1) * 4), 68)
    for bar, name in [(WAVES, "Waves"), (INTRO, "Intro"), (VERSE1, "Verse A"), (VERSE2, "Verse A'"),
                      (PRE, "Pre-chorus"), (CHORUS, "Chorus"), (BRIDGE, "Bridge"),
                      (FINAL, "Final chorus (G major)"), (OUTRO, "Outro")]:
        conductor.marker(ticks(bar * 4), name)
    tracks = [conductor]
    for part in PARTS:
        track = Track(part.name)
        if part.channel != 9:
            track.program(0, part.channel, part.program)
        track.control(0, part.channel, 7, part.volume)
        track.control(0, part.channel, 10, 64 + 63 * part.pan)
        track.control(0, part.channel, 91, 127 * part.reverb)
        track.control(0, part.channel, 11, 127 if part is not strings else 58)
        for position, controller, value in part.controls:
            track.control(ticks(position), part.channel, controller, value)
        for start, length, note, velocity in sorted(part.notes):
            end = start + length
            if part.swing:
                start, end = swung(start), swung(end)
            if part.jitter:
                start += rng.gauss(0, part.jitter)
            velocity += rng.randint(-part.spread, part.spread) if part.spread else 0
            track.note(ticks(start), ticks(end), part.channel, note, velocity)
        tracks.append(track)
    write_midi(OUTPUT, tracks, PPQ)
    count = sum(len(part.notes) for part in PARTS)
    print(f"Wrote {OUTPUT.name}: {len(tracks)} tracks, {count} notes, {END} bars + {TAIL} beats of waves")


if __name__ == "__main__":
    build()
