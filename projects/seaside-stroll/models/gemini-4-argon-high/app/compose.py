#!/usr/bin/env python3
"""
Seaside Stroll ("Shonan Breeze & Sunlit Tide")
An original anime-style instrumental piece in Eb Major (52 bars, 4/4, 102 BPM with Coda rallentando).
Generates a Standard MIDI File (seaside_stroll.mid) and renders a stereo MP3 (seaside_stroll.mp3)
using sample-free physical/modal/FM synthesis with NumPy, SciPy, and FFmpeg.
"""

from __future__ import annotations

import math
import os
import shutil
import struct
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy import signal

# ============================================================================
# 1. Musical Constants & Helper Utilities
# ============================================================================

TPQ = 480  # Ticks per quarter note
BEATS_PER_BAR = 4
BAR_TICKS = TPQ * BEATS_PER_BAR  # 1920 ticks per 4/4 bar
SAMPLE_RATE = 44100

NOTE_OFFSETS = {
    "C": 0, "C#": 1, "Db": 1,
    "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "Fb": 4, "E#": 5,
    "F": 5, "F#": 6, "Gb": 6,
    "G": 7, "G#": 8, "Ab": 8,
    "A": 9, "A#": 10, "Bb": 10,
    "B": 11, "Cb": 11,
}


def n(name: str) -> int:
    """Convert note name like 'Eb4', 'F#3', 'Bb5' to MIDI pitch number."""
    name = name.strip()
    if len(name) >= 3 and name[1] in ("#", "b"):
        pitch_class = name[:2]
        octave = int(name[2:])
    else:
        pitch_class = name[:1]
        octave = int(name[1:])
    return (octave + 1) * 12 + NOTE_OFFSETS[pitch_class]


def chord_pitches(names: List[str]) -> List[int]:
    return [n(x) for x in names]


def bt(bar_1based: int, beat_0based: float = 0.0) -> int:
    """Convert 1-based bar number and 0-based beat offset into MIDI ticks."""
    return int(round(((bar_1based - 1) * BEATS_PER_BAR + beat_0based) * TPQ))


def dur(beats: float) -> int:
    """Convert duration in beats into MIDI ticks."""
    return int(round(beats * TPQ))


# ============================================================================
# 2. Standard MIDI File (SMF Format 1) Builder
# ============================================================================

def encode_vlq(value: int) -> bytes:
    value = max(0, int(value))
    out = [value & 0x7F]
    value >>= 7
    while value > 0:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.reverse()
    return bytes(out)


@dataclass
class MidiNote:
    start_tick: int
    end_tick: int
    pitch: int
    velocity: int
    channel: int


@dataclass
class MidiTrackBuilder:
    name: str
    channel: int = 0
    program: Optional[int] = None
    volume: int = 100
    pan: int = 64
    reverb: int = 40
    notes: List[MidiNote] = field(default_factory=list)
    raw_events: List[Tuple[int, int, bytes]] = field(default_factory=list)

    def add_meta(self, tick: int, meta_type: int, payload: bytes, order: int = 0) -> None:
        data = bytes([0xFF, meta_type]) + encode_vlq(len(payload)) + payload
        self.raw_events.append((tick, order, data))

    def add_cc(self, tick: int, controller: int, value: int, order: int = 2) -> None:
        data = bytes([0xB0 | (self.channel & 0x0F), controller & 0x7F, max(0, min(127, value))])
        self.raw_events.append((tick, order, data))

    def add_program_change(self, tick: int, program: int, order: int = 1) -> None:
        data = bytes([0xC0 | (self.channel & 0x0F), program & 0x7F])
        self.raw_events.append((tick, order, data))

    def add_note(
        self,
        start_tick: int,
        duration_ticks: int,
        pitch: int,
        velocity: int,
    ) -> None:
        if duration_ticks <= 0:
            return
        pitch = max(0, min(127, int(pitch)))
        velocity = max(1, min(127, int(velocity)))
        start = max(0, int(start_tick))
        end = max(start + 10, int(start_tick + duration_ticks))
        self.notes.append(MidiNote(start, end, pitch, velocity, self.channel))

    def _resolve_overlaps(self) -> List[MidiNote]:
        """Ensure same-pitch notes on a channel never overlap so MIDI parsers stay clean."""
        by_pitch: Dict[int, List[MidiNote]] = {}
        for note in self.notes:
            by_pitch.setdefault(note.pitch, []).append(note)

        cleaned: List[MidiNote] = []
        for pitch, pnotes in by_pitch.items():
            pnotes.sort(key=lambda x: (x.start_tick, x.end_tick))
            dedup: List[MidiNote] = []
            for note in pnotes:
                if dedup and abs(note.start_tick - dedup[-1].start_tick) <= 8:
                    if note.velocity > dedup[-1].velocity:
                        dedup[-1].velocity = note.velocity
                    dedup[-1].end_tick = max(dedup[-1].end_tick, note.end_tick)
                else:
                    dedup.append(note)
            for i in range(len(dedup) - 1):
                if dedup[i].end_tick >= dedup[i + 1].start_tick - 6:
                    dedup[i].end_tick = max(dedup[i].start_tick + 12, dedup[i + 1].start_tick - 6)
            cleaned.extend(dedup)

        cleaned.sort(key=lambda x: (x.start_tick, x.pitch))
        return cleaned

    def to_mtrk_bytes(self) -> bytes:
        events: List[Tuple[int, int, bytes]] = []
        # Track name meta event
        name_bytes = self.name.encode("utf-8")
        events.append((0, 0, bytes([0xFF, 0x03]) + encode_vlq(len(name_bytes)) + name_bytes))

        if self.program is not None and self.channel != 9:
            events.append((0, 1, bytes([0xC0 | (self.channel & 0x0F), self.program & 0x7F])))
        if self.program is not None or self.channel == 9:
            events.append((0, 2, bytes([0xB0 | (self.channel & 0x0F), 7, self.volume & 0x7F])))
            events.append((0, 2, bytes([0xB0 | (self.channel & 0x0F), 10, self.pan & 0x7F])))
            events.append((0, 2, bytes([0xB0 | (self.channel & 0x0F), 91, self.reverb & 0x7F])))

        events.extend(self.raw_events)

        resolved_notes = self._resolve_overlaps()
        self.notes = resolved_notes
        for note in resolved_notes:
            on_bytes = bytes([0x90 | (self.channel & 0x0F), note.pitch, note.velocity])
            off_bytes = bytes([0x80 | (self.channel & 0x0F), note.pitch, 0])
            events.append((note.start_tick, 4, on_bytes))
            events.append((note.end_tick, 3, off_bytes))

        events.sort(key=lambda item: (item[0], item[1]))

        buf = bytearray()
        last_tick = 0
        for tick, _order, payload in events:
            delta = max(0, tick - last_tick)
            buf.extend(encode_vlq(delta))
            buf.extend(payload)
            last_tick = tick

        # End of track
        buf.extend(encode_vlq(48))
        buf.extend(bytes([0xFF, 0x2F, 0x00]))
        return b"MTrk" + struct.pack(">I", len(buf)) + bytes(buf)


# ============================================================================
# 3. Composition Engine: "Shonan Breeze & Sunlit Tide" (52 Bars in Eb Major)
# ============================================================================

@dataclass
class ChordSpan:
    bar: int          # 1-based bar
    beat: float       # 0-based beat in bar
    length: float     # duration in beats
    symbol: str       # chord label
    bass: str         # bass root note (e.g. 'Eb2')
    fifth: str        # secondary bass note (fifth/octave)
    voicing: List[str]  # mid-register chord tones (for guitar/Rhodes/strings)
    sparkle: List[str]  # upper chord tones (for harp/celesta/vibes)


def build_harmonic_timeline() -> List[ChordSpan]:
    """
    Constructs the full 52-bar harmonic score in Eb Major with anime/city-pop voicings.
    """
    spans: List[ChordSpan] = []

    def add(bar: int, beat: float, length: float, symbol: str, bass: str, fifth: str,
            voicing: List[str], sparkle: List[str]) -> None:
        spans.append(ChordSpan(bar, beat, length, symbol, bass, fifth, voicing, sparkle))

    # --- SECTION 1: Intro: Sea Breeze & Distant Bells (Bars 1-6) ---
    add(1, 0, 4, "Ebmaj9", "Eb2", "Bb2", ["G3", "Bb3", "D4", "F4"], ["Bb4", "D5", "F5", "G5"])
    add(2, 0, 4, "Abmaj9(#11)", "Ab2", "Eb3", ["G3", "C4", "D4", "Eb4"], ["C5", "Eb5", "G5", "Bb5"])
    add(3, 0, 4, "Ebmaj9/G", "G2", "Eb3", ["G3", "Bb3", "D4", "F4"], ["Bb4", "D5", "F5", "Bb5"])
    add(4, 0, 2, "Fm9", "F2", "C3", ["Ab3", "C4", "Eb4", "G4"], ["C5", "Eb5", "G5", "Ab5"])
    add(4, 2, 2, "Abm6", "Ab2", "Eb3", ["Cb3", "Eb4", "F4", "Ab4"], ["B4", "Eb5", "F5", "Ab5"])
    add(5, 0, 4, "Eb/Bb", "Bb1", "F2", ["G3", "Bb3", "D4", "F4"], ["G4", "Bb4", "Eb5", "F5"])
    add(6, 0, 2, "Bb13sus4", "Bb1", "F2", ["Ab3", "C4", "Eb4", "G4"], ["C5", "Eb5", "F5", "G5"])
    add(6, 2, 2, "Bb7(b9)", "Bb1", "F2", ["Ab3", "Cb4", "D4", "F4"], ["Bb4", "D5", "F5", "Ab5"])

    # --- SECTION 2: Theme A: Sunlit Boardwalk (Bars 7-14) ---
    add(7, 0, 4, "Ebmaj9", "Eb2", "Bb2", ["G3", "Bb3", "D4", "F4"], ["Bb4", "D5", "F5", "G5"])
    add(8, 0, 2, "Cm9", "C2", "G2", ["Bb3", "D4", "Eb4", "G4"], ["Bb4", "D5", "Eb5", "G5"])
    add(8, 2, 2, "Gm7", "G2", "D3", ["Bb3", "D4", "F4", "A4"], ["Bb4", "D5", "F5", "G5"])
    add(9, 0, 2, "Abmaj9", "Ab2", "Eb3", ["G3", "Bb3", "C4", "Eb4"], ["C5", "Eb5", "G5", "Bb5"])
    add(9, 2, 2, "Bb13sus4", "Bb2", "F2", ["Ab3", "C4", "Eb4", "G4"], ["C5", "Eb5", "F5", "G5"])
    add(10, 0, 2, "Gm7", "G2", "D3", ["Bb3", "D4", "F4", "A4"], ["Bb4", "D5", "F5", "A5"])
    add(10, 2, 2, "Cm9", "C2", "G2", ["Bb3", "D4", "Eb4", "G4"], ["C5", "Eb5", "G5", "Bb5"])
    add(11, 0, 2, "Fm9", "F2", "C3", ["Ab3", "C4", "Eb4", "G4"], ["C5", "Eb5", "G5", "Ab5"])
    add(11, 2, 2, "Bb13", "Bb1", "F2", ["Ab3", "C4", "D4", "G4"], ["Bb4", "D5", "F5", "G5"])
    add(12, 0, 2, "Gm7", "G2", "D3", ["Bb3", "D4", "F4", "A4"], ["Bb4", "D5", "F5", "G5"])
    add(12, 2, 2, "C7(b9)", "C2", "G2", ["Bb3", "Db4", "E4", "G4"], ["Bb4", "Db5", "E5", "G5"])
    add(13, 0, 2, "Fm9", "F2", "C3", ["Ab3", "C4", "Eb4", "G4"], ["C5", "Eb5", "F5", "Ab5"])
    add(13, 2, 2, "Abm6", "Ab2", "Eb3", ["B3", "Eb4", "F4", "Ab4"], ["B4", "Eb5", "F5", "Ab5"])
    add(14, 0, 2, "Bb13sus4", "Bb1", "F2", ["Ab3", "C4", "Eb4", "G4"], ["C5", "Eb5", "F5", "G5"])
    add(14, 2, 2, "Bb7", "Bb1", "F2", ["Ab3", "C4", "D4", "F4"], ["Bb4", "D5", "F5", "Ab5"])

    # --- SECTION 3: Theme A': Sparkling Tide Pool (Bars 15-22) ---
    add(15, 0, 4, "Ebmaj9", "Eb2", "Bb2", ["G3", "Bb3", "D4", "F4"], ["Bb4", "D5", "F5", "G5"])
    add(16, 0, 2, "Eb/G", "G2", "Eb2", ["Bb3", "D4", "Eb4", "G4"], ["Bb4", "Eb5", "G5", "Bb5"])
    add(16, 2, 2, "Edim7", "E2", "Bb2", ["G3", "Bb3", "Db4", "G4"], ["Bb4", "Db5", "E5", "G5"])
    add(17, 0, 2, "Fm9", "F2", "C3", ["Ab3", "C4", "Eb4", "G4"], ["C5", "Eb5", "G5", "Ab5"])
    add(17, 2, 2, "G7(b9)", "G2", "D3", ["B3", "D4", "F4", "Ab4"], ["B4", "D5", "F5", "Ab5"])
    add(18, 0, 2, "Cm9", "C2", "G2", ["Bb3", "D4", "Eb4", "G4"], ["C5", "Eb5", "G5", "Bb5"])
    add(18, 2, 2, "Eb9/Bb", "Bb2", "F2", ["G3", "Db4", "Eb4", "F4"], ["Bb4", "Db5", "Eb5", "G5"])
    add(19, 0, 2, "Abmaj9", "Ab2", "Eb3", ["G3", "C4", "Eb4", "G4"], ["C5", "Eb5", "G5", "Bb5"])
    add(19, 2, 2, "Abm6", "Ab2", "Eb3", ["B3", "Eb4", "F4", "Ab4"], ["B4", "Eb5", "F5", "Ab5"])
    add(20, 0, 2, "Gm7", "G2", "D3", ["Bb3", "D4", "F4", "A4"], ["Bb4", "D5", "F5", "A5"])
    add(20, 2, 2, "C7(b9)", "C2", "G2", ["Bb3", "Db4", "E4", "G4"], ["Bb4", "Db5", "E5", "G5"])
    add(21, 0, 2, "Fm9", "F2", "C3", ["Ab3", "C4", "Eb4", "G4"], ["C5", "Eb5", "G5", "Ab5"])
    add(21, 2, 2, "Bb13", "Bb1", "F2", ["Ab3", "C4", "D4", "G4"], ["Bb4", "D5", "F5", "G5"])
    add(22, 0, 2, "Ebmaj9", "Eb2", "Bb2", ["G3", "Bb3", "D4", "F4"], ["Bb4", "D5", "Eb5", "G5"])
    add(22, 2, 2, "Eb7(9)", "Eb2", "Bb2", ["G3", "Bb3", "Db4", "F4"], ["Bb4", "Db5", "F5", "G5"])

    # --- SECTION 4: Theme B (Chorus): Wind Over the Pier (Bars 23-30, Royal Road) ---
    add(23, 0, 2, "Abmaj9", "Ab2", "Eb3", ["G3", "C4", "Eb4", "G4"], ["C5", "Eb5", "G5", "Bb5"])
    add(23, 2, 2, "Bb13sus4", "Bb2", "F2", ["Ab3", "C4", "D4", "G4"], ["Bb4", "D5", "F5", "G5"])
    add(24, 0, 2, "Gm7", "G2", "D3", ["Bb3", "D4", "F4", "A4"], ["Bb4", "D5", "F5", "A5"])
    add(24, 2, 2, "Cm9", "C2", "G2", ["Bb3", "D4", "Eb4", "G4"], ["C5", "Eb5", "G5", "Bb5"])
    add(25, 0, 2, "Fm9", "F2", "C3", ["Ab3", "C4", "Eb4", "G4"], ["C5", "Eb5", "G5", "Ab5"])
    add(25, 2, 2, "G7(b9)", "G2", "D3", ["B3", "D4", "F4", "Ab4"], ["B4", "D5", "F5", "G5"])
    add(26, 0, 2, "Cm9", "C2", "G2", ["Bb3", "D4", "Eb4", "G4"], ["C5", "Eb5", "G5", "Bb5"])
    add(26, 2, 2, "Eb9/Bb", "Bb2", "F2", ["G3", "Db4", "Eb4", "F4"], ["Bb4", "Db5", "F5", "G5"])
    add(27, 0, 2, "Abmaj9", "Ab2", "Eb3", ["G3", "C4", "Eb4", "G4"], ["C5", "Eb5", "G5", "Bb5"])
    add(27, 2, 2, "Bb7(b9)", "Bb2", "F2", ["Ab3", "Cb4", "D4", "F4"], ["Bb4", "D5", "F5", "Ab5"])
    add(28, 0, 2, "Gm7", "G2", "D3", ["Bb3", "D4", "F4", "A4"], ["Bb4", "D5", "F5", "A5"])
    add(28, 2, 2, "C7(b9)", "C2", "G2", ["Bb3", "Db4", "E4", "G4"], ["Bb4", "Db5", "E5", "G5"])
    add(29, 0, 2, "Fm9", "F2", "C3", ["Ab3", "C4", "Eb4", "G4"], ["C5", "Eb5", "G5", "Ab5"])
    add(29, 2, 2, "Abm6", "Ab2", "Eb3", ["B3", "Eb4", "F4", "Ab4"], ["B4", "Eb5", "F5", "Ab5"])
    add(30, 0, 2, "Bb13sus4", "Bb1", "F2", ["Ab3", "C4", "Eb4", "G4"], ["C5", "Eb5", "F5", "G5"])
    add(30, 2, 2, "Bb7", "Bb1", "F2", ["Ab3", "C4", "D4", "F4"], ["Bb4", "D5", "F5", "Ab5"])

    # --- SECTION 5: Bridge: Glass Shells & Cloud Shadows (Bars 31-38) ---
    add(31, 0, 4, "Cm9", "C2", "G2", ["Bb3", "D4", "Eb4", "G4"], ["C5", "D5", "Eb5", "G5"])
    add(32, 0, 4, "Gm7", "G2", "D3", ["Bb3", "D4", "F4", "A4"], ["Bb4", "D5", "F5", "A5"])
    add(33, 0, 2, "Abmaj9", "Ab2", "Eb3", ["G3", "C4", "Eb4", "G4"], ["C5", "Eb5", "G5", "Bb5"])
    add(33, 2, 2, "Eb/G", "G2", "Eb2", ["Bb3", "D4", "Eb4", "G4"], ["Bb4", "D5", "Eb5", "G5"])
    add(34, 0, 2, "Fm9", "F2", "C3", ["Ab3", "C4", "Eb4", "G4"], ["C5", "Eb5", "G5", "Ab5"])
    add(34, 2, 2, "G7sus4", "G2", "D3", ["C4", "D4", "F4", "G4"], ["C5", "D5", "F5", "G5"])
    add(35, 0, 2, "Cm9", "C2", "G2", ["Bb3", "D4", "Eb4", "G4"], ["C5", "Eb5", "G5", "Bb5"])
    add(35, 2, 2, "Am7b5", "A2", "Eb3", ["G3", "C4", "Eb4", "G4"], ["C5", "Eb5", "G5", "A5"])
    add(36, 0, 2, "Abmaj9", "Ab2", "Eb3", ["G3", "C4", "Eb4", "G4"], ["C5", "Eb5", "G5", "Bb5"])
    add(36, 2, 2, "Gm7", "G2", "D3", ["Bb3", "D4", "F4", "A4"], ["Bb4", "D5", "F5", "A5"])
    add(37, 0, 2, "Fm9", "F2", "C3", ["Ab3", "C4", "Eb4", "G4"], ["C5", "Eb5", "G5", "Ab5"])
    add(37, 2, 2, "Eb/G", "G2", "Eb3", ["Bb3", "D4", "Eb4", "G4"], ["Bb4", "D5", "Eb5", "G5"])
    add(38, 0, 2, "Abmaj9", "Ab2", "Eb3", ["G3", "C4", "Eb4", "G4"], ["C5", "Eb5", "G5", "Bb5"])
    add(38, 2, 2, "Bb13sus4", "Bb1", "F2", ["Ab3", "C4", "Eb4", "G4"], ["C5", "Eb5", "F5", "Bb5"])

    # --- SECTION 6: Grand Chorus: Golden Horizon (Bars 39-46) ---
    add(39, 0, 2, "Abmaj9", "Ab2", "Eb3", ["G3", "C4", "Eb4", "G4"], ["C5", "Eb5", "G5", "Bb5"])
    add(39, 2, 2, "Bb13", "Bb2", "F2", ["Ab3", "C4", "D4", "G4"], ["Bb4", "D5", "F5", "G5"])
    add(40, 0, 2, "Gm7", "G2", "D3", ["Bb3", "D4", "F4", "A4"], ["Bb4", "D5", "F5", "A5"])
    add(40, 2, 2, "Cm9", "C2", "G2", ["Bb3", "D4", "Eb4", "G4"], ["C5", "Eb5", "G5", "Bb5"])
    add(41, 0, 2, "Fm9", "F2", "C3", ["Ab3", "C4", "Eb4", "G4"], ["C5", "Eb5", "G5", "Ab5"])
    add(41, 2, 2, "G7(b9)", "G2", "D3", ["B3", "D4", "F4", "Ab4"], ["B4", "D5", "F5", "Ab5"])
    add(42, 0, 2, "Cm9", "C2", "G2", ["Bb3", "D4", "Eb4", "G4"], ["C5", "Eb5", "G5", "Bb5"])
    add(42, 2, 2, "Eb9/Bb", "Bb2", "F2", ["G3", "Db4", "Eb4", "F4"], ["Bb4", "Db5", "F5", "G5"])
    add(43, 0, 2, "Abmaj9", "Ab2", "Eb3", ["G3", "C4", "Eb4", "G4"], ["C5", "Eb5", "G5", "Bb5"])
    add(43, 2, 2, "Abm6", "Ab2", "Eb3", ["B3", "Eb4", "F4", "Ab4"], ["B4", "Eb5", "F5", "Ab5"])
    add(44, 0, 2, "Gm7", "G2", "D3", ["Bb3", "D4", "F4", "A4"], ["Bb4", "D5", "F5", "A5"])
    add(44, 2, 2, "C7(b9)", "C2", "G2", ["Bb3", "Db4", "E4", "G4"], ["Bb4", "Db5", "E5", "G5"])
    add(45, 0, 2, "Fm9", "F2", "C3", ["Ab3", "C4", "Eb4", "G4"], ["C5", "Eb5", "G5", "Ab5"])
    add(45, 2, 2, "Bb13", "Bb1", "F2", ["Ab3", "C4", "D4", "G4"], ["Bb4", "D5", "F5", "G5"])
    add(46, 0, 4, "Ebmaj9", "Eb2", "Bb2", ["G3", "Bb3", "D4", "F4"], ["Bb4", "D5", "F5", "G5"])

    # --- SECTION 7: Coda: Footprints in the Wet Sand (Bars 47-52) ---
    add(47, 0, 2, "Abmaj9", "Ab2", "Eb3", ["G3", "C4", "Eb4", "G4"], ["C5", "Eb5", "G5", "Bb5"])
    add(47, 2, 2, "Abm6", "Ab2", "Eb3", ["B3", "Eb4", "F4", "Ab4"], ["B4", "Eb5", "F5", "Ab5"])
    add(48, 0, 2, "Eb/G", "G2", "Eb2", ["Bb3", "D4", "Eb4", "G4"], ["Bb4", "D5", "Eb5", "G5"])
    add(48, 2, 2, "C7(b9)", "C2", "G2", ["Bb3", "Db4", "E4", "G4"], ["Bb4", "Db5", "E5", "G5"])
    add(49, 0, 2, "Fm9", "F2", "C3", ["Ab3", "C4", "Eb4", "G4"], ["C5", "Eb5", "G5", "Ab5"])
    add(49, 2, 2, "Db9(#11)", "Db2", "Ab2", ["F3", "Cb4", "Eb4", "G4"], ["C5", "Eb5", "F5", "G5"])
    add(50, 0, 2, "Ebmaj9/Bb", "Bb1", "F2", ["G3", "Bb3", "D4", "F4"], ["Bb4", "D5", "F5", "G5"])
    add(50, 2, 2, "Bb13sus4", "Bb1", "F2", ["Ab3", "C4", "Eb4", "F4"], ["C5", "Eb5", "F5", "G5"])
    add(51, 0, 4, "Ebmaj9(#11)", "Eb2", "Bb2", ["G3", "Bb3", "D4", "F4"], ["Bb4", "D5", "F5", "A5"])
    add(52, 0, 4, "Ebmaj9", "Eb1", "Eb2", ["G3", "Bb3", "D4", "F4", "G4"], ["Bb4", "D5", "F5", "G5", "Bb5"])

    return spans


def compose_piece() -> Tuple[bytes, List[MidiTrackBuilder], List[Tuple[int, int]]]:
    """
    Build all MIDI tracks and return (midi_file_bytes, tracks, tempo_events).
    """
    rng = np.random.default_rng(20261014)
    spans = build_harmonic_timeline()

    # Track 0: Conductor (Tempo, Time Sig, Key Sig, Section Markers)
    conductor = MidiTrackBuilder(name="Conductor", channel=0, program=None)
    # Time Signature: 4/4
    conductor.add_meta(0, 0x58, bytes([4, 2, 24, 8]), order=0)
    # Key Signature: Eb Major (-3 flats, 0 = major)
    conductor.add_meta(0, 0x59, struct.pack("bb", -3, 0), order=0)

    # Tempo map: (tick, bpm)
    tempo_points = [
        (bt(1, 0), 102.0),
        (bt(31, 0), 98.0),
        (bt(35, 0), 100.0),
        (bt(37, 0), 102.0),
        (bt(39, 0), 104.0),
        (bt(47, 0), 98.0),
        (bt(48, 0), 94.0),
        (bt(49, 0), 89.0),
        (bt(50, 0), 83.0),
        (bt(51, 0), 77.0),
        (bt(52, 0), 72.0),
    ]
    tempo_events_micros: List[Tuple[int, int]] = []
    for tick, bpm in tempo_points:
        micros = int(round(60_000_000 / bpm))
        tempo_events_micros.append((tick, micros))
        conductor.add_meta(tick, 0x51, struct.pack(">I", micros)[1:], order=0)

    section_markers = [
        (bt(1, 0), "Intro: Sea Breeze & Distant Bells"),
        (bt(7, 0), "Theme A: Sunlit Boardwalk"),
        (bt(15, 0), "Theme A': Sparkling Tide Pool"),
        (bt(23, 0), "Chorus: Wind Over the Pier"),
        (bt(31, 0), "Bridge: Glass Shells & Cloud Shadows"),
        (bt(39, 0), "Grand Chorus: Golden Horizon"),
        (bt(47, 0), "Coda: Footprints in the Wet Sand"),
    ]
    for tick, label in section_markers:
        conductor.add_meta(tick, 0x06, label.encode("utf-8"), order=0)

    # Instrument tracks
    flute = MidiTrackBuilder("Flute Lead", channel=0, program=73, volume=110, pan=54, reverb=52)
    violin = MidiTrackBuilder("Solo Violin", channel=1, program=40, volume=102, pan=76, reverb=56)
    guitar = MidiTrackBuilder("Coastal Nylon Guitar", channel=2, program=24, volume=98, pan=42, reverb=38)
    rhodes = MidiTrackBuilder("Rhodes Electric Piano", channel=3, program=4, volume=94, pan=84, reverb=46)
    vibes = MidiTrackBuilder("Vibraphone", channel=4, program=11, volume=90, pan=36, reverb=54)
    celesta = MidiTrackBuilder("Celesta", channel=5, program=8, volume=88, pan=92, reverb=60)
    harp = MidiTrackBuilder("Orchestral Harp", channel=6, program=46, volume=90, pan=30, reverb=62)
    strings = MidiTrackBuilder("Warm String Ensemble", channel=7, program=48, volume=86, pan=64, reverb=68)
    bass = MidiTrackBuilder("Fingered Electric Bass", channel=8, program=33, volume=108, pan=64, reverb=18)
    drums = MidiTrackBuilder("Coastal Percussion", channel=9, program=0, volume=96, pan=64, reverb=28)

    def add_melodic_phrase(
        track: MidiTrackBuilder,
        events: List[Tuple[int, float, float, str, int]],
        legato: float = 0.95,
        humanize_ticks: int = 8,
    ) -> None:
        """
        events: list of (bar, beat, duration_beats, note_name, velocity)
        """
        for bar, beat, d_beats, note_str, vel in events:
            jitter = int(rng.integers(-humanize_ticks, humanize_ticks + 1))
            vel_jitter = int(rng.integers(-3, 4))
            start = max(0, bt(bar, beat) + jitter)
            length = max(24, int(round(dur(d_beats) * legato)))
            track.add_note(start, length, n(note_str), vel + vel_jitter)

    # ------------------------------------------------------------------------
    # A. Lead Melodies (Flute & Solo Violin) + Mallet Doublings (Vibes/Celesta)
    # ------------------------------------------------------------------------

    # Intro Flute motif (Bars 3-6): gentle sea-breeze call
    intro_flute = [
        (3, 0.5, 1.0, "Bb4", 82), (3, 1.5, 0.5, "C5", 80), (3, 2.0, 1.2, "D5", 86), (3, 3.25, 0.7, "Eb5", 84),
        (4, 0.0, 1.5, "C5", 85), (4, 1.5, 0.5, "Bb4", 78), (4, 2.0, 1.8, "Ab4", 82),
        (5, 0.5, 0.5, "G4", 76), (5, 1.0, 1.0, "Bb4", 82), (5, 2.0, 1.0, "F5", 88), (5, 3.0, 0.9, "Eb5", 84),
        (6, 0.0, 2.0, "Eb5", 84), (6, 2.0, 1.7, "D5", 79),
    ]
    add_melodic_phrase(flute, intro_flute, legato=0.94)

    # Theme A (Bars 7-14): Lyrical stroll melody on Flute
    theme_a_flute = [
        # Bar 7 (Ebmaj9)
        (7, 0.0, 1.5, "Bb4", 92), (7, 1.5, 0.5, "C5", 88), (7, 2.0, 1.0, "D5", 94), (7, 3.0, 0.5, "Eb5", 95), (7, 3.5, 0.5, "F5", 92),
        # Bar 8 (Cm9 -> Gm7)
        (8, 0.0, 1.5, "G5", 98), (8, 1.5, 0.5, "F5", 90), (8, 2.0, 1.0, "Eb5", 92), (8, 3.0, 0.9, "D5", 88),
        # Bar 9 (Abmaj9 -> Bb13sus4)
        (9, 0.0, 1.0, "C5", 90), (9, 1.0, 0.5, "Eb5", 92), (9, 1.5, 1.0, "G5", 96), (9, 2.5, 0.5, "F5", 92), (9, 3.0, 0.9, "Eb5", 90),
        # Bar 10 (Gm7 -> Cm9)
        (10, 0.0, 1.5, "D5", 91), (10, 1.5, 0.5, "Bb4", 84), (10, 2.0, 1.7, "G4", 86),
        # Bar 11 (Fm9 -> Bb13)
        (11, 0.0, 1.0, "Ab4", 88), (11, 1.0, 0.5, "C5", 90), (11, 1.5, 1.0, "Eb5", 95), (11, 2.5, 0.5, "D5", 92), (11, 3.0, 0.5, "Eb5", 94), (11, 3.5, 0.5, "F5", 96),
        # Bar 12 (Gm7 -> C7b9)
        (12, 0.0, 1.5, "Bb5", 102), (12, 1.5, 0.5, "A5", 94), (12, 2.0, 1.0, "G5", 98), (12, 3.0, 0.9, "E5", 92),
        # Bar 13 (Fm9 -> Abm6)
        (13, 0.0, 1.0, "F5", 96), (13, 1.0, 0.5, "Eb5", 92), (13, 1.5, 0.5, "C5", 88), (13, 2.0, 1.5, "Cb5", 94), (13, 3.5, 0.5, "Eb5", 90),
        # Bar 14 (Bb13sus4 -> Bb7)
        (14, 0.0, 2.0, "G5", 95), (14, 2.0, 1.6, "F5", 90),
    ]
    add_melodic_phrase(flute, theme_a_flute, legato=0.95)

    # Theme A answering phrases on Vibraphone (Bars 8, 10, 14)
    theme_a_vibes = [
        (8, 2.5, 0.5, "Bb4", 78), (8, 3.0, 0.5, "D5", 80), (8, 3.5, 0.5, "F5", 82),
        (10, 2.0, 0.5, "C5", 80), (10, 2.5, 0.5, "D5", 82), (10, 3.0, 0.5, "Eb5", 84), (10, 3.5, 0.5, "G5", 82),
        (14, 2.0, 0.5, "Bb4", 80), (14, 2.5, 0.5, "C5", 82), (14, 3.0, 0.5, "D5", 85), (14, 3.5, 0.5, "F5", 88),
    ]
    add_melodic_phrase(vibes, theme_a_vibes, legato=1.15)

    # Theme A' (Bars 15-22): Flute + Violin counter-melody + Vibraphone 3rds/6ths
    theme_ap_flute = [
        # Bar 15 (Ebmaj9)
        (15, 0.0, 0.2, "A4", 82), (15, 0.2, 1.3, "Bb4", 95), (15, 1.5, 0.5, "C5", 91), (15, 2.0, 1.0, "D5", 96), (15, 3.0, 0.5, "Eb5", 97), (15, 3.5, 0.5, "F5", 95),
        # Bar 16 (Eb/G -> Edim7)
        (16, 0.0, 1.5, "G5", 100), (16, 1.5, 0.5, "Bb5", 102), (16, 2.0, 1.0, "G5", 96), (16, 3.0, 0.9, "E5", 94),
        # Bar 17 (Fm9 -> G7b9)
        (17, 0.0, 1.0, "F5", 96), (17, 1.0, 0.5, "G5", 95), (17, 1.5, 1.0, "Ab5", 100), (17, 2.5, 0.5, "G5", 96), (17, 3.0, 0.9, "F5", 94),
        # Bar 18 (Cm9 -> Eb9/Bb)
        (18, 0.0, 1.5, "Eb5", 96), (18, 1.5, 0.5, "D5", 92), (18, 2.0, 1.0, "Db5", 94), (18, 3.0, 0.9, "C5", 90),
        # Bar 19 (Abmaj9 -> Abm6)
        (19, 0.0, 1.0, "C5", 94), (19, 1.0, 0.5, "Eb5", 96), (19, 1.5, 1.0, "G5", 100), (19, 2.5, 0.5, "F5", 96), (19, 3.0, 0.9, "Cb5", 94),
        # Bar 20 (Gm7 -> C7b9)
        (20, 0.0, 1.0, "Bb4", 92), (20, 1.0, 1.0, "D5", 95), (20, 2.0, 1.0, "G5", 100), (20, 3.0, 0.9, "E5", 95),
        # Bar 21 (Fm9 -> Bb13)
        (21, 0.0, 1.0, "F5", 98), (21, 1.0, 0.5, "G5", 96), (21, 1.5, 1.0, "Ab5", 102), (21, 2.5, 0.5, "G5", 98), (21, 3.0, 0.5, "F5", 96), (21, 3.5, 0.5, "D5", 92),
        # Bar 22 (Ebmaj9 -> Eb7)
        (22, 0.0, 2.5, "Eb5", 98), (22, 2.5, 0.5, "F5", 94), (22, 3.0, 0.5, "G5", 98), (22, 3.5, 0.5, "Bb5", 102),
    ]
    add_melodic_phrase(flute, theme_ap_flute, legato=0.95)

    theme_ap_violin = [
        # Lyrical counter-melody weaving through Flute phrases
        (15, 2.0, 1.0, "G4", 82), (15, 3.0, 1.0, "Bb4", 85),
        (16, 0.0, 2.0, "Eb5", 88), (16, 2.0, 2.0, "Db5", 86),
        (17, 0.0, 2.0, "C5", 88), (17, 2.0, 2.0, "B4", 88),
        (18, 0.0, 1.5, "C5", 90), (18, 1.5, 0.5, "Bb4", 86), (18, 2.0, 1.8, "G4", 85),
        (19, 0.0, 2.0, "Ab4", 88), (19, 2.0, 2.0, "F4", 86),
        (20, 0.0, 2.0, "G4", 88), (20, 2.0, 2.0, "Bb4", 90),
        (21, 0.0, 2.0, "C5", 92), (21, 2.0, 2.0, "D5", 94),
        (22, 0.0, 2.0, "Bb4", 90), (22, 2.0, 1.8, "Db5", 92),
    ]
    add_melodic_phrase(violin, theme_ap_violin, legato=0.98)

    theme_ap_vibes = [
        (15, 0.0, 1.5, "G4", 82), (15, 2.0, 1.0, "Bb4", 84),
        (16, 0.0, 1.5, "Eb5", 85), (16, 2.0, 1.0, "Bb4", 82),
        (17, 1.5, 1.0, "C5", 86), (18, 0.0, 1.5, "G4", 82),
        (19, 1.5, 1.0, "Eb5", 88), (20, 2.0, 1.0, "Bb4", 84),
        (21, 1.5, 1.0, "C5", 88), (22, 0.0, 2.0, "G4", 85),
    ]
    add_melodic_phrase(vibes, theme_ap_vibes, legato=1.15)

    # Section 4: Chorus (Theme B: Wind Over the Pier, Bars 23-30, Royal Road)
    chorus_flute = [
        # Bar 23 (Abmaj9 -> Bb13sus4)
        (23, 0.0, 1.5, "C6", 104), (23, 1.5, 0.5, "Bb5", 100), (23, 2.0, 1.0, "Ab5", 102), (23, 3.0, 0.5, "G5", 98), (23, 3.5, 0.5, "F5", 96),
        # Bar 24 (Gm7 -> Cm9)
        (24, 0.0, 1.5, "Bb5", 104), (24, 1.5, 0.5, "G5", 96), (24, 2.0, 1.5, "Eb5", 98), (24, 3.5, 0.5, "G5", 94),
        # Bar 25 (Fm9 -> G7b9)
        (25, 0.0, 1.0, "Ab5", 100), (25, 1.0, 0.5, "G5", 96), (25, 1.5, 1.0, "F5", 98), (25, 2.5, 0.5, "G5", 98), (25, 3.0, 0.9, "Ab5", 100),
        # Bar 26 (Cm9 -> Eb9/Bb)
        (26, 0.0, 1.5, "G5", 100), (26, 1.5, 0.5, "F5", 94), (26, 2.0, 1.5, "Eb5", 96), (26, 3.5, 0.5, "Bb5", 100),
        # Bar 27 (Abmaj9 -> Bb7b9)
        (27, 0.0, 1.5, "C6", 106), (27, 1.5, 0.5, "Bb5", 102), (27, 2.0, 1.0, "Ab5", 104), (27, 3.0, 0.5, "G5", 98), (27, 3.5, 0.5, "Ab5", 100),
        # Bar 28 (Gm7 -> C7b9)
        (28, 0.0, 1.5, "Bb5", 105), (28, 1.5, 0.5, "A5", 98), (28, 2.0, 1.0, "G5", 102), (28, 3.0, 0.9, "E5", 96),
        # Bar 29 (Fm9 -> Abm6)
        (29, 0.0, 1.0, "F5", 100), (29, 1.0, 0.5, "G5", 98), (29, 1.5, 1.0, "Ab5", 102), (29, 2.5, 0.5, "Cb5", 96), (29, 3.0, 0.9, "Eb5", 98),
        # Bar 30 (Bb13sus4 -> Bb7)
        (30, 0.0, 2.0, "G5", 100), (30, 2.0, 1.7, "F5", 95),
    ]
    add_melodic_phrase(flute, chorus_flute, legato=0.96)

    chorus_violin = [
        # Violin harmonizes in warm 6ths/3rds and answers the Flute
        (23, 0.0, 1.5, "Eb5", 96), (23, 1.5, 0.5, "D5", 92), (23, 2.0, 1.0, "C5", 94), (23, 3.0, 1.0, "Bb4", 92),
        (24, 0.0, 1.5, "D5", 96), (24, 1.5, 0.5, "Bb4", 90), (24, 2.0, 1.8, "C5", 92),
        (25, 0.0, 1.5, "C5", 94), (25, 1.5, 1.0, "Ab4", 90), (25, 2.5, 1.4, "B4", 94),
        (26, 0.0, 2.0, "Eb5", 96), (26, 2.0, 1.8, "Db5", 94),
        (27, 0.0, 1.5, "Eb5", 98), (27, 1.5, 0.5, "D5", 94), (27, 2.0, 1.0, "C5", 96), (27, 3.0, 1.0, "D5", 95),
        (28, 0.0, 1.5, "D5", 98), (28, 1.5, 0.5, "C5", 94), (28, 2.0, 1.0, "Bb4", 95), (28, 3.0, 0.9, "Db5", 94),
        (29, 0.0, 1.5, "C5", 96), (29, 1.5, 0.5, "Eb5", 96), (29, 2.0, 1.8, "Cb4", 92),
        (30, 0.0, 2.0, "Eb5", 95), (30, 2.0, 1.7, "D5", 92),
    ]
    add_melodic_phrase(violin, chorus_violin, legato=0.98)

    # Celesta doubles key chorus sparkles
    chorus_celesta = [
        (23, 0.0, 1.0, "C6", 84), (23, 2.0, 1.0, "Ab5", 80),
        (24, 0.0, 1.0, "Bb5", 82), (24, 2.0, 1.0, "Eb5", 78),
        (27, 0.0, 1.0, "C6", 86), (27, 2.0, 1.0, "Ab5", 82),
        (28, 0.0, 1.0, "Bb5", 84), (29, 2.0, 1.0, "Ab5", 82),
        (30, 0.0, 1.5, "G5", 80), (30, 2.0, 1.5, "F5", 78),
    ]
    add_melodic_phrase(celesta, chorus_celesta, legato=1.1)

    # Section 5: Bridge: Glass Shells & Cloud Shadows (Bars 31-38)
    # Bars 31-34: Translucent Celesta + Flute dialogue; Bars 35-38: Emotional Violin lead + Flute ascent
    bridge_celesta = [
        (31, 0.0, 1.0, "G5", 82), (31, 1.0, 0.5, "F5", 78), (31, 1.5, 1.5, "Eb5", 84), (31, 3.0, 1.0, "D5", 80),
        (32, 0.0, 1.5, "D5", 82), (32, 1.5, 0.5, "C5", 78), (32, 2.0, 1.8, "Bb4", 80),
        (33, 0.0, 1.0, "C5", 82), (33, 1.0, 1.0, "Eb5", 85), (33, 2.0, 1.0, "G5", 88), (33, 3.0, 1.0, "Bb5", 86),
        (34, 0.0, 2.0, "Ab5", 86), (34, 2.0, 1.8, "G5", 84),
    ]
    add_melodic_phrase(celesta, bridge_celesta, legato=1.1)

    bridge_violin = [
        (33, 0.0, 2.0, "Eb4", 84), (33, 2.0, 2.0, "Bb4", 88),
        (34, 0.0, 2.0, "C5", 90), (34, 2.0, 1.9, "B4", 88),
        # Violin takes the aching bridge solo in Bars 35-38
        (35, 0.0, 1.5, "G5", 98), (35, 1.5, 0.5, "F5", 94), (35, 2.0, 1.0, "Eb5", 98), (35, 3.0, 0.9, "C5", 94),
        (36, 0.0, 1.5, "Eb5", 98), (36, 1.5, 0.5, "F5", 96), (36, 2.0, 1.5, "D5", 96), (36, 3.5, 0.5, "Bb4", 90),
        (37, 0.0, 1.0, "C5", 96), (37, 1.0, 1.0, "Eb5", 98), (37, 2.0, 1.0, "Eb5", 100), (37, 3.0, 1.0, "G5", 102),
        (38, 0.0, 1.5, "Ab5", 104), (38, 1.5, 0.5, "G5", 100), (38, 2.0, 1.0, "F5", 102), (38, 3.0, 0.9, "Bb5", 106),
    ]
    add_melodic_phrase(violin, bridge_violin, legato=0.98)

    bridge_flute = [
        (31, 2.0, 1.5, "C5", 84), (31, 3.5, 0.5, "Bb4", 80),
        (32, 0.0, 2.0, "A4", 82), (32, 2.0, 1.8, "G4", 78),
        (35, 2.0, 1.0, "G5", 88), (35, 3.0, 1.0, "F5", 86),
        (36, 2.0, 1.8, "Bb5", 92),
        (37, 0.0, 1.0, "Ab5", 94), (37, 1.0, 1.0, "G5", 96), (37, 2.0, 1.0, "Bb5", 100), (37, 3.0, 1.0, "Eb5", 96),
        (38, 0.0, 1.0, "C5", 96), (38, 1.0, 1.0, "Eb5", 98), (38, 2.0, 0.5, "F5", 100), (38, 2.5, 0.5, "G5", 102), (38, 3.0, 0.5, "Ab5", 104), (38, 3.5, 0.5, "Bb5", 106),
    ]
    add_melodic_phrase(flute, bridge_flute, legato=0.95)

    # Section 6: Grand Chorus: Golden Horizon (Bars 39-46)
    grand_flute = [
        # Bar 39 (Abmaj9 -> Bb13)
        (39, 0.0, 1.5, "C6", 108), (39, 1.5, 0.5, "Bb5", 104), (39, 2.0, 1.0, "Ab5", 106), (39, 3.0, 0.5, "Bb5", 105), (39, 3.5, 0.5, "C6", 108),
        # Bar 40 (Gm7 -> Cm9)
        (40, 0.0, 1.5, "D6", 110), (40, 1.5, 0.5, "Bb5", 104), (40, 2.0, 1.5, "G5", 104), (40, 3.5, 0.5, "Eb5", 98),
        # Bar 41 (Fm9 -> G7b9)
        (41, 0.0, 1.0, "Ab5", 104), (41, 1.0, 0.5, "G5", 100), (41, 1.5, 1.0, "F5", 102), (41, 2.5, 0.5, "G5", 102), (41, 3.0, 0.9, "Ab5", 105),
        # Bar 42 (Cm9 -> Eb9/Bb)
        (42, 0.0, 1.5, "G5", 104), (42, 1.5, 0.5, "Bb5", 104), (42, 2.0, 1.5, "Eb6", 110), (42, 3.5, 0.5, "Db6", 106),
        # Bar 43 (Abmaj9 -> Abm6)
        (43, 0.0, 1.5, "C6", 108), (43, 1.5, 0.5, "Bb5", 104), (43, 2.0, 1.0, "Cb6", 106), (43, 3.0, 0.9, "Ab5", 102),
        # Bar 44 (Gm7 -> C7b9)
        (44, 0.0, 1.5, "Bb5", 106), (44, 1.5, 0.5, "A5", 100), (44, 2.0, 1.0, "G5", 104), (44, 3.0, 0.9, "E5", 98),
        # Bar 45 (Fm9 -> Bb13)
        (45, 0.0, 1.0, "F5", 102), (45, 1.0, 0.5, "G5", 102), (45, 1.5, 1.0, "Ab5", 106), (45, 2.5, 0.5, "Bb5", 106), (45, 3.0, 0.5, "G5", 102), (45, 3.5, 0.5, "F5", 100),
        # Bar 46 (Ebmaj9)
        (46, 0.0, 3.0, "Eb5", 104), (46, 3.0, 0.9, "Bb5", 98),
    ]
    add_melodic_phrase(flute, grand_flute, legato=0.96)

    grand_violin = [
        (39, 0.0, 1.5, "Eb5", 100), (39, 1.5, 0.5, "D5", 96), (39, 2.0, 1.0, "C5", 98), (39, 3.0, 1.0, "D5", 98),
        (40, 0.0, 1.5, "F5", 102), (40, 1.5, 0.5, "D5", 96), (40, 2.0, 1.8, "Eb5", 98),
        (41, 0.0, 1.5, "C5", 98), (41, 1.5, 1.0, "Ab4", 94), (41, 2.5, 1.4, "B4", 98),
        (42, 0.0, 2.0, "Eb5", 100), (42, 2.0, 2.0, "G5", 102),
        (43, 0.0, 1.5, "Eb5", 102), (43, 1.5, 0.5, "D5", 98), (43, 2.0, 1.0, "Eb5", 100), (43, 3.0, 1.0, "Cb5", 96),
        (44, 0.0, 1.5, "D5", 100), (44, 1.5, 0.5, "C5", 96), (44, 2.0, 1.0, "Bb4", 98), (44, 3.0, 0.9, "Db5", 96),
        (45, 0.0, 1.0, "C5", 98), (45, 1.0, 0.5, "Bb4", 96), (45, 1.5, 1.0, "C5", 100), (45, 2.5, 0.5, "D5", 100), (45, 3.0, 1.0, "D5", 98),
        (46, 0.0, 3.5, "Bb4", 98),
    ]
    add_melodic_phrase(violin, grand_violin, legato=0.98)

    grand_vibes = [
        (39, 0.0, 1.0, "Eb5", 88), (39, 1.5, 0.5, "F5", 86), (39, 2.0, 1.0, "Ab5", 90), (39, 3.0, 1.0, "Bb5", 90),
        (40, 0.0, 1.5, "Bb5", 92), (40, 2.0, 1.5, "G5", 88),
        (41, 0.0, 1.0, "C5", 86), (41, 1.5, 1.0, "Eb5", 88), (41, 2.5, 1.5, "D5", 88),
        (42, 0.0, 1.5, "Eb5", 88), (42, 2.0, 1.5, "G5", 90),
        (43, 0.0, 1.5, "Ab5", 92), (43, 2.0, 1.5, "F5", 88),
        (44, 0.0, 1.5, "G5", 90), (44, 2.0, 1.5, "E5", 88),
        (45, 0.0, 1.5, "F5", 90), (45, 1.5, 1.0, "Ab5", 92), (45, 2.5, 1.5, "D5", 88),
        (46, 0.0, 2.5, "Eb5", 90),
    ]
    add_melodic_phrase(vibes, grand_vibes, legato=1.15)

    grand_celesta = [
        (39, 0.0, 1.0, "C6", 88), (40, 0.0, 1.0, "D6", 90), (40, 2.0, 1.0, "G5", 84),
        (42, 2.0, 1.0, "Eb6", 90), (43, 0.0, 1.0, "C6", 88), (43, 2.0, 1.0, "Cb6", 86),
        (45, 1.5, 1.0, "Ab5", 88), (46, 0.0, 2.0, "G5", 86),
    ]
    add_melodic_phrase(celesta, grand_celesta, legato=1.15)

    # Section 7: Coda: Footprints in the Wet Sand (Bars 47-52)
    coda_flute = [
        (47, 0.0, 1.5, "C6", 94), (47, 1.5, 0.5, "Bb5", 90), (47, 2.0, 1.5, "Cb5", 88), (47, 3.5, 0.5, "Eb5", 86),
        (48, 0.0, 1.5, "Bb5", 92), (48, 1.5, 0.5, "G5", 86), (48, 2.0, 1.8, "E5", 84),
        (49, 0.0, 1.5, "F5", 88), (49, 1.5, 0.5, "Eb5", 84), (49, 2.0, 1.8, "G5", 86),
        (50, 0.0, 2.0, "F5", 84), (50, 2.0, 1.8, "D5", 80),
        (51, 0.0, 3.5, "Eb5", 82),
        (52, 0.0, 3.8, "Bb4", 76),
    ]
    add_melodic_phrase(flute, coda_flute, legato=0.96)

    coda_violin = [
        (47, 0.0, 2.0, "Eb5", 86), (47, 2.0, 2.0, "F4", 82),
        (48, 0.0, 2.0, "G4", 84), (48, 2.0, 2.0, "Bb4", 82),
        (49, 0.0, 2.0, "Ab4", 82), (49, 2.0, 2.0, "Cb4", 80),
        (50, 0.0, 2.0, "Bb4", 80), (50, 2.0, 2.0, "Ab4", 76),
        (51, 0.0, 3.8, "G4", 76),
    ]
    add_melodic_phrase(violin, coda_violin, legato=0.98)

    coda_celesta = [
        (47, 0.0, 1.5, "G5", 80), (47, 2.0, 1.5, "F5", 78),
        (49, 2.0, 1.5, "Eb5", 78),
        (51, 0.5, 1.0, "Bb5", 78), (51, 1.5, 1.0, "D6", 76), (51, 2.5, 1.5, "F6", 74),
        (52, 0.0, 3.8, "G6", 72),
    ]
    add_melodic_phrase(celesta, coda_celesta, legato=1.2)

    # ------------------------------------------------------------------------
    # B. Accompaniment & Ensemble Tracks across all 52 Bars
    # ------------------------------------------------------------------------

    for span in spans:
        bar = span.bar
        b0 = span.beat
        length = span.length
        v_pitches = chord_pitches(span.voicing)
        s_pitches = chord_pitches(span.sparkle)
        bass_root = n(span.bass)
        bass_fifth = n(span.fifth)

        # 1. Orchestral Harp: Shimmering arpeggios in Intro, Chorus transitions, Bridge, and Coda
        if bar in (1, 2, 3, 4, 5, 6, 15, 22, 23, 27, 30, 31, 33, 38, 39, 43, 46, 47, 49, 51, 52):
            arp_notes = v_pitches[:2] + s_pitches
            step = 0.5 if length >= 4 else 0.25
            count = min(len(arp_notes), int(length / step))
            for idx in range(count):
                vel = 74 + (idx * 2) - (8 if bar >= 48 else 0)
                harp.add_note(
                    bt(bar, b0 + idx * step),
                    dur(min(2.5, length - idx * step + 0.5)),
                    arp_notes[idx % len(arp_notes)],
                    vel,
                )

        # 2. Coastal Nylon Guitar: Fingerstyle bossa/arpeggio patterns
        if bar >= 3:
            if bar >= 47 or (31 <= bar <= 34):
                # Gentle arpeggiated fingerpicking for Bridge & Coda
                pattern = [
                    (0.0, 0, 1.5, 76),
                    (0.5, 1, 1.2, 70),
                    (1.0, 2, 1.2, 72),
                    (1.5, 3, 1.2, 74),
                ]
                loops = int(max(1, length // 2))
                for lp in range(loops):
                    offset = b0 + lp * 2.0
                    for rel_b, v_idx, d_b, vel in pattern:
                        if offset + rel_b < b0 + length:
                            guitar.add_note(
                                bt(bar, offset + rel_b) + int(rng.integers(-5, 6)),
                                dur(d_b),
                                v_pitches[v_idx % len(v_pitches)],
                                vel - (6 if bar >= 50 else 0),
                            )
            else:
                # Bossa / Shonan stroll syncopated plucking
                if length >= 4:
                    # 4-beat bossa cell: thumb at 0, 1.5, 3.0; chord plucks at 0.5, 1.5, 2.5, 3.5
                    guitar.add_note(bt(bar, b0 + 0.0), dur(1.3), v_pitches[0] - 12, 80)
                    for p in v_pitches[1:]:
                        guitar.add_note(bt(bar, b0 + 0.5), dur(0.8), p, 74)
                        guitar.add_note(bt(bar, b0 + 1.5), dur(0.9), p, 78)
                        guitar.add_note(bt(bar, b0 + 2.5), dur(0.8), p, 72)
                    guitar.add_note(bt(bar, b0 + 2.0), dur(1.2), v_pitches[0], 75)
                    guitar.add_note(bt(bar, b0 + 3.5), dur(0.45), v_pitches[-1], 70)
                else:
                    # 2-beat harmonic cell
                    guitar.add_note(bt(bar, b0 + 0.0), dur(0.9), v_pitches[0], 78)
                    for i, p in enumerate(v_pitches[1:]):
                        guitar.add_note(bt(bar, b0 + 0.5) + i * 10, dur(0.85), p, 75)
                    guitar.add_note(bt(bar, b0 + 1.5), dur(0.45), v_pitches[-1], 72)

        # 3. Rhodes Electric Piano: Warm jazz-pop comping & bell voicings
        if bar in (1, 2, 5, 6) or (31 <= bar <= 34) or bar >= 47:
            # Rolled warm sustained chord
            for i, p in enumerate(v_pitches):
                rhodes.add_note(
                    bt(bar, b0) + i * 18,
                    dur(length * 0.92),
                    p,
                    74 - (6 if bar >= 50 else 0),
                )
        elif 7 <= bar <= 46:
            if length >= 4:
                for i, p in enumerate(v_pitches):
                    rhodes.add_note(bt(bar, b0 + 0.0) + i * 12, dur(1.35), p, 78)
                    rhodes.add_note(bt(bar, b0 + 1.5) + i * 10, dur(1.4), p, 82)
                rhodes.add_note(bt(bar, b0 + 3.0), dur(0.85), v_pitches[-1] + 12, 74)
            else:
                for i, p in enumerate(v_pitches):
                    rhodes.add_note(bt(bar, b0 + 0.0) + i * 12, dur(1.2), p, 80)
                if b0 == 0.0:
                    rhodes.add_note(bt(bar, b0 + 1.5), dur(0.45), v_pitches[-1], 72)
                else:
                    for p in v_pitches[1:3]:
                        rhodes.add_note(bt(bar, b0 + 1.5), dur(0.45), p, 74)

        # 4. Warm String Ensemble: Lush pads in Theme A', Chorus, Bridge build, Grand Chorus, Coda
        if bar >= 15:
            str_vel = 68
            if 23 <= bar <= 30:
                str_vel = 78
            elif 31 <= bar <= 34:
                str_vel = 62
            elif 39 <= bar <= 46:
                str_vel = 84
            elif bar >= 47:
                str_vel = 64

            pad_pitches = [v_pitches[0], v_pitches[1], v_pitches[-1]]
            if 39 <= bar <= 46:
                pad_pitches.append(v_pitches[0] + 12)
            for p in pad_pitches:
                strings.add_note(bt(bar, b0), dur(length * 0.97), p, str_vel)

        # 5. Fingered Electric Bass: Buoyant walking/bossa bassline
        if bar >= 5:
            if bar in (5, 6) or (31 <= bar <= 34) or bar >= 48:
                bass.add_note(bt(bar, b0), dur(length * 0.92), bass_root, 86 - (8 if bar >= 50 else 0))
            elif length >= 4:
                # 4-beat dotted-quarter + eighth + half groove
                bass.add_note(bt(bar, b0 + 0.0), dur(1.4), bass_root, 96)
                bass.add_note(bt(bar, b0 + 1.5), dur(0.45), bass_fifth, 88)
                bass.add_note(bt(bar, b0 + 2.0), dur(1.4), bass_root + 12 if bass_root < n("C2") else bass_fifth, 92)
                bass.add_note(bt(bar, b0 + 3.5), dur(0.45), bass_root + 2, 86)
            else:
                # 2-beat groove with fifth/approach note
                bass.add_note(bt(bar, b0 + 0.0), dur(1.4), bass_root, 96)
                bass.add_note(bt(bar, b0 + 1.5), dur(0.45), bass_fifth, 88)

    # ------------------------------------------------------------------------
    # C. Coastal Percussion Track (Channel 9)
    # ------------------------------------------------------------------------
    KICK = 36
    STICK = 37
    SNARE = 38
    CHH = 42
    OHH = 46
    RIDE = 51
    TAMB = 54
    CONGA_H = 63
    CONGA_L = 64
    SHAKER = 70
    TRIANGLE = 81

    for bar in range(1, 53):
        if bar in (4, 6, 14, 22, 30, 38, 46, 51):
            drums.add_note(bt(bar, 0.0), dur(1.5), TRIANGLE, 72)

        # Bars 5-6: Gentle shaker wake-up
        if bar in (5, 6):
            for step in range(8):
                drums.add_note(bt(bar, step * 0.5), dur(0.2), SHAKER, 56 if step % 2 == 0 else 44)

        # Theme A & A' (Bars 7-22): Light coastal stroll groove
        elif 7 <= bar <= 22:
            for step in range(8):
                b = step * 0.5
                drums.add_note(bt(bar, b), dur(0.2), SHAKER, 62 if step % 2 == 0 else 48)
                drums.add_note(bt(bar, b), dur(0.2), CHH, 58 if step % 2 == 0 else 44)
            # Kick on 1, 2.5, 3
            drums.add_note(bt(bar, 0.0), dur(0.4), KICK, 84)
            drums.add_note(bt(bar, 1.5), dur(0.4), KICK, 74)
            drums.add_note(bt(bar, 2.0), dur(0.4), KICK, 80)
            # Cross-stick on 2 & 4
            drums.add_note(bt(bar, 1.0), dur(0.25), STICK, 76)
            drums.add_note(bt(bar, 3.0), dur(0.25), STICK, 78)
            if bar >= 15:
                drums.add_note(bt(bar, 1.5), dur(0.25), CONGA_H, 66)
                drums.add_note(bt(bar, 3.5), dur(0.25), CONGA_L, 68)
                drums.add_note(bt(bar, 3.0), dur(0.3), TAMB, 64)
            if bar in (14, 22):
                # Subtle turnaround fill
                drums.add_note(bt(bar, 3.0), dur(0.25), SNARE, 74)
                drums.add_note(bt(bar, 3.5), dur(0.25), SNARE, 82)
                drums.add_note(bt(bar, 3.75), dur(0.2), OHH, 76)

        # Chorus (Bars 23-30) & Grand Chorus (Bars 39-46): Full buoyant groove
        elif (23 <= bar <= 30) or (39 <= bar <= 46):
            is_grand = bar >= 39
            boost = 6 if is_grand else 0
            for step in range(8):
                b = step * 0.5
                drums.add_note(bt(bar, b), dur(0.2), SHAKER, 66 + boost if step % 2 == 0 else 52 + boost)
                drums.add_note(bt(bar, b), dur(0.35), RIDE if is_grand else CHH, 68 if step % 2 == 0 else 54)
            drums.add_note(bt(bar, 0.0), dur(0.4), KICK, 90 + boost)
            drums.add_note(bt(bar, 1.5), dur(0.4), KICK, 80 + boost)
            drums.add_note(bt(bar, 2.0), dur(0.4), KICK, 86 + boost)
            drums.add_note(bt(bar, 3.5), dur(0.4), KICK, 76 + boost)
            drums.add_note(bt(bar, 1.0), dur(0.3), SNARE, 80 + boost)
            drums.add_note(bt(bar, 3.0), dur(0.3), SNARE, 84 + boost)
            drums.add_note(bt(bar, 1.0), dur(0.25), TAMB, 66 + boost)
            drums.add_note(bt(bar, 3.0), dur(0.25), TAMB, 70 + boost)
            drums.add_note(bt(bar, 0.75), dur(0.2), CONGA_H, 66)
            drums.add_note(bt(bar, 2.5), dur(0.25), CONGA_L, 70)
            if bar in (26, 30, 42, 46):
                drums.add_note(bt(bar, 3.25), dur(0.2), SNARE, 78)
                drums.add_note(bt(bar, 3.5), dur(0.2), SNARE, 84)
                drums.add_note(bt(bar, 3.75), dur(0.25), OHH, 80)

        # Bridge (Bars 35-38): Gentle re-entry & build into Grand Chorus
        elif 35 <= bar <= 38:
            for step in range(8):
                b = step * 0.5
                drums.add_note(bt(bar, b), dur(0.2), SHAKER, 56 + (bar - 35) * 4)
            drums.add_note(bt(bar, 0.0), dur(0.4), KICK, 78 + (bar - 35) * 4)
            drums.add_note(bt(bar, 2.0), dur(0.4), KICK, 76 + (bar - 35) * 4)
            drums.add_note(bt(bar, 1.0), dur(0.25), STICK, 72 + (bar - 35) * 3)
            drums.add_note(bt(bar, 3.0), dur(0.25), STICK, 74 + (bar - 35) * 3)
            if bar == 38:
                for fill_step, pitch_d in enumerate([SNARE, CONGA_H, SNARE, OHH]):
                    drums.add_note(bt(38, 2.0 + fill_step * 0.5), dur(0.35), pitch_d, 80 + fill_step * 5)

        # Coda (Bars 47-49): Soft fading shaker & heartbeat kick
        elif 47 <= bar <= 49:
            fade = (bar - 46) * 8
            for step in range(4):
                drums.add_note(bt(bar, step * 1.0), dur(0.25), SHAKER, max(36, 58 - fade))
            drums.add_note(bt(bar, 0.0), dur(0.4), KICK, max(48, 72 - fade))
            drums.add_note(bt(bar, 2.0), dur(0.25), STICK, max(42, 66 - fade))

    all_tracks = [
        conductor,
        flute,
        violin,
        guitar,
        rhodes,
        vibes,
        celesta,
        harp,
        strings,
        bass,
        drums,
    ]

    header = b"MThd" + struct.pack(">IHHH", 6, 1, len(all_tracks), TPQ)
    track_chunks = b"".join(t.to_mtrk_bytes() for t in all_tracks)
    return header + track_chunks, all_tracks, tempo_events_micros


# ============================================================================
# 4. Sample-Free Acoustic & Modal Synthesizer (44.1 kHz Stereo)
# ============================================================================

class TempoMap:
    def __init__(self, tempo_events: List[Tuple[int, int]], tpq: int = TPQ) -> None:
        self.tpq = tpq
        sorted_events = sorted(tempo_events, key=lambda x: x[0])
        self.segments: List[Tuple[int, int, float]] = []  # (tick, micros, sec_at_tick)
        cur_tick = 0
        cur_micros = 500_000
        cur_sec = 0.0
        for tick, micros in sorted_events:
            if tick > cur_tick:
                cur_sec += ((tick - cur_tick) * cur_micros) / 1_000_000.0 / self.tpq
            cur_tick = tick
            cur_micros = micros
            if self.segments and self.segments[-1][0] == tick:
                self.segments[-1] = (tick, micros, cur_sec)
            else:
                self.segments.append((tick, micros, cur_sec))
        if not self.segments:
            self.segments.append((0, 500_000, 0.0))

    def tick_to_seconds(self, tick: int) -> float:
        seg_tick, seg_micros, seg_sec = self.segments[0]
        for t, m, s in self.segments:
            if t <= tick:
                seg_tick, seg_micros, seg_sec = t, m, s
            else:
                break
        return seg_sec + ((tick - seg_tick) * seg_micros) / 1_000_000.0 / self.tpq


def midi_to_hz(pitch: float) -> float:
    return 440.0 * (2.0 ** ((pitch - 69.0) / 12.0))


def adsr_envelope(
    total_samples: int,
    note_samples: int,
    attack_s: float,
    decay_s: float,
    sustain_level: float,
    release_s: float,
) -> np.ndarray:
    env = np.zeros(total_samples, dtype=np.float64)
    a_len = max(1, int(attack_s * SAMPLE_RATE))
    d_len = max(1, int(decay_s * SAMPLE_RATE))
    note_samples = min(total_samples, max(a_len + 1, note_samples))

    # Attack (smooth raised cosine / exponential curve)
    end_a = min(total_samples, a_len)
    env[:end_a] = np.linspace(0.0, 1.0, end_a) ** 0.8

    # Decay + Sustain
    if note_samples > end_a:
        end_d = min(note_samples, end_a + d_len)
        env[end_a:end_d] = np.linspace(1.0, sustain_level, end_d - end_a)
        if note_samples > end_d:
            env[end_a + d_len : note_samples] = sustain_level

    # Release
    rel_len = total_samples - note_samples
    if rel_len > 0:
        start_val = env[note_samples - 1] if note_samples > 0 else sustain_level
        t_rel = np.linspace(0.0, 1.0, rel_len)
        env[note_samples:] = start_val * np.exp(-5.0 * t_rel) * (1.0 - t_rel)

    return env


def synth_flute(pitch: int, velocity: int, duration_s: float, rng: np.random.Generator) -> np.ndarray:
    """Breathy concert flute with expressive delayed vibrato and air-jet onset."""
    rel_s = 0.16
    total_s = duration_s + rel_s
    n_samples = int(total_s * SAMPLE_RATE)
    note_samples = int(duration_s * SAMPLE_RATE)
    t = np.arange(n_samples, dtype=np.float64) / SAMPLE_RATE
    f0 = midi_to_hz(pitch)
    vel_gain = (velocity / 127.0) ** 1.15

    # Delayed vibrato + subtle pitch scoop at onset
    vib_env = np.clip((t - 0.14) / 0.22, 0.0, 1.0)
    scoop = -0.12 * np.exp(-t / 0.025)
    inst_freq = f0 * (2.0 ** ((scoop + 0.11 * vib_env * np.sin(2.0 * np.pi * 5.3 * t)) / 12.0))
    phase = 2.0 * np.pi * np.cumsum(inst_freq) / SAMPLE_RATE

    # Pure harmonic spectrum with gentle 2nd & 3rd harmonics
    tone = (
        1.00 * np.sin(phase)
        + 0.28 * np.sin(2.0 * phase + 0.3)
        + 0.09 * np.sin(3.0 * phase + 0.7)
        + 0.03 * np.sin(4.0 * phase)
    )
    # Subtle amplitude tremolo coupled to vibrato
    tone *= 1.0 + 0.06 * vib_env * np.sin(2.0 * np.pi * 5.3 * t - 0.5)

    # Chiff / air jet breath noise
    noise = rng.standard_normal(n_samples)
    sos = signal.butter(2, [max(400.0, f0 * 0.8), min(8000.0, f0 * 3.5)], btype="bandpass", fs=SAMPLE_RATE, output="sos")
    breath = signal.sosfilt(sos, noise)
    chiff_env = 0.14 * np.exp(-t / 0.045) + 0.025

    env = adsr_envelope(n_samples, note_samples, attack_s=0.045, decay_s=0.12, sustain_level=0.88, release_s=rel_s)
    return (tone + breath * chiff_env) * env * vel_gain * 0.36


def synth_violin(pitch: int, velocity: int, duration_s: float, rng: np.random.Generator) -> np.ndarray:
    """Warm solo violin with bowed harmonics, body formant filtering, and lyrical vibrato."""
    rel_s = 0.22
    total_s = duration_s + rel_s
    n_samples = int(total_s * SAMPLE_RATE)
    note_samples = int(duration_s * SAMPLE_RATE)
    t = np.arange(n_samples, dtype=np.float64) / SAMPLE_RATE
    f0 = midi_to_hz(pitch)
    vel_gain = (velocity / 127.0) ** 1.15

    vib_env = np.clip((t - 0.10) / 0.20, 0.0, 1.0)
    inst_freq = f0 * (2.0 ** ((0.15 * vib_env * np.sin(2.0 * np.pi * 5.7 * t)) / 12.0))
    phase = 2.0 * np.pi * np.cumsum(inst_freq) / SAMPLE_RATE

    # Band-limited bowed string harmonic series
    sig = np.zeros(n_samples, dtype=np.float64)
    max_h = min(16, int((SAMPLE_RATE * 0.42) / f0))
    for h in range(1, max_h + 1):
        amp = (1.0 / (h ** 1.15)) * (0.85 if h % 2 == 0 else 1.0)
        sig += amp * np.sin(h * phase + (h * 0.17))

    # Simulated wooden body resonance peaks (~290 Hz, ~540 Hz, ~1200 Hz, ~2600 Hz)
    sos_lp = signal.butter(2, min(6500.0, f0 * 7.5), btype="lowpass", fs=SAMPLE_RATE, output="sos")
    sig = signal.sosfilt(sos_lp, sig)
    for center_hz, bw_hz, boost in [(290.0, 90.0, 0.35), (540.0, 130.0, 0.30), (1250.0, 300.0, 0.22)]:
        sos_bp = signal.butter(1, [center_hz - bw_hz / 2, center_hz + bw_hz / 2], btype="bandpass", fs=SAMPLE_RATE, output="sos")
        sig = sig + boost * signal.sosfilt(sos_bp, sig)

    # Subtle bow rosin texture at attack
    bow_noise = rng.standard_normal(n_samples) * (0.04 * np.exp(-t / 0.05) + 0.006)
    env = adsr_envelope(n_samples, note_samples, attack_s=0.065, decay_s=0.15, sustain_level=0.86, release_s=rel_s)
    return (sig * 0.42 + bow_noise) * env * vel_gain * 0.30


def synth_nylon_guitar(pitch: int, velocity: int, duration_s: float) -> np.ndarray:
    """Warm fingerstyle nylon-string guitar with harmonic-dependent damping and body resonance."""
    rel_s = 0.28
    total_s = max(0.35, duration_s + rel_s)
    n_samples = int(total_s * SAMPLE_RATE)
    note_samples = int(duration_s * SAMPLE_RATE)
    t = np.arange(n_samples, dtype=np.float64) / SAMPLE_RATE
    f0 = midi_to_hz(pitch)
    vel_gain = (velocity / 127.0) ** 1.2

    # Plucked nylon string: higher partials decay much faster than fundamental
    sig = np.zeros(n_samples, dtype=np.float64)
    harmonics = [
        (1.0, 1.00, 1.25),
        (2.0, 0.58, 0.65),
        (3.0, 0.32, 0.35),
        (4.0, 0.16, 0.18),
        (5.0, 0.08, 0.10),
        (6.0, 0.04, 0.06),
    ]
    for mult, amp, tau in harmonics:
        freq = f0 * mult * np.sqrt(1.0 + 0.00008 * (mult ** 2))
        if freq < SAMPLE_RATE * 0.45:
            sig += amp * np.sin(2.0 * np.pi * freq * t) * np.exp(-t / tau)

    # Soft finger-flesh pluck impulse + warm guitar body resonance (~195 Hz)
    pluck = np.sin(2.0 * np.pi * min(1800.0, f0 * 4.5) * t) * np.exp(-t / 0.008) * 0.22
    body = np.sin(2.0 * np.pi * 192.0 * t) * np.exp(-t / 0.045) * 0.12
    env = adsr_envelope(n_samples, note_samples, attack_s=0.004, decay_s=0.10, sustain_level=0.75, release_s=rel_s)
    return (sig + pluck + body) * env * vel_gain * 0.28


def synth_rhodes(pitch: int, velocity: int, duration_s: float) -> np.ndarray:
    """Warm Rhodes electric piano with glassy tine harmonic and tonebar sustain."""
    rel_s = 0.30
    total_s = duration_s + rel_s
    n_samples = int(total_s * SAMPLE_RATE)
    note_samples = int(duration_s * SAMPLE_RATE)
    t = np.arange(n_samples, dtype=np.float64) / SAMPLE_RATE
    f0 = midi_to_hz(pitch)
    vel_norm = velocity / 127.0
    vel_gain = vel_norm ** 1.25

    w0 = 2.0 * np.pi * f0 * t
    # Tonebar FM (1:1 modulator for warm Rhodes bark on harder velocities)
    mod1 = (0.9 * vel_norm) * np.exp(-t / 0.32) * np.sin(w0)
    # Tine bell FM (7:1 inharmonic metallic chime with quick decay)
    mod_tine = (0.38 * vel_norm) * np.exp(-t / 0.11) * np.sin(7.0 * w0)
    tone = (
        np.sin(w0 + mod1 + mod_tine) * np.exp(-t / 1.8)
        + 0.22 * np.sin(2.0 * w0) * np.exp(-t / 0.85)
        + 0.08 * np.sin(3.0 * w0) * np.exp(-t / 0.40)
    )
    env = adsr_envelope(n_samples, note_samples, attack_s=0.005, decay_s=0.20, sustain_level=0.72, release_s=rel_s)
    return tone * env * vel_gain * 0.24


def synth_vibraphone(pitch: int, velocity: int, duration_s: float) -> np.ndarray:
    """Sunlit vibraphone bar (1 : 4 : 10 tuned modes) with yarn mallet and motor tremolo."""
    rel_s = 0.45
    total_s = duration_s + rel_s
    n_samples = int(total_s * SAMPLE_RATE)
    note_samples = int(duration_s * SAMPLE_RATE)
    t = np.arange(n_samples, dtype=np.float64) / SAMPLE_RATE
    f0 = midi_to_hz(pitch)
    vel_gain = (velocity / 127.0) ** 1.15

    # Tuned aluminum bar modes (1 : 4 : 10)
    sig = np.sin(2.0 * np.pi * f0 * t) * np.exp(-t / 1.55)
    if f0 * 4.0 < SAMPLE_RATE * 0.45:
        sig += 0.24 * np.sin(2.0 * np.pi * (f0 * 4.0) * t) * np.exp(-t / 0.35)
    if f0 * 10.0 < SAMPLE_RATE * 0.45:
        sig += 0.06 * np.sin(2.0 * np.pi * (f0 * 10.0) * t) * np.exp(-t / 0.09)

    # Motor resonator tremolo
    tremolo = 1.0 - 0.20 * (0.5 * (1.0 - np.cos(2.0 * np.pi * 5.8 * t)))
    env = adsr_envelope(n_samples, note_samples, attack_s=0.004, decay_s=0.15, sustain_level=0.80, release_s=rel_s)
    return sig * tremolo * env * vel_gain * 0.25


def synth_celesta(pitch: int, velocity: int, duration_s: float) -> np.ndarray:
    """Sparkling celesta steel-plate bell with felt hammer attack."""
    rel_s = 0.42
    total_s = duration_s + rel_s
    n_samples = int(total_s * SAMPLE_RATE)
    note_samples = int(duration_s * SAMPLE_RATE)
    t = np.arange(n_samples, dtype=np.float64) / SAMPLE_RATE
    f0 = midi_to_hz(pitch)
    vel_gain = (velocity / 127.0) ** 1.15

    sig = (
        1.00 * np.sin(2.0 * np.pi * f0 * t) * np.exp(-t / 1.15)
        + 0.34 * np.sin(2.0 * np.pi * (f0 * 2.0) * t) * np.exp(-t / 0.55)
    )
    if f0 * 2.756 < SAMPLE_RATE * 0.45:
        sig += 0.22 * np.sin(2.0 * np.pi * (f0 * 2.756) * t) * np.exp(-t / 0.28)
    if f0 * 5.404 < SAMPLE_RATE * 0.45:
        sig += 0.09 * np.sin(2.0 * np.pi * (f0 * 5.404) * t) * np.exp(-t / 0.11)

    env = adsr_envelope(n_samples, note_samples, attack_s=0.003, decay_s=0.12, sustain_level=0.75, release_s=rel_s)
    return sig * env * vel_gain * 0.23


def synth_harp(pitch: int, velocity: int, duration_s: float) -> np.ndarray:
    """Luminous concert harp pluck with warm soundboard bloom."""
    rel_s = 0.55
    total_s = duration_s + rel_s
    n_samples = int(total_s * SAMPLE_RATE)
    note_samples = int(duration_s * SAMPLE_RATE)
    t = np.arange(n_samples, dtype=np.float64) / SAMPLE_RATE
    f0 = midi_to_hz(pitch)
    vel_gain = (velocity / 127.0) ** 1.15

    sig = (
        1.00 * np.sin(2.0 * np.pi * f0 * t) * np.exp(-t / 1.45)
        + 0.42 * np.sin(2.0 * np.pi * (2.0 * f0) * t) * np.exp(-t / 0.72)
        + 0.16 * np.sin(2.0 * np.pi * (3.0 * f0) * t) * np.exp(-t / 0.36)
        + 0.06 * np.sin(2.0 * np.pi * (4.0 * f0) * t) * np.exp(-t / 0.18)
    )
    env = adsr_envelope(n_samples, note_samples, attack_s=0.005, decay_s=0.20, sustain_level=0.78, release_s=rel_s)
    return sig * env * vel_gain * 0.24


def synth_string_pad(pitch: int, velocity: int, duration_s: float) -> Tuple[np.ndarray, np.ndarray]:
    """Lush stereo string ensemble pad (6 detuned bowed voices split across L/R)."""
    rel_s = 0.50
    total_s = duration_s + rel_s
    n_samples = int(total_s * SAMPLE_RATE)
    note_samples = int(duration_s * SAMPLE_RATE)
    t = np.arange(n_samples, dtype=np.float64) / SAMPLE_RATE
    f0 = midi_to_hz(pitch)
    vel_gain = (velocity / 127.0) ** 1.2

    detune_cents = [-11.0, -4.5, +2.0, -2.5, +5.0, +11.5]
    lfo_rates = [4.1, 4.7, 5.3, 4.4, 5.0, 5.6]
    left = np.zeros(n_samples, dtype=np.float64)
    right = np.zeros(n_samples, dtype=np.float64)

    for idx, (cents, rate) in enumerate(zip(detune_cents, lfo_rates)):
        freq = f0 * (2.0 ** ((cents + 3.5 * np.sin(2.0 * np.pi * rate * t + idx)) / 1200.0))
        w = 2.0 * np.pi * freq * t + idx * 0.9
        voice = (
            1.00 * np.sin(w)
            + 0.48 * np.sin(2.0 * w + 0.2)
            + 0.26 * np.sin(3.0 * w + 0.5)
            + 0.14 * np.sin(4.0 * w + 0.8)
            + 0.07 * np.sin(5.0 * w)
        )
        if idx < 3:
            left += voice * 0.34
            right += voice * 0.12
        else:
            left += voice * 0.12
            right += voice * 0.34

    cutoff = min(3800.0, f0 * 5.2)
    sos = signal.butter(2, cutoff, btype="lowpass", fs=SAMPLE_RATE, output="sos")
    left = signal.sosfilt(sos, left)
    right = signal.sosfilt(sos, right)

    env = adsr_envelope(n_samples, note_samples, attack_s=0.26, decay_s=0.35, sustain_level=0.84, release_s=rel_s)
    gain = env * vel_gain * 0.14
    return left * gain, right * gain


def synth_fingered_bass(pitch: int, velocity: int, duration_s: float) -> np.ndarray:
    """Warm, punchy fingered electric bass with dynamic filter envelope."""
    rel_s = 0.12
    total_s = duration_s + rel_s
    n_samples = int(total_s * SAMPLE_RATE)
    note_samples = int(duration_s * SAMPLE_RATE)
    t = np.arange(n_samples, dtype=np.float64) / SAMPLE_RATE
    f0 = midi_to_hz(pitch)
    vel_gain = (velocity / 127.0) ** 1.15

    w0 = 2.0 * np.pi * f0 * t
    pluck_decay = np.exp(-t / 0.16)
    sig = (
        1.00 * np.sin(w0)
        + (0.55 + 0.30 * pluck_decay) * np.sin(2.0 * w0 + 0.2)
        + (0.22 + 0.35 * pluck_decay) * np.sin(3.0 * w0 + 0.4)
        + (0.06 + 0.20 * pluck_decay) * np.sin(4.0 * w0)
    )
    sos = signal.butter(2, min(1400.0, f0 * 6.5), btype="lowpass", fs=SAMPLE_RATE, output="sos")
    sig = signal.sosfilt(sos, sig)
    env = adsr_envelope(n_samples, note_samples, attack_s=0.008, decay_s=0.14, sustain_level=0.80, release_s=rel_s)
    return sig * env * vel_gain * 0.38


def synth_drum_hit(pitch: int, velocity: int, rng: np.random.Generator) -> Tuple[np.ndarray, float]:
    """Synthesize individual coastal percussion hit and return (mono_wave, pan_0_to_1)."""
    vel = (velocity / 127.0) ** 1.15

    if pitch == 36:  # Soft warm kick
        n_s = int(0.26 * SAMPLE_RATE)
        t = np.arange(n_s) / SAMPLE_RATE
        freq = 52.0 + 95.0 * np.exp(-t / 0.018)
        phase = 2.0 * np.pi * np.cumsum(freq) / SAMPLE_RATE
        body = np.sin(phase) * np.exp(-t / 0.085)
        click = np.sin(2.0 * np.pi * 420.0 * t) * np.exp(-t / 0.005) * 0.18
        return (body + click) * vel * 0.48, 0.50

    if pitch == 37:  # Woody side-stick / rim click
        n_s = int(0.09 * SAMPLE_RATE)
        t = np.arange(n_s) / SAMPLE_RATE
        wood = (
            np.sin(2.0 * np.pi * 820.0 * t) * np.exp(-t / 0.009)
            + 0.7 * np.sin(2.0 * np.pi * 1680.0 * t) * np.exp(-t / 0.006)
        )
        click = rng.standard_normal(n_s) * np.exp(-t / 0.003) * 0.25
        return (wood + click) * vel * 0.26, 0.44

    if pitch == 38:  # Brushed / light acoustic snare
        n_s = int(0.22 * SAMPLE_RATE)
        t = np.arange(n_s) / SAMPLE_RATE
        tone = np.sin(2.0 * np.pi * (185.0 + 40.0 * np.exp(-t / 0.015)) * t) * np.exp(-t / 0.045) * 0.45
        noise = rng.standard_normal(n_s)
        sos = signal.butter(2, [900.0, 7500.0], btype="bandpass", fs=SAMPLE_RATE, output="sos")
        wires = signal.sosfilt(sos, noise) * np.exp(-t / 0.075) * 0.55
        return (tone + wires) * vel * 0.30, 0.48

    if pitch in (42, 46):  # Closed / Open Hi-Hat
        dur_s = 0.075 if pitch == 42 else 0.36
        decay = 0.016 if pitch == 42 else 0.095
        n_s = int(dur_s * SAMPLE_RATE)
        t = np.arange(n_s) / SAMPLE_RATE
        noise = rng.standard_normal(n_s)
        sos = signal.butter(2, 6800.0, btype="highpass", fs=SAMPLE_RATE, output="sos")
        hat = signal.sosfilt(sos, noise) * np.exp(-t / decay)
        return hat * vel * 0.16, 0.62

    if pitch == 51:  # Shimmering Ride Cymbal
        n_s = int(0.55 * SAMPLE_RATE)
        t = np.arange(n_s) / SAMPLE_RATE
        bell = (
            np.sin(2.0 * np.pi * 2840.0 * t) * np.exp(-t / 0.14)
            + 0.6 * np.sin(2.0 * np.pi * 4320.0 * t) * np.exp(-t / 0.09)
            + 0.4 * np.sin(2.0 * np.pi * 6190.0 * t) * np.exp(-t / 0.06)
        ) * 0.25
        noise = rng.standard_normal(n_s)
        sos = signal.butter(2, 5500.0, btype="highpass", fs=SAMPLE_RATE, output="sos")
        wash = signal.sosfilt(sos, noise) * np.exp(-t / 0.16) * 0.35
        return (bell + wash) * vel * 0.16, 0.66

    if pitch == 54:  # Tambourine jingle
        n_s = int(0.18 * SAMPLE_RATE)
        t = np.arange(n_s) / SAMPLE_RATE
        noise = rng.standard_normal(n_s)
        sos = signal.butter(2, [4800.0, 11500.0], btype="bandpass", fs=SAMPLE_RATE, output="sos")
        jing = signal.sosfilt(sos, noise) * (np.exp(-t / 0.035) + 0.45 * np.exp(-((t - 0.024) ** 2) / 0.0002))
        return jing * vel * 0.15, 0.35

    if pitch in (63, 64):  # High / Low Conga
        f0 = 265.0 if pitch == 63 else 195.0
        n_s = int(0.18 * SAMPLE_RATE)
        t = np.arange(n_s) / SAMPLE_RATE
        freq = f0 + 35.0 * np.exp(-t / 0.012)
        phase = 2.0 * np.pi * np.cumsum(freq) / SAMPLE_RATE
        conga = (np.sin(phase) + 0.22 * np.sin(2.0 * phase)) * np.exp(-t / 0.055)
        slap = rng.standard_normal(n_s) * np.exp(-t / 0.005) * 0.12
        return (conga + slap) * vel * 0.26, 0.38 if pitch == 63 else 0.42

    if pitch == 70:  # Soft Shaker
        n_s = int(0.085 * SAMPLE_RATE)
        t = np.arange(n_s) / SAMPLE_RATE
        noise = rng.standard_normal(n_s)
        sos = signal.butter(2, [4500.0, 11000.0], btype="bandpass", fs=SAMPLE_RATE, output="sos")
        env = np.sin(np.pi * np.clip(t / 0.055, 0.0, 1.0)) ** 1.6
        shk = signal.sosfilt(sos, noise) * env
        return shk * vel * 0.13, 0.68

    if pitch == 81:  # Sparkling Triangle
        n_s = int(0.95 * SAMPLE_RATE)
        t = np.arange(n_s) / SAMPLE_RATE
        tri = (
            np.sin(2.0 * np.pi * 3520.0 * t) * np.exp(-t / 0.42)
            + 0.45 * np.sin(2.0 * np.pi * 6480.0 * t) * np.exp(-t / 0.25)
            + 0.22 * np.sin(2.0 * np.pi * 9310.0 * t) * np.exp(-t / 0.15)
        )
        return tri * vel * 0.14, 0.72

    return np.zeros(64, dtype=np.float64), 0.50


def synth_seaside_ambience(total_samples: int, rng: np.random.Generator) -> np.ndarray:
    """
    Synthesizes a subtle, musical stereo ocean surf and two distant gull calls
    for the intro and coda so the coastal setting feels alive without masking the music.
    """
    t = np.arange(total_samples, dtype=np.float64) / SAMPLE_RATE
    total_s = total_samples / SAMPLE_RATE

    # Slow rolling wave envelopes (two stereo wave fronts)
    wave_env_l = 0.35 + 0.65 * (0.5 * (1.0 + np.sin(2.0 * np.pi * 0.11 * t - 0.6))) ** 2.2
    wave_env_r = 0.35 + 0.65 * (0.5 * (1.0 + np.sin(2.0 * np.pi * 0.11 * t - 1.5))) ** 2.2

    noise_l = rng.standard_normal(total_samples)
    noise_r = rng.standard_normal(total_samples)

    # Low warm surf rumble + gentle high foam shimmer
    sos_low = signal.butter(2, [90.0, 620.0], btype="bandpass", fs=SAMPLE_RATE, output="sos")
    sos_foam = signal.butter(2, [900.0, 3200.0], btype="bandpass", fs=SAMPLE_RATE, output="sos")

    surf_l = signal.sosfilt(sos_low, noise_l) * wave_env_l + 0.28 * signal.sosfilt(sos_foam, noise_l) * (wave_env_l ** 2)
    surf_r = signal.sosfilt(sos_low, noise_r) * wave_env_r + 0.28 * signal.sosfilt(sos_foam, noise_r) * (wave_env_r ** 2)

    # Dynamic ducking curve: audible in Intro (0-12s) and Coda (last 18s), whisper-quiet during main music
    duck = np.full(total_samples, 0.18, dtype=np.float64)
    intro_mask = t < 15.0
    duck[intro_mask] = 0.18 + 0.82 * np.cos(0.5 * np.pi * np.clip((t[intro_mask] - 3.0) / 12.0, 0.0, 1.0)) ** 2
    outro_start = max(0.0, total_s - 20.0)
    outro_mask = t > outro_start
    duck[outro_mask] = 0.18 + 0.82 * np.sin(0.5 * np.pi * np.clip((t[outro_mask] - outro_start) / 14.0, 0.0, 1.0)) ** 2

    # Fade in first 1.2s and fade out last 2.2s
    fade_in = np.clip(t / 1.2, 0.0, 1.0)
    fade_out = np.clip((total_s - t) / 2.2, 0.0, 1.0)
    gain = 0.022 * duck * fade_in * fade_out

    stereo = np.column_stack([surf_l * gain, surf_r * gain])

    # Distant soft gull cries in Intro (t=2.1s, 3.4s) and Coda (total_s - 6.5s)
    for call_t, base_hz, pan in [(2.1, 1680.0, 0.30), (3.3, 1520.0, 0.72), (total_s - 6.5, 1600.0, 0.36)]:
        if 0.5 < call_t < total_s - 1.2:
            c_len = int(0.52 * SAMPLE_RATE)
            ct = np.arange(c_len) / SAMPLE_RATE
            # Natural gull pitch arc: rise quickly then glide down
            f_curve = base_hz * (1.0 + 0.18 * np.sin(np.pi * np.clip(ct / 0.16, 0.0, 1.0)) - 0.24 * (ct / 0.52) ** 1.5)
            c_phase = 2.0 * np.pi * np.cumsum(f_curve) / SAMPLE_RATE
            gull = (np.sin(c_phase) + 0.35 * np.sin(2.0 * c_phase)) * np.sin(np.pi * ct / 0.52) ** 1.8 * 0.011
            idx0 = int(call_t * SAMPLE_RATE)
            stereo[idx0 : idx0 + c_len, 0] += gull * np.cos(pan * np.pi * 0.5)
            stereo[idx0 : idx0 + c_len, 1] += gull * np.sin(pan * np.pi * 0.5)

    return stereo


def apply_stereo_concert_reverb(dry_wet_bus: np.ndarray) -> np.ndarray:
    """
    Applies a lush, transparent stereo Schroeder/FDN hall reverb to the reverb send bus.
    """
    n_samples = dry_wet_bus.shape[0]
    sos_lp = signal.butter(1, 4400.0, btype="lowpass", fs=SAMPLE_RATE, output="sos")
    sos_hp = signal.butter(1, 140.0, btype="highpass", fs=SAMPLE_RATE, output="sos")
    filtered = signal.sosfilt(sos_hp, signal.sosfilt(sos_lp, dry_wet_bus, axis=0), axis=0)

    # Multi-tap early reflections + decaying late reflections (prime-ish ms delays)
    taps_l = [
        (int(0.023 * SAMPLE_RATE), 0.36),
        (int(0.041 * SAMPLE_RATE), 0.28),
        (int(0.067 * SAMPLE_RATE), 0.22),
        (int(0.097 * SAMPLE_RATE), 0.17),
        (int(0.139 * SAMPLE_RATE), 0.13),
        (int(0.193 * SAMPLE_RATE), 0.09),
        (int(0.263 * SAMPLE_RATE), 0.06),
        (int(0.347 * SAMPLE_RATE), 0.04),
    ]
    taps_r = [
        (int(0.029 * SAMPLE_RATE), 0.36),
        (int(0.047 * SAMPLE_RATE), 0.28),
        (int(0.073 * SAMPLE_RATE), 0.22),
        (int(0.107 * SAMPLE_RATE), 0.17),
        (int(0.151 * SAMPLE_RATE), 0.13),
        (int(0.211 * SAMPLE_RATE), 0.09),
        (int(0.283 * SAMPLE_RATE), 0.06),
        (int(0.373 * SAMPLE_RATE), 0.04),
    ]

    wet = np.zeros_like(dry_wet_bus)
    src_l = filtered[:, 0]
    src_r = filtered[:, 1]
    for delay, gain in taps_l:
        if delay < n_samples:
            wet[delay:, 0] += src_l[:-delay] * gain + src_r[:-delay] * (gain * 0.45)
    for delay, gain in taps_r:
        if delay < n_samples:
            wet[delay:, 1] += src_r[:-delay] * gain + src_l[:-delay] * (gain * 0.45)

    # Second diffusion pass for smooth tail
    second_l = wet[:, 0].copy()
    second_r = wet[:, 1].copy()
    for delay, gain in [(int(0.083 * SAMPLE_RATE), 0.28), (int(0.179 * SAMPLE_RATE), 0.18), (int(0.311 * SAMPLE_RATE), 0.11)]:
        if delay < n_samples:
            wet[delay:, 0] += second_r[:-delay] * gain
            wet[delay:, 1] += second_l[:-delay] * gain

    return signal.sosfilt(sos_lp, wet, axis=0)


def render_tracks_to_stereo(
    tracks: List[MidiTrackBuilder],
    tempo_events: List[Tuple[int, int]],
) -> np.ndarray:
    """Render all MIDI tracks into a mastered 44.1 kHz stereo waveform."""
    rng = np.random.default_rng(20261014)
    tmap = TempoMap(tempo_events, TPQ)

    max_end_tick = max(
        (note.end_tick for tr in tracks for note in tr.notes),
        default=bt(52, 4),
    )
    music_end_s = tmap.tick_to_seconds(max_end_tick)
    total_s = music_end_s + 3.2  # 3.2s tail for natural ring-out & ocean waves
    total_samples = int(math.ceil(total_s * SAMPLE_RATE))

    dry_bus = np.zeros((total_samples, 2), dtype=np.float64)
    rev_send_bus = np.zeros((total_samples, 2), dtype=np.float64)

    def mix_mono(wave: np.ndarray, start_idx: int, pan_0_1: float, rev_send: float) -> None:
        if start_idx >= total_samples or len(wave) == 0:
            return
        end_idx = min(total_samples, start_idx + len(wave))
        seg = wave[: end_idx - start_idx]
        angle = np.clip(pan_0_1, 0.0, 1.0) * (np.pi * 0.5)
        gl = math.cos(angle)
        gr = math.sin(angle)
        dry_bus[start_idx:end_idx, 0] += seg * gl
        dry_bus[start_idx:end_idx, 1] += seg * gr
        if rev_send > 0.0:
            rev_send_bus[start_idx:end_idx, 0] += seg * gl * rev_send
            rev_send_bus[start_idx:end_idx, 1] += seg * gr * rev_send

    for track in tracks:
        if not track.notes:
            continue
        pan_0_1 = track.pan / 127.0
        rev_send = (track.reverb / 127.0) * 0.55
        vol_scale = (track.volume / 100.0)

        for note in track.notes:
            start_s = tmap.tick_to_seconds(note.start_tick)
            end_s = tmap.tick_to_seconds(note.end_tick)
            dur_s = max(0.04, end_s - start_s)
            start_idx = int(round(start_s * SAMPLE_RATE))

            if track.channel == 9:
                wave, drum_pan = synth_drum_hit(note.pitch, note.velocity, rng)
                mix_mono(wave * vol_scale, start_idx, drum_pan, rev_send)
            elif track.program == 73:  # Flute
                wave = synth_flute(note.pitch, note.velocity, dur_s, rng) * vol_scale
                mix_mono(wave, start_idx, pan_0_1, rev_send)
            elif track.program == 40:  # Violin
                wave = synth_violin(note.pitch, note.velocity, dur_s, rng) * vol_scale
                mix_mono(wave, start_idx, pan_0_1, rev_send)
            elif track.program == 24:  # Nylon Guitar
                wave = synth_nylon_guitar(note.pitch, note.velocity, dur_s) * vol_scale
                mix_mono(wave, start_idx, pan_0_1, rev_send)
            elif track.program == 4:   # Rhodes Electric Piano
                wave = synth_rhodes(note.pitch, note.velocity, dur_s) * vol_scale
                mix_mono(wave, start_idx, pan_0_1, rev_send)
            elif track.program == 11:  # Vibraphone
                wave = synth_vibraphone(note.pitch, note.velocity, dur_s) * vol_scale
                mix_mono(wave, start_idx, pan_0_1, rev_send)
            elif track.program == 8:   # Celesta
                wave = synth_celesta(note.pitch, note.velocity, dur_s) * vol_scale
                mix_mono(wave, start_idx, pan_0_1, rev_send)
            elif track.program == 46:  # Orchestral Harp
                wave = synth_harp(note.pitch, note.velocity, dur_s) * vol_scale
                mix_mono(wave, start_idx, pan_0_1, rev_send)
            elif track.program == 48:  # String Ensemble (native stereo)
                wl, wr = synth_string_pad(note.pitch, note.velocity, dur_s)
                end_idx = min(total_samples, start_idx + len(wl))
                seg_l = wl[: end_idx - start_idx] * vol_scale
                seg_r = wr[: end_idx - start_idx] * vol_scale
                dry_bus[start_idx:end_idx, 0] += seg_l
                dry_bus[start_idx:end_idx, 1] += seg_r
                rev_send_bus[start_idx:end_idx, 0] += seg_l * rev_send
                rev_send_bus[start_idx:end_idx, 1] += seg_r * rev_send
            elif track.program == 33:  # Fingered Bass
                wave = synth_fingered_bass(note.pitch, note.velocity, dur_s) * vol_scale
                mix_mono(wave, start_idx, pan_0_1, rev_send)

    # Apply concert hall reverb + subtle seaside ambience
    wet_bus = apply_stereo_concert_reverb(rev_send_bus)
    ambience = synth_seaside_ambience(total_samples, rng)
    mix = dry_bus + wet_bus + ambience

    # Mastering: remove DC offset, gentle soft-knee saturation, clean fade-out, normalize to -1.0 dBFS
    sos_dc = signal.butter(1, 22.0, btype="highpass", fs=SAMPLE_RATE, output="sos")
    mix = signal.sosfilt(sos_dc, mix, axis=0)

    # Gentle console-style soft saturation
    peak_raw = float(np.max(np.abs(mix)))
    if peak_raw > 1e-6:
        mix = mix / peak_raw
    mix = np.tanh(mix * 1.35) / math.tanh(1.35)

    # Master fade-out over final 2.0 seconds
    fade_samples = int(2.0 * SAMPLE_RATE)
    if total_samples > fade_samples:
        fade_curve = np.linspace(1.0, 0.0, fade_samples) ** 1.6
        mix[-fade_samples:, 0] *= fade_curve
        mix[-fade_samples:, 1] *= fade_curve

    peak = float(np.max(np.abs(mix)))
    target_peak = 10.0 ** (-1.0 / 20.0)  # -1.0 dBFS (~0.891)
    if peak > 1e-6:
        mix *= target_peak / peak

    return mix


def write_wav_and_mp3(stereo_mix: np.ndarray, mp3_path: Path) -> None:
    """Encode stereo float64 waveform [-1, 1] to 192 kbps MP3 via FFmpeg."""
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        raise RuntimeError("ffmpeg not found in PATH")

    pcm16 = np.clip(np.round(stereo_mix * 32767.0), -32768, 32767).astype(np.int16)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_wav = Path(tmp.name)

    try:
        num_frames = pcm16.shape[0]
        byte_data = pcm16.tobytes()
        with open(tmp_wav, "wb") as wf:
            wf.write(b"RIFF")
            wf.write(struct.pack("<I", 36 + len(byte_data)))
            wf.write(b"WAVEfmt ")
            wf.write(struct.pack("<IHHIIHH", 16, 1, 2, SAMPLE_RATE, SAMPLE_RATE * 4, 4, 16))
            wf.write(b"data")
            wf.write(struct.pack("<I", len(byte_data)))
            wf.write(byte_data)

        subprocess.run(
            [
                ffmpeg_bin,
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(tmp_wav),
                "-codec:a",
                "libmp3lame",
                "-b:a",
                "192k",
                "-ar",
                str(SAMPLE_RATE),
                "-ac",
                "2",
                str(mp3_path),
            ],
            check=True,
        )
    finally:
        if tmp_wav.exists():
            os.remove(tmp_wav)


def main() -> None:
    out_dir = Path(__file__).resolve().parent
    mid_path = out_dir / "seaside_stroll.mid"
    mp3_path = out_dir / "seaside_stroll.mp3"

    print("Composing MIDI score: 'Seaside Stroll (Shonan Breeze & Sunlit Tide)'...")
    midi_bytes, tracks, tempo_events = compose_piece()
    mid_path.write_bytes(midi_bytes)

    total_notes = sum(len(t.notes) for t in tracks)
    print(f"Wrote {mid_path.name} ({len(midi_bytes):,} bytes, {len(tracks)} tracks, {total_notes} notes).")

    print("Synthesizing stereo audio at 44.1 kHz and encoding MP3...")
    stereo_mix = render_tracks_to_stereo(tracks, tempo_events)
    write_wav_and_mp3(stereo_mix, mp3_path)

    duration_s = stereo_mix.shape[0] / SAMPLE_RATE
    rms_db = 20.0 * math.log10(float(np.sqrt(np.mean(stereo_mix ** 2))) + 1e-12)
    peak_db = 20.0 * math.log10(float(np.max(np.abs(stereo_mix))) + 1e-12)
    print(
        f"Wrote {mp3_path.name} ({mp3_path.stat().st_size:,} bytes, "
        f"duration={duration_s:.2f}s, RMS={rms_db:.2f} dBFS, Peak={peak_db:.2f} dBFS)."
    )


if __name__ == "__main__":
    main()
