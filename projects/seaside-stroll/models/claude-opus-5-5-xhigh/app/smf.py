"""Minimal Standard MIDI File (format 1) writer and reader.

compose.py uses the writer to produce seaside_stroll.mid; render.py reads that
file back with the reader, so the MP3 is rendered from the MIDI data alone.
Only the Python standard library is used here.
"""

from bisect import bisect_right
import struct


def _vlq(value):
    out = [value & 0x7F]
    value >>= 7
    while value:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(out))


class Track:
    """Collects events for one MTrk chunk. Times are absolute ticks."""

    def __init__(self, name):
        self.name = name
        self.events = []  # (tick, order, payload bytes)
        self.notes = []  # (start, end, channel, pitch, velocity)
        self.meta(0, 0x03, name.encode("utf-8"))

    def meta(self, tick, kind, data):
        self.events.append((tick, 0, bytes([0xFF, kind]) + _vlq(len(data)) + data))

    def text(self, tick, text):
        self.meta(tick, 0x01, text.encode("utf-8"))

    def marker(self, tick, text):
        self.meta(tick, 0x06, text.encode("utf-8"))

    def tempo(self, tick, bpm):
        micros = round(60_000_000 / bpm)
        self.meta(tick, 0x51, micros.to_bytes(3, "big"))

    def time_signature(self, tick, numerator, denominator):
        power = denominator.bit_length() - 1
        self.meta(tick, 0x58, bytes([numerator, power, 24, 8]))

    def key_signature(self, tick, sharps, minor=False):
        self.meta(tick, 0x59, struct.pack("bB", sharps, 1 if minor else 0))

    def program(self, tick, channel, program):
        self.events.append((tick, 1, bytes([0xC0 | channel, program])))

    def control(self, tick, channel, controller, value):
        value = max(0, min(127, int(round(value))))
        self.events.append((tick, 1, bytes([0xB0 | channel, controller, value])))

    def note(self, start, end, channel, pitch, velocity):
        velocity = max(1, min(127, int(round(velocity))))
        self.notes.append((int(start), int(max(end, start + 1)), channel, pitch, velocity))

    def encode(self):
        events = list(self.events)
        # A repeated pitch on the same channel cuts the previous note short, so
        # every note-on has exactly one matching note-off.
        by_key = {}
        for start, end, channel, pitch, velocity in sorted(self.notes):
            by_key.setdefault((channel, pitch), []).append([start, end, velocity])
        for (channel, pitch), notes in by_key.items():
            for index, (start, end, velocity) in enumerate(notes):
                if index + 1 < len(notes):
                    end = min(end, notes[index + 1][0])
                end = max(end, start + 1)
                events.append((start, 3, bytes([0x90 | channel, pitch, velocity])))
                events.append((end, 2, bytes([0x80 | channel, pitch, 64])))
        events.sort(key=lambda event: (event[0], event[1]))
        body = bytearray()
        last = 0
        for tick, _, payload in events:
            body += _vlq(tick - last) + payload
            last = tick
        body += _vlq(0) + b"\xFF\x2F\x00"
        return b"MTrk" + struct.pack(">I", len(body)) + bytes(body)


def write_midi(path, tracks, ppq):
    header = b"MThd" + struct.pack(">IHHH", 6, 1, len(tracks), ppq)
    with open(path, "wb") as handle:
        handle.write(header + b"".join(track.encode() for track in tracks))


class TempoMap:
    def __init__(self, ppq, tempos):
        self.ppq = ppq
        points = {}
        for tick, micros in sorted(tempos):
            points[tick] = micros
        if 0 not in points:
            points[0] = 500_000
        self.ticks = sorted(points)
        self.micros = [points[tick] for tick in self.ticks]
        self.seconds = [0.0]
        for index in range(1, len(self.ticks)):
            span = self.ticks[index] - self.ticks[index - 1]
            self.seconds.append(self.seconds[-1] + span * self.micros[index - 1] / 1e6 / ppq)

    def time(self, tick):
        index = bisect_right(self.ticks, tick) - 1
        return self.seconds[index] + (tick - self.ticks[index]) * self.micros[index] / 1e6 / self.ppq


def read_midi(path):
    """Parse a Standard MIDI File into notes, controllers, programs, and meta data."""
    with open(path, "rb") as handle:
        data = handle.read()
    if data[:4] != b"MThd":
        raise ValueError("not a Standard MIDI File")
    length, fmt, count, division = struct.unpack(">IHHH", data[4:14])
    if division & 0x8000:
        raise ValueError("SMPTE time division is not supported")
    offset = 8 + length
    tempos, notes, controls, programs, markers, names, keys = [], [], [], [], [], [], []
    for track_index in range(count):
        if data[offset:offset + 4] != b"MTrk":
            raise ValueError("missing MTrk chunk")
        size = struct.unpack(">I", data[offset + 4:offset + 8])[0]
        position, end = offset + 8, offset + 8 + size
        offset = end
        tick, status, name = 0, 0, ""
        open_notes = {}

        def quantity():
            nonlocal position
            value = 0
            while True:
                byte = data[position]
                position += 1
                value = (value << 7) | (byte & 0x7F)
                if not byte & 0x80:
                    return value

        while position < end:
            tick += quantity()
            kind = data[position]
            if kind & 0x80:
                position += 1
            else:
                kind = status
            if kind == 0xFF:
                meta = data[position]
                position += 1
                size = quantity()
                payload = data[position:position + size]
                position += size
                if meta == 0x51:
                    tempos.append((tick, int.from_bytes(payload, "big")))
                elif meta == 0x03 and not name:
                    name = payload.decode("utf-8", "replace")
                elif meta == 0x06:
                    markers.append((tick, payload.decode("utf-8", "replace")))
                elif meta == 0x59:
                    keys.append((tick, struct.unpack("b", payload[:1])[0], payload[1]))
                elif meta == 0x2F:
                    break
                status = 0
            elif kind in (0xF0, 0xF7):
                position += quantity()
                status = 0
            else:
                status = kind
                channel, high = kind & 0x0F, kind & 0xF0
                first = data[position]
                position += 1
                second = 0
                if high not in (0xC0, 0xD0):
                    second = data[position]
                    position += 1
                if high == 0x90 and second:
                    open_notes.setdefault((channel, first), []).append((tick, second))
                elif high in (0x80, 0x90):
                    started = open_notes.get((channel, first))
                    if started:
                        start, velocity = started.pop(0)
                        notes.append({"start": start, "end": tick, "channel": channel,
                                      "pitch": first, "velocity": velocity, "track": track_index})
                elif high == 0xB0:
                    controls.append((tick, channel, first, second))
                elif high == 0xC0:
                    programs.append((tick, channel, first))
        for (channel, pitch), started in open_notes.items():
            for start, velocity in started:
                notes.append({"start": start, "end": tick, "channel": channel,
                              "pitch": pitch, "velocity": velocity, "track": track_index})
        names.append(name)
    tempo_map = TempoMap(division, tempos)
    for note in notes:
        note["t0"] = tempo_map.time(note["start"])
        note["t1"] = tempo_map.time(note["end"])
    notes.sort(key=lambda note: (note["start"], note["channel"], note["pitch"]))
    return {
        "format": fmt,
        "ppq": division,
        "tempo_map": tempo_map,
        "notes": notes,
        "controls": sorted(controls, key=lambda item: item[0]),
        "programs": sorted(programs, key=lambda item: item[0]),
        "markers": markers,
        "keys": keys,
        "track_names": names,
    }
