"""Compose and render an original seaside walking theme.

Run ``python compose.py`` after installing requirements.txt. The MIDI is
written directly from the note arrangement; the MP3 renders those same notes
with deterministic, sample-free synthesis.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import shutil
import struct
import subprocess
import tempfile
import wave

import numpy as np


BPM = 104
BEATS_PER_BAR = 4
TICKS_PER_BEAT = 480
SAMPLE_RATE = 44_100
SEED = 6_104_2026
HERE = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Note:
    pitch: int
    start: float  # Quarter-note beats from the start of the piece.
    length: float
    velocity: int


@dataclass
class Part:
    name: str
    channel: int
    program: int | None
    pan: float
    gain: float
    notes: list[Note]

    def add(self, pitch: int, start: float, length: float, velocity: int) -> None:
        self.notes.append(Note(pitch, start, length, velocity))


# D major. Each accompaniment voicing leaves the singing register clear.
# The bass notes are explicit so inversions remain audible in both files.
CHORDS: list[tuple[str, int, tuple[int, ...]]] = [
    ("Dmaj9", 38, (54, 57, 62, 64)),
    ("A/C#", 37, (52, 57, 61, 64)),
    ("Bm7", 35, (54, 57, 59, 62)),
    ("Gmaj9", 31, (55, 59, 62, 66)),
    ("Dmaj9", 38, (54, 57, 62, 64)),
    ("A/C#", 37, (52, 57, 61, 64)),
    ("Bm7", 35, (54, 57, 59, 62)),
    ("Gmaj9", 31, (55, 59, 62, 66)),
    ("Em7", 40, (52, 55, 59, 62)),
    ("A7", 33, (52, 55, 57, 61)),
    ("F#m7", 30, (54, 57, 61, 64)),
    ("Bm7", 35, (54, 57, 59, 62)),
    ("Gmaj9", 31, (55, 59, 62, 66)),
    ("A7", 33, (52, 55, 57, 61)),
    ("F#m7", 30, (54, 57, 61, 64)),
    ("Bm7", 35, (54, 57, 59, 62)),
    ("Em7", 40, (52, 55, 59, 62)),
    ("F#m7", 30, (54, 57, 61, 64)),
    ("Gmaj9", 31, (55, 59, 62, 66)),
    ("A7", 33, (52, 55, 57, 61)),
    ("Dmaj9", 38, (54, 57, 62, 64)),
    ("A/C#", 37, (52, 57, 61, 64)),
    ("Bm7", 35, (54, 57, 59, 62)),
    ("Gmaj9", 31, (55, 59, 62, 66)),
    ("Em7", 40, (52, 55, 59, 62)),
    ("A7", 33, (52, 55, 57, 61)),
    ("Dmaj9", 38, (54, 57, 62, 64)),
    ("A7", 33, (52, 55, 57, 61)),
    ("Gmaj9", 31, (55, 59, 62, 66)),
    ("A7", 33, (52, 55, 57, 61)),
    ("Dmaj9", 38, (54, 57, 62, 64)),
    ("Dmaj9", 38, (54, 57, 62, 64)),
]


# (eighth-note position, duration in eighth notes, MIDI pitch), one bar per row.
# Bars 4-11 introduce the theme; 12-19 lift it into the high register;
# 20-27 return to the opening motif with a changed answer.
MELODY: list[tuple[tuple[int, int, int], ...]] = [
    ((0, 2, 74), (2, 1, 78), (3, 1, 76), (4, 2, 74), (6, 2, 69)),
    ((0, 2, 73), (2, 1, 76), (3, 1, 78), (4, 2, 76), (6, 2, 73)),
    ((0, 1, 71), (1, 1, 73), (2, 2, 74), (4, 2, 78), (6, 2, 76)),
    ((0, 2, 74), (2, 2, 71), (4, 2, 69), (6, 2, 66)),
    ((0, 1, 67), (1, 1, 71), (2, 2, 74), (4, 2, 76), (6, 2, 78)),
    ((0, 2, 76), (2, 2, 73), (4, 1, 71), (5, 1, 73), (6, 2, 76)),
    ((0, 2, 78), (2, 1, 76), (3, 1, 74), (4, 2, 73), (6, 2, 69)),
    ((0, 2, 71), (2, 2, 74), (4, 3, 78)),
    ((0, 1, 74), (1, 1, 76), (2, 2, 78), (4, 2, 81), (6, 2, 78)),
    ((0, 1, 76), (1, 1, 78), (2, 2, 79), (4, 2, 76), (6, 2, 73)),
    ((0, 2, 78), (2, 1, 81), (3, 1, 83), (4, 2, 81), (6, 2, 78)),
    ((0, 2, 74), (2, 2, 78), (4, 1, 76), (5, 1, 74), (6, 2, 71)),
    ((0, 1, 67), (1, 1, 71), (2, 2, 74), (4, 2, 79), (6, 2, 78)),
    ((0, 1, 69), (1, 1, 73), (2, 2, 76), (4, 2, 78), (6, 2, 76)),
    ((0, 2, 74), (2, 1, 78), (3, 1, 79), (4, 2, 81), (6, 2, 86)),
    ((0, 2, 85), (2, 2, 83), (4, 2, 81), (6, 2, 79)),
    ((0, 2, 74), (2, 1, 78), (3, 1, 76), (4, 2, 74), (6, 2, 69)),
    ((0, 2, 73), (2, 1, 76), (3, 1, 78), (4, 2, 81), (6, 2, 76)),
    ((0, 1, 71), (1, 1, 73), (2, 2, 74), (4, 2, 78), (6, 2, 76)),
    ((0, 2, 74), (2, 2, 71), (4, 2, 69), (6, 2, 71)),
    ((0, 1, 67), (1, 1, 71), (2, 2, 74), (4, 2, 78), (6, 2, 79)),
    ((0, 2, 81), (2, 1, 78), (3, 1, 76), (4, 2, 73), (6, 2, 76)),
    ((0, 2, 78), (2, 1, 76), (3, 1, 74), (4, 2, 69), (6, 2, 74)),
    ((0, 2, 76), (2, 2, 73), (4, 2, 71), (6, 2, 69)),
    ((0, 2, 67), (2, 2, 71), (4, 2, 74), (6, 2, 78)),
    ((0, 2, 76), (2, 2, 73), (4, 2, 71), (6, 2, 69)),
    ((0, 4, 74), (4, 2, 78), (6, 2, 76)),
    ((0, 6, 74),),
]


def arrange() -> list[Part]:
    lead = Part("Sea breeze - flute", 0, 73, 0.02, 0.17, [])
    piano = Part("Footsteps - electric piano", 1, 4, -0.22, 0.12, [])
    celesta = Part("Sun glitter - celesta", 2, 8, 0.42, 0.10, [])
    guitar = Part("Warm light - nylon guitar", 3, 24, 0.25, 0.10, [])
    strings = Part("Open horizon - strings", 4, 48, -0.12, 0.075, [])
    bass = Part("Walking bass", 5, 33, 0.0, 0.17, [])
    drums = Part("Soft walking kit", 9, None, 0.0, 0.12, [])

    for bar, (_, root, chord) in enumerate(CHORDS):
        beat = bar * BEATS_PER_BAR
        quiet = bar < 4 or bar >= 28
        arp_pattern = (0, 2, 1, 3, 2, 1, 2, 3)
        for eighth, chord_index in enumerate(arp_pattern):
            piano.add(chord[chord_index], beat + eighth * 0.5, 0.42,
                      (49 if quiet else 55) + (6 if eighth in (0, 4) else 0))

        if 2 <= bar <= 31:
            pad_velocity = 45 if bar < 4 or bar >= 28 else 56
            for pitch in chord:
                strings.add(pitch - 12, beat, 3.82, pad_velocity)

        if 4 <= bar <= 30:
            bass.add(root, beat, 1.35, 76 if bar < 28 else 62)
            bass.add(root + 7, beat + 2, 0.9, 59 if bar < 28 else 48)
            if bar < 28:
                bass.add(root + 12, beat + 3.5, 0.4, 49)

        if 4 <= bar <= 29:
            for strum_beat in (0.0, 2.0):
                for string, pitch in enumerate(chord[1:]):
                    guitar.add(pitch, beat + strum_beat + string * 0.035,
                               1.2, 44 + (5 if strum_beat == 0 else 0))

        # Celesta frames the flute rather than playing continuously over it.
        if bar < 4 or bar in (7, 11, 15, 19, 23, 27, 28, 29, 30, 31):
            for i, pitch in enumerate((chord[2] + 12, chord[3] + 12,
                                       chord[2] + 12, chord[1] + 12)):
                celesta.add(pitch, beat + 0.5 + i, 0.65,
                            48 if bar < 4 else 42)

        if 4 <= bar <= 29:
            drums.add(36, beat, 0.18, 61 if bar % 4 == 0 else 55)
            drums.add(36, beat + 2, 0.16, 47)
            for backbeat in (1.0, 3.0):
                drums.add(38, beat + backbeat, 0.17, 43)
            for eighth in range(8):
                drums.add(42, beat + eighth * 0.5, 0.09,
                          34 if eighth % 2 == 0 else 27)
            if bar in (11, 19, 27):
                drums.add(45, beat + 3.5, 0.23, 39)
            if bar in (4, 12, 20, 28):
                drums.add(49, beat, 1.0, 35)

    for phrase_bar, phrase in enumerate(MELODY, start=4):
        for eighth, duration, pitch in phrase:
            lead.add(pitch, phrase_bar * 4 + eighth * 0.5,
                     duration * 0.5 * (0.98 if duration >= 4 else 0.91),
                     72 + (7 if eighth in (0, 4) else 0)
                     + (3 if 12 <= phrase_bar < 20 else 0))

    return [lead, piano, celesta, guitar, strings, bass, drums]


def vlq(value: int) -> bytes:
    result = [value & 0x7F]
    value >>= 7
    while value:
        result.insert(0, 0x80 | (value & 0x7F))
        value >>= 7
    return bytes(result)


def midi_track(events: list[tuple[int, int, bytes]]) -> bytes:
    body = bytearray()
    tick_before = 0
    for tick, _, data in sorted(events):
        body += vlq(tick - tick_before) + data
        tick_before = tick
    body += b"\x00\xff\x2f\x00"
    return b"MTrk" + struct.pack(">I", len(body)) + body


def write_midi(parts: list[Part], path: Path) -> None:
    tempo = round(60_000_000 / BPM)
    conductor: list[tuple[int, int, bytes]] = [
        (0, 0, b"\xff\x03\x09Conductor"),
        (0, 1, b"\xff\x51\x03" + tempo.to_bytes(3, "big")),
        (0, 2, b"\xff\x58\x04\x04\x02\x18\x08"),
        (0, 3, b"\xff\x59\x02\x02\x00"),  # Two sharps, major.
    ]
    for bar, label in ((0, "Intro"), (4, "Theme"), (12, "Lift"),
                       (20, "Return"), (28, "Coda")):
        encoded = label.encode("ascii")
        conductor.append((bar * 4 * TICKS_PER_BEAT, 4,
                          b"\xff\x06" + vlq(len(encoded)) + encoded))
    chunks = [midi_track(conductor)]

    for part in parts:
        name = part.name.encode("ascii")
        events: list[tuple[int, int, bytes]] = [
            (0, 0, b"\xff\x03" + vlq(len(name)) + name)
        ]
        if part.program is not None:
            events.append((0, 1, bytes((0xC0 | part.channel, part.program))))
        for note in part.notes:
            on_tick = round(note.start * TICKS_PER_BEAT)
            off_tick = round((note.start + note.length) * TICKS_PER_BEAT)
            events.append((off_tick, 0,
                           bytes((0x80 | part.channel, note.pitch, 0))))
            events.append((on_tick, 2,
                           bytes((0x90 | part.channel, note.pitch,
                                  note.velocity))))
        chunks.append(midi_track(events))

    path.write_bytes(b"MThd" + struct.pack(">IHHH", 6, 1, len(chunks),
                                          TICKS_PER_BEAT) + b"".join(chunks))


def envelope(t: np.ndarray, hold: float, attack: float, release: float) -> np.ndarray:
    rise = np.minimum(1.0, t / max(attack, 0.001))
    fall = np.minimum(1.0, np.maximum(0.0, hold + release - t) / release)
    return rise * fall


def high_passed_noise(rng: np.random.Generator, size: int,
                      window: int) -> np.ndarray:
    noise = rng.standard_normal(size).astype(np.float32)
    return noise - np.convolve(noise, np.ones(window) / window,
                               mode="same").astype(np.float32)


def synth_note(part: Part, note: Note) -> np.ndarray:
    kind = part.channel
    if kind == 9:
        tail = {36: 0.36, 38: 0.27, 42: 0.11, 45: 0.34,
                49: 1.05}[note.pitch]
    else:
        tail = {0: 0.25, 1: 0.32, 2: 0.45, 3: 0.24,
                4: 0.62, 5: 0.17}[kind]
    hold = note.length * 60 / BPM
    t = np.arange(max(1, round((hold + tail) * SAMPLE_RATE)),
                  dtype=np.float32) / SAMPLE_RATE
    freq = 440.0 * 2 ** ((note.pitch - 69) / 12)
    phase = 2 * np.pi * freq * t
    rng = np.random.default_rng(SEED + note.pitch * 10_007
                                + round(note.start * 960) + kind * 1_000_003)

    if kind == 0:  # Airy flute with a small delayed vibrato.
        vib = 0.0015 * np.sin(2 * np.pi * 5.1 * t)
        phase = 2 * np.pi * freq * (t + vib * np.minimum(1, t / 0.4))
        tone = (np.sin(phase) + 0.19 * np.sin(2 * phase)
                + 0.055 * np.sin(3 * phase))
        tone += 0.015 * high_passed_noise(rng, len(t), 17)
        env = envelope(t, hold, 0.075, tail)
    elif kind == 1:  # Soft electric piano, with decaying tine partials.
        tone = (np.sin(phase) + 0.35 * np.sin(2.004 * phase)
                + 0.12 * np.sin(3.012 * phase))
        env = envelope(t, hold, 0.006, tail) * np.exp(-t / 1.15)
    elif kind == 2:  # Celesta, intentionally short and glassy.
        tone = (np.sin(phase) + 0.30 * np.sin(2.08 * phase)
                + 0.14 * np.sin(3.93 * phase))
        env = envelope(t, hold, 0.004, tail) * np.exp(-t / 0.75)
    elif kind == 3:  # Nylon-like pluck, with a brief pick transient.
        tone = sum((0.7 ** (n - 1)) * np.sin(n * phase)
                   * np.exp(-t / (1.0 / n)) for n in range(1, 6))
        tone += 0.025 * rng.standard_normal(len(t)) * np.exp(-t / 0.012)
        env = envelope(t, hold, 0.003, tail)
    elif kind == 4:  # Wide, gently chorused synthetic string section.
        tone = sum(np.sin(n * phase) * (0.5 ** (n - 1))
                   for n in range(1, 5))
        tone += 0.34 * np.sin(2 * np.pi * freq * 1.0035 * t)
        env = envelope(t, hold, 0.29, tail)
    elif kind == 5:  # Rounded bass with audible upper harmonics.
        tone = np.sin(phase) + 0.28 * np.sin(2 * phase) + 0.10 * np.sin(3 * phase)
        env = envelope(t, hold, 0.012, tail) * np.exp(-t / 1.8)
    else:
        if note.pitch == 36:  # Kick.
            kick_phase = 2 * np.pi * (52 * t + 72 * 0.026
                                      * (1 - np.exp(-t / 0.026)))
            tone = np.sin(kick_phase) * np.exp(-t / 0.11)
            tone += 0.16 * rng.standard_normal(len(t)) * np.exp(-t / 0.009)
        elif note.pitch == 38:  # Brush snare.
            tone = 0.60 * high_passed_noise(rng, len(t), 23) * np.exp(-t / 0.075)
            tone += 0.35 * np.sin(2 * np.pi * 178 * t) * np.exp(-t / 0.055)
        elif note.pitch == 42:  # Closed hat.
            tone = 0.46 * high_passed_noise(rng, len(t), 31) * np.exp(-t / 0.028)
        elif note.pitch == 45:  # Small tom fill.
            tone = np.sin(2 * np.pi * (150 * t + 45 * 0.05
                                       * (1 - np.exp(-t / 0.05))))
            tone *= np.exp(-t / 0.095)
        else:  # Soft transition cymbal.
            tone = 0.26 * high_passed_noise(rng, len(t), 43) * np.exp(-t / 0.29)
        env = np.ones_like(t)

    return (tone * env * (note.velocity / 90.0)).astype(np.float32)


def reverb(send: np.ndarray, delays: tuple[int, ...]) -> np.ndarray:
    # A small feedback network supplies a room tail without external samples.
    wet = np.zeros_like(send)
    for delay in delays:
        echo = send.copy()
        for start in range(delay, len(send), delay):
            stop = min(len(send), start + delay)
            echo[start:stop] += 0.73 * echo[start - delay:stop - delay]
        wet += echo * 0.25
    return wet


def render(parts: list[Part], path: Path) -> tuple[float, float]:
    seconds = len(CHORDS) * BEATS_PER_BAR * 60 / BPM + 3.0
    frame_count = math.ceil(seconds * SAMPLE_RATE)
    mix = np.zeros((frame_count, 2), dtype=np.float32)
    send = np.zeros(frame_count, dtype=np.float32)

    for part in parts:
        for note in part.notes:
            start = round(note.start * 60 / BPM * SAMPLE_RATE)
            sound = synth_note(part, note) * part.gain
            end = min(frame_count, start + len(sound))
            sound = sound[:end - start]
            pan = part.pan
            if part.channel == 9 and note.pitch == 42:
                pan = 0.22
            mix[start:end, 0] += sound * math.sqrt((1 - pan) / 2)
            mix[start:end, 1] += sound * math.sqrt((1 + pan) / 2)
            if part.channel in (0, 1, 2, 3, 4):
                send[start:end] += sound * (0.40 if part.channel != 4 else 0.28)

    mix[:, 0] += 0.14 * reverb(send, (1277, 1601, 1913, 2309))
    mix[:, 1] += 0.14 * reverb(send, (1301, 1669, 1993, 2357))
    mix = np.tanh(mix * 1.18)
    peak = float(np.max(np.abs(mix)))
    mix *= 10 ** (-1 / 20) / peak  # Peak-normalize to -1 dBFS.
    pcm = np.round(mix * 32767).astype("<i2")

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required to encode the MP3")
    with tempfile.TemporaryDirectory() as temp_dir:
        wav_path = Path(temp_dir) / "seaside_stroll.wav"
        with wave.open(str(wav_path), "wb") as output:
            output.setnchannels(2)
            output.setsampwidth(2)
            output.setframerate(SAMPLE_RATE)
            output.writeframes(pcm.tobytes())
        subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                        "-i", str(wav_path), "-codec:a", "libmp3lame",
                        "-qscale:a", "2", str(path)], check=True)
    return seconds, peak


def main() -> None:
    parts = arrange()
    midi_path = HERE / "seaside_stroll.mid"
    mp3_path = HERE / "seaside_stroll.mp3"
    write_midi(parts, midi_path)
    seconds, pre_master_peak = render(parts, mp3_path)
    print(f"Wrote {midi_path.name} and {mp3_path.name} "
          f"({seconds:.1f} s, pre-normalization peak {pre_master_peak:.3f})")


if __name__ == "__main__":
    main()
