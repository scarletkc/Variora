"""Snowlit Eve (雪明かりのイブ).

Composition script. It writes snowlit-eve.mid: a Japanese Christmas pop
ballad in D major that lifts to E-flat major for its last chorus. Every
note, controller and tempo change is generated here; render.py turns the
MIDI file into audio.

    python compose.py
"""

import itertools
import random
from pathlib import Path

import smf

HERE = Path(__file__).resolve().parent
MIDI_PATH = HERE / "snowlit-eve.mid"
TITLE = "Snowlit Eve (雪明かりのイブ)"
SEED = 1224  # used only for small timing and velocity variations

PPQ = 480
S = PPQ // 4  # one sixteenth note
BAR = 16 * S
TEMPO = 84


def at(bar, step=0):
    """Tick of a 1-based bar plus a number of sixteenth steps."""
    return (bar - 1) * BAR + round(step * S)


# --- Pitches and chords -----------------------------------------------------

LETTERS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def split_name(name):
    size = 1
    while size < len(name) and name[size] in "#b":
        size += 1
    shift = sum(1 if sign == "#" else -1 for sign in name[1:size])
    return LETTERS[name[0]] + shift, name[size:]


def note(name):
    """MIDI number of a note name such as F#5 or Bb4."""
    pitch_class, octave = split_name(name)
    return 12 * (int(octave) + 1) + pitch_class


# Intervals above the root: (keyboard colour tones, core triad/seventh tones).
QUALITIES = {
    "": ((0, 4, 7), (0, 4, 7)),
    "add9": ((0, 4, 7, 14), (0, 4, 7, 14)),
    "M7": ((4, 7, 11, 14), (0, 4, 7, 11)),
    "m": ((0, 3, 7), (0, 3, 7)),
    "mM7": ((3, 7, 11), (3, 7, 11)),
    "m7": ((3, 7, 10, 14), (0, 3, 7, 10)),
    "m7_11": ((3, 7, 10, 17), (0, 3, 7, 10)),
    "m7b5": ((0, 3, 6, 10), (0, 3, 6, 10)),
    "m6": ((3, 7, 9, 14), (0, 3, 7, 9)),
    "7": ((4, 10, 14, 21), (0, 4, 7, 10)),
    "9": ((4, 7, 10, 14), (0, 4, 7, 10)),
    "7b9": ((4, 7, 10, 13), (0, 4, 7, 10)),
    "7sus4": ((5, 7, 10, 14), (0, 5, 7, 10)),
}


class Chord:
    def __init__(self, symbol):
        self.symbol = symbol
        head, _, bass = symbol.partition("/")
        size = 2 if len(head) > 1 and head[1] in "#b" else 1
        self.root = split_name(head[:size] + "0")[0] % 12
        color, core = QUALITIES[head[size:]]
        self.color = [(self.root + step) % 12 for step in color]
        self.core = [(self.root + step) % 12 for step in core]
        self.bass = split_name(bass + "0")[0] % 12 if bass else self.root

    def __repr__(self):
        return self.symbol


class Timeline:
    """Chord spans across the whole song."""

    def __init__(self):
        self.spans = []

    def chart(self, bar, bars):
        for offset, text in enumerate(bars):
            items = []
            for token in text.split():
                symbol, _, beats = token.partition(":")
                items.append([symbol, float(beats) if beats else None])
            fixed = sum(beats for _, beats in items if beats is not None)
            open_items = [item for item in items if item[1] is None]
            for item in open_items:
                item[1] = (4 - fixed) / len(open_items)
            tick = at(bar + offset)
            for symbol, beats in items:
                length = round(beats * PPQ)
                self.spans.append((tick, tick + length, Chord(symbol)))
                tick += length

    def within(self, first_bar, last_bar):
        start, end = at(first_bar), at(last_bar + 1)
        return [span for span in self.spans if start <= span[0] < end]


# --- Parts ------------------------------------------------------------------


class Part:
    def __init__(self, name, channel, program, volume, pan, reverb, chorus):
        self.name = name
        self.channel = channel
        self.program = program
        self.setup = {7: volume, 10: pan, 91: reverb, 93: chorus}
        self.notes = []
        self.controls = []

    def add(self, start, length, pitch, velocity):
        self.notes.append([int(start), int(length), int(pitch), velocity])

    def cc(self, tick, controller, value):
        self.controls.append((int(tick), controller, value))

    def ramp(self, controller, start, end, first, last, step=S):
        count = max(1, (end - start) // step)
        for index in range(count + 1):
            share = index / count
            self.cc(start + index * step, controller, first + (last - first) * share)

    def untangle(self):
        """End each note just before the same key sounds again, as a keyboard would."""
        self.notes.sort()
        latest = {}
        for item in self.notes:
            previous = latest.get(item[2])
            if previous is not None and previous[0] + previous[1] > item[0] - 5:
                previous[1] = max(15, item[0] - 5 - previous[0])
            latest[item[2]] = item

    def between(self, start, end, shortest=0):
        return [
            item
            for item in self.notes
            if item[0] < end and item[0] + item[1] > start and item[1] >= shortest
        ]


def phrase(part, bar, text, shift=0, level=80):
    """Write a line such as 'r:2 A4:1 A4:1 | ~:4 ...' (lengths in sixteenths).

    'r' is a rest and '~' extends the previous note; '|' must fall on a bar line.
    """
    origin = tick = at(bar)
    for token in text.split():
        if token == "|":
            if (tick - origin) % BAR:
                raise ValueError(f"bar line misplaced in bar {bar}: {text}")
            continue
        name, length = token.split(":")
        length = int(length) * S
        if name == "~":
            last = part.notes[-1]
            if last[0] + last[1] != tick:
                raise ValueError(f"tie without a note to extend in bar {bar}")
            last[1] += length
        elif name != "r":
            part.add(tick, length, note(name) + shift, level)
        tick += length
    return tick


def accent(tick):
    step = (tick % BAR) // S
    if step == 0:
        return 6
    if step == 8:
        return 3
    if step % 4 == 0:
        return 2
    return 0 if step % 2 == 0 else -3


def shape(notes, spread=0.55, rng=None):
    """Give written lines a sung contour: stress, length and height."""
    for item in notes:
        start, length, pitch, level = item
        value = level + accent(start) + min(6, length / S / 2) + (pitch - 74) * spread
        if rng:
            value += rng.uniform(-2, 2)
        item[3] = max(20, min(127, round(value)))


RUB = {1: 20, 13: 14, 25: 5, 37: 2}  # minor second and its compounds


def rub(first, second):
    """Cost of a minor second (or minor ninth...) between two pitches.

    A major seventh is fine; only an upper note a semitone above the lower
    one's pitch class rubs.
    """
    lower, upper = sorted((first, second))
    return RUB.get(upper - lower, 0)


def clashes(pitch, others):
    return any(rub(pitch, other) for other in others)


def voicing(chord, tones, low, high, previous, melody=(), avoid=(), size=None, span=16):
    """Place tones in a register, moving smoothly from the previous voicing.

    It stays under the tune, avoids rubbing against the tune or against
    notes other parts already hold, and may drop one tone (never the third
    or the suspended fourth) when that is the only clean way.
    """
    tones = list(tones)
    while size and len(tones) < size:
        tones.append(chord.root)
    keep = {(chord.root + step) % 12 for step in (3, 4, 5)}
    choices = [(tones, 0)]
    if len(tones) >= 3:
        for index, tone in enumerate(tones):
            if tone not in keep:
                choices.append((tones[:index] + tones[index + 1 :], 6))
    best, best_cost = None, None
    for chosen, omitted in choices:
        options = [[p for p in range(low, high + 1) if p % 12 == tone] for tone in chosen]
        for combo in itertools.product(*options):
            notes = sorted(set(combo))
            if len(notes) < len(chosen) or notes[-1] - notes[0] > span:
                continue
            cost = float(omitted)
            for index, lower in enumerate(notes):
                for upper in notes[index + 1 :]:
                    cost += rub(lower, upper)
            for lower, upper in zip(notes, notes[1:]):
                if lower < 57 and upper - lower < 3:
                    cost += 5
            for pitch in melody:
                for tone in notes:
                    cost += 1.2 * rub(tone, pitch)
                    if tone != pitch and abs(tone - pitch) <= 2:
                        cost += 3
                if notes[-1] > pitch + 2:
                    cost += 1.5 * (notes[-1] - pitch - 2)
            for other in avoid:
                for tone in notes:
                    cost += 0.8 * rub(tone, other)
            if previous:
                cost += sum(min(abs(n - p) for p in previous) for n in notes)
                cost += sum(min(abs(p - n) for n in notes) for p in previous)
                cost += 0.5 * abs(notes[-1] - previous[-1])
            else:
                cost += abs(sum(notes) / len(notes) - (low + high) / 2)
            if best_cost is None or cost < best_cost:
                best, best_cost = notes, cost
    if best is None:
        raise ValueError(f"no voicing for {chord} in {low}-{high}")
    return best


def bass_note(pitch_class, previous, low=33, high=50):
    candidates = [p for p in range(low, high + 1) if p % 12 == pitch_class]
    if previous is None:
        return min(candidates, key=lambda p: abs(p - 40))
    return min(candidates, key=lambda p: (abs(p - previous), p))


# --- Song -------------------------------------------------------------------


class Song:
    def __init__(self):
        self.rng = random.Random(SEED)
        self.timeline = Timeline()
        self.parts = {}
        for key, name, channel, program, volume, pan, reverb, chorus in [
            ("flute", "Lead flute", 0, 73, 104, 64, 44, 0),
            ("ep", "Electric piano", 1, 5, 90, 58, 34, 70),
            ("bass", "Bass", 2, 33, 100, 64, 6, 0),
            ("pad", "Strings", 3, 48, 86, 64, 54, 36),
            ("line", "Strings line", 4, 49, 104, 72, 54, 24),
            ("choir", "Choir", 5, 52, 84, 64, 72, 24),
            ("musicbox", "Music box", 6, 10, 96, 76, 60, 0),
            ("glock", "Glockenspiel", 7, 9, 78, 48, 56, 0),
            ("harp", "Harp", 8, 46, 84, 42, 56, 0),
            ("drums", "Drums and percussion", 9, 0, 96, 64, 34, 0),
            ("bells", "Tubular bells", 10, 14, 76, 84, 96, 0),
            ("sweep", "Reverse cymbal", 11, 119, 70, 64, 44, 0),
        ]:
            self.parts[key] = Part(name, channel, program, volume, pan, reverb, chorus)
        self.meta = smf.Track(TITLE)
        self.sung = []  # tune notes carried by parts other than the flute
        self.ep_last = None
        self.pad_last = None
        self.choir_last = None
        self.bass_last = None
        self.left_hand = None

    def human(self, spread):
        return round(self.rng.gauss(0, spread))

    # Tempo --------------------------------------------------------------

    def tempo(self, tick, bpm):
        self.meta.tempo(tick, bpm)

    def glide(self, start, end, first, last, step=S):
        count = max(1, (end - start) // step)
        for index in range(count):
            share = (index + 0.5) / count
            self.tempo(start + index * step, first + (last - first) * share)

    # Melodic helpers ----------------------------------------------------

    def melody_pitches(self, start, end):
        lead = self.parts["flute"].between(start, end, shortest=3 * S)
        lead += [
            item
            for item in self.sung
            if item[0] < end and item[0] + item[1] > start and item[1] >= 3 * S
        ]
        return sorted({item[2] for item in lead})

    def held(self, start, end, keys):
        """Pitches other parts already sound during a chord span."""
        pitches = set()
        for key in keys:
            for item in self.parts[key].between(start + 30, end - 30):
                pitches.add(item[2])
        return sorted(pitches)

    def double(self, source, target, first_bar, last_bar, shift, scale=1.0, shortest=0):
        start, end = at(first_bar), at(last_bar + 1)
        for item in self.parts[source].notes:
            if start <= item[0] < end and item[1] >= shortest:
                self.parts[target].add(item[0], item[1], item[2] + shift, item[3] * scale)

    # Keyboard -----------------------------------------------------------

    def ep_chords(self, first_bar, last_bar, style, level, pedal=None, low=52, high=76, plain=False):
        part = self.parts["ep"]
        spans = self.timeline.within(first_bar, last_bar)
        pedal = style in ("arp", "hold", "ballad", "roll") if pedal is None else pedal
        for start, end, chord in spans:
            length = end - start
            melody = self.melody_pitches(start, end)
            avoid = self.held(start, end, ["musicbox", "line"])
            tones = chord.core if plain else chord.color
            notes = voicing(chord, tones, low, high, self.ep_last, melody, avoid, span=15)
            self.ep_last = notes
            if pedal:
                part.cc(start, 64, 0)
                part.cc(start + 24, 64, 127)
            if style == "hold":
                self.strike(part, start, length - 10, notes, level, roll=10)
            elif style == "stabs":
                for step, size, lift in ((0, 3, 0), (3, 3, -10), (6, 2, -5)):
                    for block in range(0, length, 8 * S):
                        offset = block + step * S
                        if offset < length:
                            held = min(size * S - 25, length - offset - 20)
                            self.strike(part, start + offset, held, notes, level + lift, roll=4)
            elif style == "pulse":
                for step in range(0, length // S, 2):
                    lift = 0 if step % 8 == 0 else (-4 if step % 4 == 0 else -12)
                    self.strike(part, start + step * S, 2 * S - 30, notes, level + lift, roll=3)
            elif style == "sixteenths":
                for step in range(0, length // S):
                    share = (start + step * S - spans[0][0]) / max(1, spans[-1][1] - spans[0][0])
                    lift = (0 if step % 4 == 0 else -14) + 26 * share
                    self.strike(part, start + step * S, S - 20, notes, level + lift, roll=2)
            elif style == "arp":
                order = [0, 1, 2, 3, 2, 1, 2, 3]
                for index, step in enumerate(range(0, length // S, 2)):
                    pitch = notes[order[index % len(order)] % len(notes)]
                    lift = 4 if index == 0 else -6
                    part.add(start + step * S + self.human(4), 2 * S, pitch, level + lift + self.human(3))
            elif style == "ballad":
                root = bass_note(chord.bass, self.left_hand, 38, 50)
                self.left_hand = root
                part.add(start, length - 10, root, level + 2)
                part.add(start + 8, length - 18, root + 12, level - 8)
                self.strike(part, start + 2 * S, length - 2 * S - 10, notes[:2], level - 10, roll=12)
                order = [2, 3, 2, 1]
                for index, step in enumerate(range(4, length // S, 2)):
                    pitch = notes[order[index % len(order)] % len(notes)]
                    part.add(start + step * S + self.human(4), 2 * S, pitch, level - 12 + self.human(3))
            elif style == "roll":
                self.strike(part, start, length - 10, notes, level, roll=36)
            else:
                raise ValueError(style)
        if pedal:
            part.cc(spans[-1][1] - 1, 64, 0)

    def strike(self, part, start, length, notes, level, roll=6):
        for index, pitch in enumerate(notes):
            delay = index * roll + self.human(3)
            part.add(max(0, start + delay), max(30, length - delay), pitch, level + self.human(3))

    # Bass ---------------------------------------------------------------

    def bass(self, first_bar, last_bar, style, level):
        part = self.parts["bass"]
        spans = self.timeline.within(first_bar, last_bar)
        for start, end, chord in spans:
            length = end - start
            root = bass_note(chord.bass, self.bass_last)
            self.bass_last = root
            fifth = root + 7 if root + 7 <= 52 else root - 5
            if style == "whole":
                part.add(start + self.human(3), length - 30, root, level)
            elif style == "ballad":
                for block in range(0, length, 8 * S):
                    size = min(8 * S, length - block)
                    part.add(start + block + self.human(3), size - 2 * S - 20, root, level + (4 if block == 0 else 0))
                    part.add(start + block + size - 2 * S + self.human(3), 2 * S - 30, root + 12 if block else fifth, level - 10)
            elif style == "drive":
                for step in range(0, length // S, 2):
                    part.add(start + step * S + self.human(3), 2 * S - 40, root, level + (4 if step % 4 == 0 else -6))
            elif style == "groove":
                for block in range(0, length, 8 * S):
                    size = min(8 * S, length - block)
                    part.add(start + block + self.human(3), 3 * S - 30, root, level + 4)
                    if size >= 6 * S:
                        part.add(start + block + 3 * S + self.human(3), 3 * S - 30, root, level - 8)
                        part.add(start + block + 6 * S + self.human(3), 2 * S - 40, root + 12, level - 6)
            else:
                raise ValueError(style)

    # Strings and choir --------------------------------------------------

    def pad(self, first_bar, last_bar, level, low=55, high=79, cello=False):
        part = self.parts["pad"]
        for start, end, chord in self.timeline.within(first_bar, last_bar):
            melody = self.melody_pitches(start, end)
            avoid = self.held(start, end, ["ep", "musicbox", "line"])
            notes = voicing(chord, chord.core, low, high, self.pad_last, melody, avoid, size=4, span=19)
            self.pad_last = notes
            for pitch in notes:
                part.add(start + self.human(6), end - start + 30, pitch, level + self.human(3))
            if cello:
                root = bass_note(chord.bass, None, 38, 50)
                part.add(start + self.human(6), end - start + 30, root, level - 6)

    def choir_pad(self, first_bar, last_bar, level, low=57, high=74):
        part = self.parts["choir"]
        for start, end, chord in self.timeline.within(first_bar, last_bar):
            tones = [tone for tone in chord.core if tone != chord.root] or chord.core
            melody = self.melody_pitches(start, end)
            avoid = self.held(start, end, ["ep", "pad", "line", "musicbox"])
            notes = voicing(chord, tones[:3], low, high, self.choir_last, melody, avoid, span=14)
            self.choir_last = notes
            for pitch in notes:
                part.add(start + self.human(8), end - start + 40, pitch, level + self.human(3))

    # Harp ---------------------------------------------------------------

    def harp_arps(self, first_bar, last_bar, level, step=2, pattern=(0, 1, 2, 3, 4, 3, 2, 1)):
        part = self.parts["harp"]
        for start, end, chord in self.timeline.within(first_bar, last_bar):
            base = bass_note(chord.bass, None, 43, 54)
            others = self.held(start, end, ["ep", "pad", "line", "choir"])
            others += self.melody_pitches(start, end)
            ladder = [base]
            for pitch in range(base + 7, base + 32):
                if pitch % 12 in chord.core and pitch % 12 != chord.root and not clashes(pitch, others):
                    ladder.append(pitch)
            ladder = ladder[:6]
            for index, offset in enumerate(range(0, (end - start) // S, step)):
                pitch = ladder[pattern[index % len(pattern)] % len(ladder)]
                begin = start + offset * S + self.human(4)
                length = min(6 * S, end - begin + S)
                part.add(begin, length, pitch, level + (6 if index == 0 else 0) + self.human(4))

    def harp_gliss(self, start, length, low, high, target, level):
        """Sweep up through the tones of the chord the gliss lands on."""
        part = self.parts["harp"]
        tones = set(target.color) | set(target.core)
        landing = self.melody_pitches(start + length, start + length + 4 * S)
        landing += self.held(start, start + length, ["ep", "pad"])
        ladder = [
            p for p in range(low, high + 1) if p % 12 in tones and not clashes(p, landing)
        ]
        for index, pitch in enumerate(ladder):
            share = index / max(1, len(ladder) - 1)
            part.add(start + round(share * length), 5 * S, pitch, level + 26 * share)

    # Percussion ---------------------------------------------------------

    def drums(self, bar, pattern, scale=1.0, spread=4):
        levels = {"X": 118, "x": 96, "o": 74, "g": 46, "-": 60}
        part = self.parts["drums"]
        for pitch, steps in pattern.items():
            steps = steps.replace(" ", "")
            for index, mark in enumerate(steps):
                if mark == ".":
                    continue
                velocity = levels[mark] * scale + self.human(3)
                part.add(max(0, at(bar, index) + self.human(spread)), S, pitch, velocity)

    def hit(self, bar, step, pitch, velocity, length=S):
        self.parts["drums"].add(at(bar, step), length, pitch, velocity)

    def sweep(self, end_tick, length, velocity=90):
        self.parts["sweep"].add(end_tick - length, length, 64, velocity)

    def bell(self, bar, step, name, velocity):
        self.parts["bells"].add(at(bar, step), 8 * S, note(name), velocity)


# Groove patterns: sixteen steps per bar (X accent, x normal, o soft, g ghost).
KICK, RIM, SNARE, HAT, PEDAL, OPEN, CRASH = 36, 37, 38, 42, 44, 46, 49
TOM_LOW, TOM_MID, TOM_HIGH, TAMBOURINE = 45, 47, 50, 54
TRIANGLE, SHAKER, JINGLE, CHIMES = 81, 82, 83, 84

INTRO_GROOVE = {
    KICK: "x... .... ..x. ....",
    SNARE: ".... x... .... x...",
    HAT: "x.o. x.o. x.o. x.o.",
    JINGLE: "xgog xgog xgog xgog",
    TAMBOURINE: ".... o... .... o...",
}
VERSE_GROOVE = {
    KICK: "x... .... ..o. ....",
    RIM: ".... x... .... x...",
    HAT: "o.g. o.g. o.g. o.g.",
    JINGLE: ".... o... .... o...",
}
VERSE2_GROOVE = {
    KICK: "x... .... ..o. ....",
    RIM: ".... x... .... x...",
    HAT: "ogog ogog ogog ogog",
    JINGLE: "o.g. o.g. o.g. o.g.",
}
PRE_GROOVE = {
    KICK: "x... .... ..o. ....",
    RIM: ".... x... .... x...",
    HAT: "o.o. o.o. o.o. o.o.",
    JINGLE: "o.g. o.g. o.g. o.g.",
}
PRE_BUILD = {
    KICK: "x... ..o. x.o. ....",
    SNARE: ".... x... .... x...",
    HAT: "x.o. x.o. x.o. x.o.",
    JINGLE: "xgog xgog xgog xgog",
}
CHORUS_GROOVE = {
    KICK: "x... ..o. ..x. ....",
    SNARE: ".... x..g .... x...",
    HAT: "xgog xgog xgog xgog",
    JINGLE: "xgog xgog xgog xgog",
    TAMBOURINE: ".... x... .... x...",
}
CHORUS_TURN = {
    KICK: "x... ..o. ..x. ..o.",
    SNARE: ".... x..g .... x..g",
    HAT: "xgog xgog xgog xg..",
    OPEN: ".... .... .... ..o.",
    JINGLE: "xgog xgog xgog xgog",
    TAMBOURINE: ".... x... .... x...",
}
FINAL_GROOVE = {
    KICK: "x... ..x. ..x. ..o.",
    SNARE: ".... X..g .... X..g",
    HAT: "xgog xgog xgog xgog",
    JINGLE: "XgoG xgog XgoG xgog".replace("G", "o"),
    TAMBOURINE: "..o. x.o. ..o. x.o.",
}
FILL_TO_CHORUS = {
    KICK: "x... .... x... ....",
    SNARE: ".... x... .... ....",
    TOM_HIGH: ".... .... xo.. ....",
    TOM_MID: ".... .... ..xo ....",
    TOM_LOW: ".... .... .... xoxx",
    JINGLE: "xgog xgog xgog xgog",
}
FILL_SMALL = {
    KICK: "x... .... ..x. ....",
    SNARE: ".... x... .... xoxx",
    HAT: "x.o. x.o. x.o. ....",
    JINGLE: "xgog xgog xgog xgog",
}


def build():
    song = Song()
    tl = song.timeline
    parts = song.parts
    flute, glock, box = parts["flute"], parts["glock"], parts["musicbox"]
    line, choir = parts["line"], parts["choir"]

    intro_mb = ["GM7", "A7", "F#m7_11 B9", "Em7 A7sus4"]
    intro_band = ["DM7 Bm7", "GM7 A7", "DM7 Bm7", "Em7 A7"]
    verse = [
        "Dadd9 A/C#", "Bm7 Bm7/A", "GM7 DM7/F#", "Em7 A7sus4:1 A7:1",
        "Dadd9 A/C#", "Bm7 D/A", "GM7 A/G", "F#m7_11 Bm7",
    ]
    pre = [
        "Em7", "F#m7_11", "GM7", "A7sus4 A7",
        "Bm7 Bm7/A", "GM7 A/G", "F#m7_11 B9", "Em7 A7sus4:1 A7:1",
    ]
    chorus = [
        "GM7", "A7", "F#m7_11 B9", "Em7 Em7/D",
        "C#m7b5 F#7b9", "Bm7 Bm7/A", "GM7 Gm6", "D/A A7",
    ]
    bridge = [
        "Bm BmM7/A#", "Bm7/A G#m7b5", "GM7 Gm6", "F#m7_11 B9",
        "Em7 F#m7_11", "GM7 A/G", "F#m7_11 Bm7", "Em7/A A7",
    ]
    final = [
        "AbM7", "Bb7", "Gm7_11 C9", "Fm7 Fm7/Eb",
        "Dm7b5 G7b9", "Cm7 Cm7/Bb", "AbM7 Abm6", "Eb/Bb Bb7",
    ]
    tag = ["Cm7 Cm7/Bb", "AbM7 Abm6", "Eb/Bb Bb7", "Ebadd9"]
    outro = ["AbM7", "Bb7sus4 Bb7", "Abm6", "Ebadd9"]

    sections = [
        (1, "Intro: music box", intro_mb),
        (5, "Intro", intro_band),
        (9, "Verse 1", verse),
        (17, "Pre-chorus 1", pre),
        (25, "Chorus 1", chorus),
        (33, "Interlude", intro_band),
        (37, "Verse 2", verse),
        (45, "Pre-chorus 2", pre),
        (53, "Chorus 2", chorus),
        (61, "Bridge", bridge),
        (69, "Quiet chorus", chorus[:4]),
        (73, "Key change", ["Bb7sus4 Bb7"]),
        (74, "Final chorus", final),
        (82, "Tag", tag),
        (86, "Outro: music box", outro),
    ]
    for bar, label, chart in sections:
        tl.chart(bar, chart)
        song.meta.marker(at(bar), label)

    # Tempo, meter and key ---------------------------------------------------
    song.meta.text(0, "Composed as code for the Variora christmas-eve prompt by claude-opus-5-5.")
    song.meta.time_signature(0, 4, 4)
    song.meta.key_signature(0, 2)
    song.tempo(0, TEMPO)
    song.glide(at(4, 8), at(5), TEMPO, 62)  # music box breathes before the band
    song.tempo(at(5), TEMPO)
    song.tempo(at(68, 8), 44)  # fermata on the bridge's last chord
    song.tempo(at(68, 12), 78)
    song.tempo(at(69), 80)  # the quiet chorus sits back a little
    song.glide(at(73), at(73, 8), 80, TEMPO, step=2 * S)
    song.tempo(at(73, 8), TEMPO)
    song.meta.key_signature(at(73), -3)
    song.glide(at(87), at(89), TEMPO, 64, step=2 * S)
    song.tempo(at(89), 58)

    # Lead line ---------------------------------------------------------------
    riff = [
        "r:2 A4:1 D5:1 F#5:3 E5:1 D5:2 B4:2 D5:4",
        "r:2 B4:1 D5:1 G5:3 F#5:1 E5:2 C#5:2 E5:4",
        "r:2 A4:1 D5:1 F#5:3 E5:1 D5:2 F#5:2 B5:4",
        "G5:3 F#5:1 E5:2 D5:2 E5:4 C#5:4",
    ]
    verse_line = [
        "r:2 A4:1 A4:1 A4:2 B4:2 A4:3 F#4:1 E4:4",
        "r:2 D4:1 E4:1 F#4:2 A4:2 F#4:8",
        "r:2 B4:1 B4:1 B4:2 D5:2 C#5:3 B4:1 A4:4",
        "r:2 G4:1 A4:1 B4:2 D5:2 D5:4 C#5:4",
        "r:2 A4:1 A4:1 A4:2 D5:2 C#5:3 B4:1 A4:4",
        "r:2 F#4:1 E4:1 D4:2 F#4:2 A4:8",
        "r:2 B4:1 B4:1 B4:2 D5:2 E5:3 D5:1 C#5:4",
        "r:2 A4:1 B4:1 C#5:2 E5:2 D5:6 r:2",
    ]
    verse_line_2 = list(verse_line)
    verse_line_2[2] = "r:2 B4:1 B4:1 B4:2 D5:2 C#5:2 D5:1 B4:1 A4:4"
    verse_line_2[6] = "r:2 B4:1 B4:1 B4:2 D5:2 E5:2 F#5:1 E5:1 C#5:4"
    pre_line = [
        "r:2 G4:2 B4:4 D5:2 E5:6",
        "r:2 A4:2 C#5:4 E5:2 F#5:6",
        "r:2 B4:2 D5:4 F#5:4 E5:2 D5:2",
        "E5:6 D5:2 C#5:6 r:2",
        "r:2 D5:2 C#5:2 D5:2 F#5:6 E5:2",
        "D5:6 B4:2 C#5:2 D5:2 E5:4",
        "F#5:6 E5:2 D#5:4 F#5:4",
        "G5:6 F#5:2 E5:4 D5:2 E5:2",
    ]
    hook = [
        "F#5:6 E5:2 F#5:2 A5:4 G5:2",
        "E5:6 C#5:2 E5:6 F#5:2",
        "A5:6 G5:2 F#5:4 D#5:2 E5:2",
    ]
    chorus_line = hook + [
        "~:4 r:2 B4:2 E5:2 F#5:2 G5:2 A5:2",
        "B5:6 A5:2 A#5:8",
        "B5:6 A5:2 F#5:6 E5:2",
        "D5:6 E5:2 G5:4 E5:2 D5:2",
        "F#5:4 E5:2 D5:2 E5:6 D5:2",
    ]
    bridge_line = [
        "D5:6 C#5:2 D5:4 F#5:4",
        "E5:4 D5:2 C#5:2 B4:4 D5:4",
        "D5:6 E5:2 D5:4 Bb4:4",
        "A4:6 C#5:2 D#5:4 F#5:4",
        "G5:6 F#5:2 E5:4 C#5:4",
        "D5:6 E5:2 E5:4 A5:4",
        "A5:6 F#5:2 B5:6 A5:2",
        "G5:4 F#5:2 E5:2 E5:8",
    ]

    def lines(part, bar, bars, shift=0, level=80):
        for offset, text in enumerate(bars):
            phrase(part, bar + offset, text, shift, level)

    lines(flute, 5, riff, level=86)
    lines(flute, 9, verse_line, level=78)
    lines(flute, 17, pre_line[:4], level=76)
    lines(flute, 21, pre_line[4:], level=82)
    lines(flute, 25, chorus_line, level=90)
    phrase(flute, 33, "~:6 r:10")
    lines(flute, 37, verse_line_2, level=80)
    lines(flute, 45, pre_line[:4], level=78)
    lines(flute, 49, pre_line[4:], level=84)
    lines(flute, 53, chorus_line, level=94)
    phrase(flute, 61, "~:6 r:10")
    lines(flute, 65, bridge_line[4:7], level=80)
    phrase(flute, 68, "G5:4 F#5:2 E5:2 E5:4 D5:2 E5:2", level=76)
    lines(flute, 69, hook, level=68)
    phrase(flute, 72, "~:6 r:10")
    phrase(flute, 73, "r:12 Eb5:2 F5:2", level=86)
    lines(flute, 74, chorus_line, shift=1, level=100)
    lines(flute, 82, [
        "~:6 r:2 Eb5:2 F5:2 G5:2 Bb5:2",
        "C6:6 Bb5:2 Ab5:4 F5:2 Eb5:2",
        "G5:4 F5:2 Eb5:2 F5:6 Eb5:2",
        "~:12 r:4",
    ], level=98)
    shape(flute.notes, rng=song.rng)

    # Bridge melody: choir in unison, strings an octave below.
    lines(choir, 61, bridge_line, level=100)
    shape(choir.notes, spread=0.4)
    song.sung = [list(item) for item in choir.notes]
    lines(line, 61, bridge_line, shift=-12, level=58)

    # Glockenspiel doubles the hooks an octave up.
    song.double("flute", "glock", 5, 8, 12, scale=0.9)
    song.double("flute", "glock", 25, 29, 12, scale=0.8)
    song.double("flute", "glock", 21, 24, 12, scale=0.7, shortest=6 * S)
    song.double("flute", "glock", 49, 52, 12, scale=0.7, shortest=6 * S)
    song.double("flute", "glock", 53, 57, 12, scale=0.8)
    song.double("flute", "glock", 74, 84, 12, scale=0.85)
    lines(glock, 33, riff, shift=12, level=92)
    for bar, text in [
        (38, "r:8 F#6:2 D6:2 B5:2 A5:2"),
        (40, "r:8 D6:2 B5:2 A5:2 E5:2"),
        (42, "r:8 A6:2 F#6:2 D6:2 A5:2"),
        (44, "r:8 F#6:2 D6:2 C#6:2 B5:2"),
    ]:
        phrase(glock, bar, text, level=64)
    lines(line, 33, riff, level=96)
    song.sung += [list(item) for item in line.notes if at(33) <= item[0] < at(37)]

    # Guide-tone line under the final chorus.
    lines(line, 74, [
        "G4:16", "Ab4:16", "F4:8 E4:8", "Eb4:8 Ab4:8",
        "C5:8 B4:8", "Bb4:8 G4:8", "C5:8 Cb5:8", "Bb4:8 Ab4:8",
        "G4:8 Bb4:8", "C5:8 Cb5:8", "Bb4:8 Ab4:8", "G4:16",
    ], level=70)

    # Music box: the hook as a lullaby at both ends, and over the quiet chorus.
    box_intro = [
        ("F#6:6 E6:2 F#6:2 A6:4 G6:2", "G4:4 D5:4 F#5:4 D5:4"),
        ("E6:6 C#6:2 E6:6 F#6:2", "A4:4 E5:4 G5:4 E5:4"),
        ("A6:6 G6:2 F#6:4 D#6:2 E6:2", "F#4:4 C#5:4 B3:4 D#5:4"),
        ("~:6 r:2 D6:8", "E4:4 G4:4 A3:4 D5:4"),
    ]
    box_outro = [
        ("G6:6 F6:2 G6:2 Bb6:4 Ab6:2", "Ab4:4 Eb5:4 G5:4 Eb5:4"),
        ("F6:6 Eb6:2 D6:8", "Bb3:4 F4:4 D5:4 Ab5:4"),
        ("Eb6:6 F6:2 Eb6:4 Cb6:4", "Ab3:4 Eb4:4 Cb5:4 F5:4"),
        ("Bb5:4 Eb6:12", "Eb4:16"),
    ]
    lines(box, 1, [top for top, _ in box_intro], level=82)
    lines(box, 1, [low for _, low in box_intro], level=60)
    lines(box, 69, hook, shift=12, level=50)
    lines(box, 86, [top for top, _ in box_outro], level=80)
    lines(box, 86, [low for _, low in box_outro], level=58)
    for index, name in enumerate(["Bb4", "G5"]):
        box.add(at(89) + 40 * (index + 1), 12 * S, note(name), 56)
    shape(box.notes, spread=0.3)

    # Keyboard ---------------------------------------------------------------
    song.ep_chords(3, 4, "roll", 42)
    song.ep_chords(5, 8, "stabs", 70, low=55, high=79)
    song.ep_chords(9, 16, "arp", 60)
    song.ep_chords(17, 20, "hold", 58)
    song.ep_chords(21, 24, "pulse", 66)
    song.ep_chords(25, 32, "stabs", 72, low=55, high=79)
    song.ep_chords(33, 36, "stabs", 70, low=55, high=79)
    song.ep_chords(37, 44, "hold", 54, plain=True)
    song.ep_chords(45, 48, "hold", 58)
    song.ep_chords(49, 52, "pulse", 68)
    song.ep_chords(53, 60, "stabs", 74, low=55, high=79)
    song.ep_chords(61, 64, "hold", 52, plain=True)
    song.ep_chords(65, 67, "arp", 60, plain=True)
    song.ep_chords(68, 68, "hold", 62)
    song.ep_chords(69, 72, "ballad", 60)
    song.ep_chords(73, 73, "sixteenths", 58, low=56, high=80)
    song.ep_chords(74, 84, "stabs", 78, low=56, high=80)
    song.ep_chords(85, 85, "roll", 64)
    song.ep_chords(86, 89, "roll", 50)

    # Bass --------------------------------------------------------------------
    song.bass(5, 8, "groove", 80)
    song.bass(9, 16, "ballad", 72)
    song.bass(17, 20, "ballad", 84)
    song.bass(21, 24, "drive", 86)
    song.bass(25, 32, "groove", 92)
    song.bass(33, 36, "groove", 80)
    song.bass(37, 44, "ballad", 74)
    song.bass(45, 48, "ballad", 86)
    song.bass(49, 52, "drive", 88)
    song.bass(53, 60, "groove", 94)
    song.bass(61, 64, "whole", 66)
    song.bass(65, 67, "ballad", 84)
    song.bass(68, 68, "whole", 86)
    song.bass(73, 73, "drive", 88)
    song.bass(74, 84, "groove", 98)
    song.bass(85, 85, "whole", 90)
    song.bass(86, 89, "whole", 60)

    # Strings pad -------------------------------------------------------------
    pad = parts["pad"]
    song.pad(3, 4, 46)
    song.pad(5, 8, 62)
    song.pad(13, 16, 50)
    song.pad(17, 24, 64)
    song.pad(25, 36, 76, cello=True)
    song.pad(37, 44, 54)
    song.pad(45, 52, 66)
    song.pad(53, 60, 80, cello=True)
    song.pad(65, 68, 66, cello=True)
    song.pad(69, 72, 40)
    song.pad(73, 73, 70)
    song.pad(74, 85, 86, cello=True)
    song.pad(86, 89, 60)
    pad.cc(0, 11, 100)
    pad.ramp(11, at(17), at(24, 12), 72, 112, step=2 * S)
    pad.ramp(11, at(24, 12), at(25), 112, 100, step=S)
    pad.ramp(11, at(45), at(52, 12), 72, 114, step=2 * S)
    pad.ramp(11, at(52, 12), at(53), 114, 100, step=S)
    pad.ramp(11, at(61), at(68, 8), 80, 116, step=2 * S)
    pad.cc(at(69), 11, 88)
    pad.ramp(11, at(73), at(74), 80, 118, step=S)
    pad.cc(at(74), 11, 108)
    pad.ramp(11, at(88), at(90), 100, 60, step=2 * S)

    line.cc(0, 11, 127)
    line.cc(at(61), 11, 112)
    line.cc(at(74), 11, 86)

    # Choir -------------------------------------------------------------------
    song.choir_pad(29, 32, 58)
    song.choir_pad(53, 60, 60)
    song.choir_pad(74, 85, 80)
    song.choir_pad(89, 89, 56)
    choir.cc(0, 11, 100)
    choir.ramp(11, at(61), at(68, 8), 110, 124, step=2 * S)
    choir.cc(at(69), 11, 100)

    # Harp --------------------------------------------------------------------
    song.harp_gliss(at(24, 12), 4 * S - 20, note("D4"), note("F#6"), Chord("GM7"), 52)
    song.harp_gliss(at(52, 12), 4 * S - 20, note("D4"), note("F#6"), Chord("GM7"), 54)
    song.harp_gliss(at(73, 10), 6 * S - 20, note("Eb4"), note("G6"), Chord("AbM7"), 56)
    song.harp_arps(37, 44, 56)
    song.harp_arps(61, 64, 44, step=1, pattern=(0, 1, 2, 3, 4, 5, 4, 3, 2, 3, 4, 5, 4, 3, 2, 1))
    song.harp_arps(65, 67, 56)
    for index, name in enumerate(["Eb3", "Bb3", "Eb4", "G4", "Bb4", "F5", "G5", "Bb5"]):
        parts["harp"].add(at(89) + index * 55, 14 * S, note(name), 54 + index * 2)

    # Tubular bells -----------------------------------------------------------
    song.bell(1, 0, "D5", 70)
    song.bell(25, 0, "G4", 66)
    song.bell(53, 0, "G4", 70)
    song.bell(61, 0, "D5", 62)
    song.bell(63, 0, "D5", 56)
    song.bell(74, 0, "Ab4", 78)
    song.bell(89, 0, "Eb4", 70)
    song.bell(89, 0, "Eb5", 64)

    # Drums and percussion ----------------------------------------------------
    song.hit(1, 0, CHIMES, 70)
    song.hit(4, 12, CHIMES, 64)
    song.sweep(at(5), 8 * S, 80)
    song.hit(5, 0, CRASH, 86)
    song.hit(5, 0, TRIANGLE, 72)
    for bar in range(5, 8):
        song.drums(bar, INTRO_GROOVE, 0.9)
    song.drums(8, FILL_SMALL, 0.85)
    for bar in range(9, 17):
        song.drums(bar, VERSE_GROOVE, 0.85)
    song.hit(16, 14, OPEN, 56)
    for bar in range(17, 21):
        song.drums(bar, PRE_GROOVE, 0.9)
    for bar in range(21, 24):
        song.drums(bar, PRE_BUILD, 0.92)
    song.drums(24, FILL_TO_CHORUS, 0.95)
    song.sweep(at(25), BAR, 84)
    for first in (25, 53):
        # Chorus 1 hands its last bar to the fill into the interlude.
        for offset in range(7 if first == 25 else 8):
            groove = CHORUS_TURN if offset in (3, 7) else CHORUS_GROOVE
            song.drums(first + offset, groove, 0.95 if first == 25 else 1.0)
        song.hit(first, 0, CRASH, 100)
        song.hit(first + 4, 0, CRASH, 92)
        song.hit(first, 0, TRIANGLE, 70)
        song.hit(first + 4, 0, TRIANGLE, 62)
    song.drums(32, FILL_SMALL, 0.9)
    song.hit(33, 0, CRASH, 86)
    song.hit(33, 0, TRIANGLE, 68)
    for bar in range(33, 36):
        song.drums(bar, INTRO_GROOVE, 0.9)
    song.drums(36, FILL_SMALL, 0.85)
    for bar in range(37, 45):
        song.drums(bar, VERSE2_GROOVE, 0.88)
    song.hit(44, 14, OPEN, 58)
    for bar in range(45, 49):
        song.drums(bar, PRE_GROOVE, 0.92)
    for bar in range(49, 52):
        song.drums(bar, PRE_BUILD, 0.95)
    song.drums(52, FILL_TO_CHORUS, 1.0)
    song.sweep(at(53), BAR, 90)
    song.hit(61, 0, CRASH, 70)
    song.hit(61, 0, TRIANGLE, 60)
    song.hit(60, 12, CHIMES, 58)
    for bar in range(61, 65):
        song.hit(bar, 0, KICK, 64)
    for bar in range(65, 67):
        song.drums(bar, VERSE_GROOVE, 0.8)
    song.drums(67, {
        KICK: "x... .... ..o. ....",
        RIM: ".... x... .... ....",
        SNARE: ".... .... gggo ooxx",
        HAT: "o.g. o.g. .... ....",
    }, 0.85, spread=2)
    song.hit(68, 8, KICK, 96)
    song.hit(68, 8, CRASH, 90)
    song.hit(69, 0, CHIMES, 60)
    song.hit(69, 0, TRIANGLE, 50)
    song.drums(73, {
        KICK: "x... .... x... x...",
        SNARE: "gggg oooo xxxx XXXX",
    }, 0.85, spread=2)
    song.hit(73, 8, CHIMES, 72)
    song.sweep(at(74), BAR, 96)
    for offset in range(10):
        groove = FINAL_GROOVE if offset not in (3, 7) else CHORUS_TURN
        song.drums(74 + offset, groove, 1.0)
    for bar in (74, 78, 82):
        song.hit(bar, 0, CRASH, 108)
        song.hit(bar, 0, TRIANGLE, 74)
    song.drums(84, FILL_SMALL, 1.0)
    song.hit(85, 0, CRASH, 100)
    song.hit(85, 0, KICK, 96)
    for bar in (86, 87, 88):
        song.drums(bar, {JINGLE: "o... g... o... g..."}, 0.9 - 0.12 * (bar - 86))
    song.hit(89, 0, CHIMES, 66)
    song.hit(89, 0, TRIANGLE, 64)

    return song


def write(song):
    tracks = [song.meta]
    for part in song.parts.values():
        part.untangle()
        track = smf.Track(part.name)
        channel = part.channel
        if channel != 9:
            track.program(0, channel, part.program)
        for controller, value in part.setup.items():
            track.control(0, channel, controller, value)
        for tick, controller, value in part.controls:
            track.control(tick, channel, controller, value)
        for start, length, pitch, velocity in part.notes:
            track.note(start, length, channel, pitch, velocity)
        tracks.append(track)
    smf.write(MIDI_PATH, tracks, PPQ)


def main():
    song = build()
    write(song)
    count = sum(len(part.notes) for part in song.parts.values())
    print(f"wrote {MIDI_PATH.name}: {count} notes")


if __name__ == "__main__":
    main()
