"""Original score: Postcards on the Sea Breeze / 海风里的明信片.

Run: python compose.py
No samples, pretrained music system, downloaded scores, or other models' work.
"""
from pathlib import Path
import json
import random
import re

import mido

HERE = Path(__file__).resolve().parent
PPQ = 960
SEED = 20261014
rng = random.Random(SEED)


def pitch(name):
    match = re.fullmatch(r"([A-G])([b#]?)(-?\d+)", name)
    if not match:
        raise ValueError(name)
    letter, accidental, octave = match.groups()
    return 12 * (int(octave) + 1) + {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[letter] + {"": 0, "b": -1, "#": 1}[accidental]


# Explicit melody, rather than a random walk or chord-tone generator.
# Each string is one complete 4/4 bar. r is a musical rest.
VERSE = [
    "r:0.5 C5:0.5 F5:1 A5:0.5 G5:0.5 F5:0.75 E5:0.25",
    "G5:1 E5:0.5 D5:0.5 C5:1 r:0.5 E5:0.5",
    "F5:0.75 A5:0.25 C6:1 A5:0.5 G5:0.5 F5:1",
    "E5:1 C5:0.5 E5:0.5 G5:1 r:1",
    "F5:0.5 Bb5:0.5 A5:1 F5:0.5 D5:0.5 F5:1",
    "A5:1 G5:0.5 F5:0.5 C5:1 A4:0.5 C5:0.5",
    "D5:0.5 F5:0.5 G5:1 A5:0.5 G5:0.5 F5:1",
    "E5:1 D5:0.5 C5:0.5 G5:0.75 E5:0.25 r:1",
]
PRE = [
    "A5:1 F5:0.5 G5:0.5 A5:1 C6:1",
    "B5:0.5 A5:0.5 G5:1 E5:1 r:0.5 G5:0.5",
    "Bb5:1 A5:0.5 G5:0.5 F5:1 D5:1",
    "C5:0.5 F5:0.5 A5:1 G5:0.5 A5:0.5 C6:1",
    "Bb5:0.5 A5:0.5 G5:1 D5:0.5 F5:0.5 G5:1",
    "A5:0.5 Bb5:0.5 D6:1 C6:1 Bb5:0.5 A5:0.5",
    "G5:1 F5:0.5 G5:0.5 Bb5:1 A5:0.5 G5:0.5",
    "E5:1 G5:0.5 A5:0.5 G5:1 r:0.5 C6:0.5",
]
CHORUS = [
    "C6:1 A5:0.5 G5:0.5 F5:0.75 G5:0.25 A5:1",
    "G5:0.5 E5:0.5 G5:1 C6:1 B5:0.5 G5:0.5",
    "A5:0.75 C6:0.25 D6:1 C6:0.5 A5:0.5 F5:1",
    "G5:1 E5:0.5 G5:0.5 A5:0.75 G5:0.25 E5:1",
    "F5:0.5 Bb5:0.5 D6:1 C6:0.5 Bb5:0.5 A5:1",
    "C6:1 A5:0.5 G5:0.5 F5:1 C5:0.5 F5:0.5",
    "G5:0.75 Bb5:0.25 A5:1 G5:0.5 F5:0.5 D5:1",
    "E5:1 G5:0.5 A5:0.5 G5:1 r:0.5 C6:0.5",
]
BRIDGE = [
    "D5:1 F5:0.5 E5:0.5 D5:1 A4:1",
    "C#5:1 E5:1 G5:0.5 E5:0.5 C#5:1",
    "D5:1 A5:0.5 G5:0.5 F5:1 E5:0.5 D5:0.5",
    "C5:1 A4:1 r:0.5 C5:0.5 F5:1",
    "D5:0.5 F5:0.5 Bb5:1 A5:1 F5:1",
    "G5:1 D5:0.5 F5:0.5 A5:1 G5:1",
    "F5:1 Db5:1 Bb4:0.5 Db5:0.5 F5:1",
    "E5:1 G5:1 Bb5:0.5 A5:0.5 G5:1",
]
TURN = [
    "F5:1 A5:0.5 G5:0.5 F5:1 E5:1",
    "D5:1 F5:0.5 A5:0.5 Bb5:1 A5:1",
    "G5:1 E5:1 D5:0.5 E5:0.5 G5:1",
    "A5:1 F#5:1 r:0.5 A5:0.5 D6:1",
]
OUTRO = [
    "B5:1 A5:0.5 G5:0.5 D5:2",
    "E5:1 G5:0.5 A5:0.5 B5:2",
    "C6:1 B5:0.5 A5:0.5 F#5:1 D5:1",
    "G5:3 r:1",
]

# Root / bass / softly voiced chord pitches, all written in F major.
CHORDS = {
    "F9": (41, 41, [53, 57, 60, 64, 67]),
    "C/E": (36, 40, [52, 55, 60, 62]),
    "Dm9": (38, 38, [53, 57, 60, 64]),
    "Am7": (33, 33, [52, 55, 57, 60]),
    "Bb9": (34, 34, [50, 53, 57, 60]),
    "F/A": (41, 33, [53, 57, 60, 67]),
    "Gm9": (31, 31, [50, 53, 57, 58]),
    "C13": (36, 36, [52, 57, 58, 62]),
    "Csus": (36, 36, [53, 55, 58, 62]),
    "A7": (33, 33, [49, 52, 55, 57]),
    "Bbm6": (34, 34, [49, 53, 55, 58]),
    "D7": (38, 38, [54, 57, 60, 62]),
}
BASE = ["F9", "C/E", "Dm9", "Am7", "Bb9", "F/A", "Gm9", "C13"]

# Instruments follow zero-based General MIDI program numbers.
INSTRUMENTS = [
    ("Breeze flute", 0, 73, 75),
    ("Felt piano", 1, 0, 76),
    ("Nylon guitar", 2, 24, 63),
    ("Vibraphone", 3, 11, 65),
    ("Warm strings", 4, 48, 70),
    ("Celesta postcards", 5, 8, 58),
    ("Acoustic bass", 6, 32, 81),
    ("Answering clarinet", 7, 71, 61),
    ("Soft coastal kit", 9, None, 62),
]
events = {channel: [] for _, channel, _, _ in INSTRUMENTS}
note_counts = {name: 0 for name, _, _, _ in INSTRUMENTS}
channel_names = {channel: name for name, channel, _, _ in INSTRUMENTS}


def note(channel, start, duration, key, velocity, human=True):
    if not 0 <= key <= 127 or duration <= 0:
        raise ValueError((channel, key, duration))
    shift = rng.uniform(-0.011, 0.011) if human else 0
    on = max(0, round((start + shift) * PPQ))
    off = max(on + 1, round((start + duration + shift) * PPQ))
    vel = max(1, min(127, round(velocity + rng.uniform(-3, 3))))
    events[channel].extend([(on, 1, mido.Message("note_on", channel=channel, note=key, velocity=vel)),
                            (off, 0, mido.Message("note_off", channel=channel, note=key, velocity=0))])
    note_counts[channel_names[channel]] += 1


def melody(bar, score, transpose=0, velocity=79, channel=0):
    cursor = 0.0
    for token in score.split():
        name, value = token.split(":")
        duration = float(value)
        if name != "r":
            note(channel, bar * 4 + cursor, duration * 0.94, pitch(name) + transpose,
                 velocity + (3 if cursor % 2 == 0 else 0))
        cursor += duration
    if abs(cursor - 4) > 1e-8:
        raise ValueError(f"Bar {bar}: {cursor} beats")


bars = []
sections = []


def section(title, chords, tempo, energy, tunes=None, transpose=0):
    sections.append({"name": title, "bar": len(bars) + 1, "tempo": tempo,
                     "key": "G major" if transpose == 2 else "F major"})
    for index, chord in enumerate(chords):
        bars.append({"chord": chord, "bpm": tempo, "energy": energy,
                     "melody": None if tunes is None else tunes[index % len(tunes)],
                     "transpose": transpose, "section": title, "local": index})


section("01 - Sunlight on the water", ["F9", "C/E", "Bb9", "C13"], 102, 0.30)
section("02 - A path beside the sea", BASE * 2, 108, 0.55, VERSE)
section("03 - The horizon opens", ["Dm9", "Am7", "Bb9", "F/A", "Gm9", "Bb9", "Csus", "C13"], 110, 0.73, PRE)
section("04 - Postcards on the sea breeze", BASE * 2, 114, 0.88, CHORUS)
section("05 - A cloud's passing shadow", ["Dm9", "A7", "Dm9", "F/A", "Bb9", "Gm9", "Bbm6", "C13"], 100, 0.40, BRIDGE)
section("06 - Around the headland", ["Dm9", "Bb9", "C13", "D7"], 108, 0.72, TURN)
section("07 - The same sea, a brighter sky", BASE * 2, 116, 1.00, CHORUS, 2)
section("08 - One last look", ["F9", "Dm9", "C13", "F9"], 104, 0.32, OUTRO, 2)
for index, bpm in enumerate([104, 98, 88, 72]):
    bars[-4 + index]["bpm"] = bpm


for bar, info in enumerate(bars):
    start = bar * 4
    trans = info["transpose"]
    root, bass, voicing = CHORDS[info["chord"]]
    root, bass = root + trans, bass + trans
    chord = [key + trans for key in voicing]
    energy = info["energy"]
    local = info["local"]
    is_intro = bar < 4
    is_outro = bar >= len(bars) - 4
    bridge = info["section"].startswith("05")
    if info["melody"]:
        melody(bar, info["melody"], trans, 68 + energy * 19)
    elif bar in (1, 3):
        melody(bar, "r:2 C5:0.5 F5:0.5 A5:0.5 G5:0.5", velocity=53, channel=5)

    # Pulsed piano and flowing fingerpicked guitar, with less motion in the bridge.
    piano_positions = [0, 2] if energy < 0.7 else [0, 1.5, 2.5]
    for position in piano_positions:
        for voice, key in enumerate(chord):
            note(1, start + position + voice * 0.014, 1.32 if energy < 0.7 else 0.88,
                 key + 12, 41 + energy * 22 - voice * 1.5)
    arp = [bass + 12, chord[0] + 12, chord[2] + 12, chord[1] + 12,
           root + 12, chord[-1] + 12, chord[2] + 12, chord[1] + 12]
    for step, key in enumerate(arp):
        if bridge and step % 2:
            continue
        note(2, start + step * 0.5, 0.43 if step % 2 else 0.72, key,
             45 + energy * 15 + (4 if step in (0, 4) else 0))

    # Bass leaves breathing space around the leading melody.
    note(6, start, 1.82, bass, 61 + energy * 21)
    if not is_outro or local < 3:
        note(6, start + 2, 1.70 if energy < 0.7 else 1.30,
             bass if energy < 0.7 else root + 7, 57 + energy * 18)
    if energy > 0.8 and local % 2 == 1:
        next_bass = CHORDS[bars[min(bar + 1, len(bars) - 1)]["chord"]][1] + bars[min(bar + 1, len(bars) - 1)]["transpose"]
        note(6, start + 3.5, 0.42, next_bass - 1, 56)

    # Strings expand from two inner voices to a full upper arrangement.
    if not is_intro:
        string_chord = chord[1:3] if energy < 0.7 else chord[:3]
        for key in string_chord:
            note(4, start + 0.03, 3.80, key + 12, 36 + energy * 22)

    # Short answering phrases avoid duplicating the lead all the way through.
    if info["melody"] and local % 8 in (3, 7) and not is_outro:
        answer = [chord[0] + 12, chord[1] + 12, chord[2] + 12]
        for step, key in enumerate(answer):
            note(7, start + 2.5 + step * 0.5, 0.46, key, 45 + energy * 8)
    if energy >= 0.85 and local % 2 == 0:
        for step, key in enumerate([chord[2] + 24, chord[1] + 24, chord[0] + 24]):
            note(3, start + 1 + step * 0.5, 0.75, key, 38 + energy * 13)
    if is_intro or (energy > 0.85 and local in (0, 4, 8, 12)):
        for step, key in enumerate(chord[:3]):
            note(5, start + 0.5 + step * 0.5, 0.70, key + 24, 46)

    # Small kit, with a soft shaker pulse and syncopated kick.
    if not is_intro and not is_outro:
        for beat in (0, 2):
            note(9, start + beat, 0.15, 36, 47 + energy * 26)
        if energy > 0.8:
            note(9, start + 2.75, 0.15, 36, 48)
        for beat in (1, 3):
            note(9, start + beat + 0.012, 0.10, 37 if energy < 0.7 else 38, 36 + energy * 22)
        for half in range(8):
            note(9, start + half * 0.5, 0.08, 42,
                 29 + energy * 16 + (6 if half % 2 == 0 else -4))
        if energy > 0.8:
            for beat in (1.5, 3.5):
                note(9, start + beat, 0.10, 54, 32)
        if local == 7 and energy >= 0.7:
            for beat, key in ((3.0, 45), (3.5, 47), (3.75, 50)):
                note(9, start + beat, 0.18, key, 50)
    if info["section"].startswith("07") and local in (0, 8):
        note(9, start, 1.2, 49, 46)

# Let the final tonic ring without a mechanical cutoff.
ending = (len(bars) - 1) * 4
for key in (43, 55, 59, 62, 69):
    note(1, ending + 0.03, 4.10, key, 49, human=False)
for key in sorted({55, 59, 62, 69}):
    note(4, ending + 0.08, 4.15, key, 35, human=False)

mid = mido.MidiFile(type=1, ticks_per_beat=PPQ)
conductor = mido.MidiTrack()
mid.tracks.append(conductor)
meta = [(0, mido.MetaMessage("track_name", name="Postcards on the Sea Breeze")),
        (0, mido.MetaMessage("time_signature", numerator=4, denominator=4)),
        (0, mido.MetaMessage("key_signature", key="F"))]
last_bpm = None
for index, info in enumerate(bars):
    if info["bpm"] != last_bpm:
        meta.append((index * 4 * PPQ, mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(info["bpm"]))))
        last_bpm = info["bpm"]
for item in sections:
    meta.append(((item["bar"] - 1) * 4 * PPQ, mido.MetaMessage("marker", text=item["name"])))
meta.append((56 * 4 * PPQ, mido.MetaMessage("key_signature", key="G")))
previous = 0
for tick, message in sorted(meta, key=lambda pair: pair[0]):
    conductor.append(message.copy(time=tick - previous))
    previous = tick
conductor.append(mido.MetaMessage("end_of_track", time=len(bars) * 4 * PPQ - previous))
for name, channel, program, volume in INSTRUMENTS:
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.MetaMessage("track_name", name=name))
    if program is not None:
        track.append(mido.Message("program_change", channel=channel, program=program))
    track.append(mido.Message("control_change", channel=channel, control=7, value=volume))
    track.append(mido.Message("control_change", channel=channel, control=10, value={0:68, 1:54, 2:42, 3:89, 4:64, 5:92, 6:64, 7:38, 9:64}[channel]))
    previous = 0
    for tick, _, message in sorted(events[channel], key=lambda item: (item[0], item[1])):
        track.append(message.copy(time=tick - previous))
        previous = tick
    track.append(mido.MetaMessage("end_of_track", time=max(0, len(bars) * 4 * PPQ - previous)))
mid.save(HERE / "sea_breeze.mid")
summary = {"title": "海风里的明信片 · Postcards on the Sea Breeze", "bars": len(bars),
           "meter": "4/4", "seed": SEED, "ticks_per_beat": PPQ,
           "midi_duration_seconds": round(mid.length, 6), "sections": sections,
           "notes_by_track": note_counts, "total_notes": sum(note_counts.values())}
(HERE / "score.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
