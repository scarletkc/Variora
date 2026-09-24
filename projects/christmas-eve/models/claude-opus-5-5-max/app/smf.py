"""Minimal Standard MIDI File writer and reader.

Only what this project needs: format-1 files with PPQ timing, note,
controller and program events, and the common meta events. No third-party
packages are required.
"""

import struct


def _vlq(value):
    out = [value & 0x7F]
    value >>= 7
    while value:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(out))


# Events that share a tick are written in this order, so a note that ends
# where the next one starts is released before it is struck again.
_META, _PROGRAM, _CONTROL, _NOTE_OFF, _NOTE_ON = range(5)


class Track:
    def __init__(self, name=None):
        self.events = []
        self._seq = 0
        if name:
            self.meta(0, 0x03, name.encode("utf-8"))

    def _add(self, tick, order, data):
        if tick < 0:
            raise ValueError("negative tick")
        self.events.append((int(tick), order, self._seq, data))
        self._seq += 1

    def meta(self, tick, kind, payload):
        self._add(tick, _META, bytes([0xFF, kind]) + _vlq(len(payload)) + payload)

    def tempo(self, tick, bpm):
        micros = round(60_000_000 / bpm)
        self.meta(tick, 0x51, micros.to_bytes(3, "big"))

    def time_signature(self, tick, numerator, denominator):
        power = denominator.bit_length() - 1
        self.meta(tick, 0x58, bytes([numerator, power, 24, 8]))

    def key_signature(self, tick, sharps, minor=False):
        self.meta(tick, 0x59, bytes([sharps & 0xFF, 1 if minor else 0]))

    def marker(self, tick, text):
        self.meta(tick, 0x06, text.encode("utf-8"))

    def text(self, tick, text):
        self.meta(tick, 0x01, text.encode("utf-8"))

    def copyright(self, tick, text):
        self.meta(tick, 0x02, text.encode("utf-8"))

    def program(self, tick, channel, program):
        self._add(tick, _PROGRAM, bytes([0xC0 | channel, program]))

    def control(self, tick, channel, controller, value):
        value = max(0, min(127, int(round(value))))
        self._add(tick, _CONTROL, bytes([0xB0 | channel, controller, value]))

    def note(self, tick, duration, channel, pitch, velocity):
        if not 0 <= pitch <= 127:
            raise ValueError(f"pitch out of range: {pitch}")
        velocity = max(1, min(127, int(round(velocity))))
        duration = max(1, int(duration))
        self._add(tick, _NOTE_ON, bytes([0x90 | channel, pitch, velocity]))
        self._add(tick + duration, _NOTE_OFF, bytes([0x80 | channel, pitch, 0]))

    def encode(self):
        body = bytearray()
        now = 0
        for tick, _, _, data in sorted(self.events):
            body += _vlq(tick - now) + data
            now = tick
        body += b"\x00\xff\x2f\x00"
        return b"MTrk" + struct.pack(">I", len(body)) + bytes(body)


def write(path, tracks, ppq):
    header = b"MThd" + struct.pack(">IHHH", 6, 1, len(tracks), ppq)
    with open(path, "wb") as handle:
        handle.write(header)
        for track in tracks:
            handle.write(track.encode())


class Song:
    """A parsed MIDI file with a tempo map in seconds."""

    def __init__(self, ppq, tempos, notes, controls, programs, names, markers):
        self.ppq = ppq
        self.tempos = tempos
        self.notes = notes
        self.controls = controls
        self.programs = programs
        self.names = names
        self.markers = markers
        segments = [(0, 500_000, 0.0)]
        for tick, micros in sorted(tempos):
            last_tick, last_micros, last_seconds = segments[-1]
            seconds = last_seconds + (tick - last_tick) * last_micros / 1e6 / ppq
            if tick == last_tick:
                segments.pop()
            segments.append((tick, micros, seconds))
        self._segments = segments

    def seconds(self, tick):
        chosen = self._segments[0]
        for segment in self._segments:
            if segment[0] <= tick:
                chosen = segment
            else:
                break
        start, micros, seconds = chosen
        return seconds + (tick - start) * micros / 1e6 / self.ppq


def read(path):
    with open(path, "rb") as handle:
        data = handle.read()
    if data[:4] != b"MThd":
        raise ValueError("not a Standard MIDI File")
    length = struct.unpack(">I", data[4:8])[0]
    _, count, ppq = struct.unpack(">HHH", data[8:14])
    if ppq & 0x8000:
        raise ValueError("SMPTE timing is not supported")
    position = 8 + length
    tempos, notes, controls, programs, names, markers = [], [], [], [], [], []
    for index in range(count):
        if data[position : position + 4] != b"MTrk":
            raise ValueError("missing MTrk chunk")
        size = struct.unpack(">I", data[position + 4 : position + 8])[0]
        chunk = data[position + 8 : position + 8 + size]
        position += 8 + size
        cursor, tick, status, open_notes = 0, 0, 0, {}

        def quantity():
            nonlocal cursor
            value = 0
            while True:
                byte = chunk[cursor]
                cursor += 1
                value = (value << 7) | (byte & 0x7F)
                if not byte & 0x80:
                    return value

        while cursor < len(chunk):
            tick += quantity()
            kind = chunk[cursor]
            if kind & 0x80:
                cursor += 1
            else:
                kind = status
            if kind == 0xFF:
                meta = chunk[cursor]
                cursor += 1
                size = quantity()
                payload = chunk[cursor : cursor + size]
                cursor += size
                if meta == 0x51:
                    tempos.append((tick, int.from_bytes(payload, "big")))
                elif meta == 0x03:
                    names.append((index, payload.decode("utf-8", "replace")))
                elif meta == 0x06:
                    markers.append((tick, payload.decode("utf-8", "replace")))
                elif meta == 0x2F:
                    break
                status = 0
            elif kind in (0xF0, 0xF7):
                cursor += quantity()
                status = 0
            else:
                status = kind
                channel = kind & 0x0F
                first = chunk[cursor]
                cursor += 1
                if kind & 0xF0 in (0xC0, 0xD0):
                    second = 0
                else:
                    second = chunk[cursor]
                    cursor += 1
                high = kind & 0xF0
                if high == 0x90 and second > 0:
                    open_notes.setdefault((channel, first), []).append((tick, second))
                elif high in (0x80, 0x90):
                    started = open_notes.get((channel, first))
                    if started:
                        begin, velocity = started.pop(0)
                        notes.append((begin, tick, channel, first, velocity, index))
                elif high == 0xB0:
                    controls.append((tick, channel, first, second))
                elif high == 0xC0:
                    programs.append((tick, channel, first))
        for (channel, pitch), started in open_notes.items():
            for begin, velocity in started:
                notes.append((begin, tick, channel, pitch, velocity, index))
    notes.sort()
    controls.sort()
    programs.sort()
    return Song(ppq, tempos, notes, controls, programs, names, sorted(markers))
