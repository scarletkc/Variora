"""Render snowlit-eve.mid to snowlit-eve.mp3 with the synthesizers in instruments.py.

    python render.py            # build/snowlit-eve.wav and snowlit-eve.mp3
    python render.py --stems    # also one WAV per track in build/stems/
    python render.py --no-mp3   # stop after the WAV

Needs numpy, scipy and an ffmpeg build with libmp3lame on PATH.
"""

import argparse
import shutil
import subprocess
import time
import wave
from pathlib import Path

import numpy as np
from scipy import ndimage, signal

import instruments as ins
import smf

HERE = Path(__file__).resolve().parent
MIDI_PATH = HERE / "snowlit-eve.mid"
MP3_PATH = HERE / "snowlit-eve.mp3"
BUILD = HERE / "build"
FS = ins.FS
SEED = 2412
KIT_TRIM = 6.0  # dB: the synthesized kit runs quieter than the pitched voices
TARGET_LUFS = -14.0
TRUE_PEAK = -1.5  # dBTP; leaves the MP3 encoder room to overshoot and still stay under -1
CEILING = 10 ** (-1.8 / 20)  # sample-peak ceiling; true peak is checked afterwards
TAIL = 6.0  # seconds rendered past the last note-off
LEAD = 0.3  # seconds of silence before the first note

# GM program -> synth voice, level trim (dB) and track EQ.
VOICES = {
    73: ("flute", 0.0, [("highpass", 180, 0.7), ("peak", 2600, 0.9, 1.5)]),
    5: ("electric_piano", 6.0, [("highpass", 70, 0.7), ("peak", 320, 0.9, -3.0), ("highshelf", 6500, 0.7, -2.0)]),
    33: ("bass", 5.5, [("highpass", 32, 0.7), ("peak", 900, 1.0, 1.5), ("lowpass", 4500, 0.7)]),
    48: ("strings", 2.0, [("highpass", 100, 0.7), ("peak", 420, 0.8, -2.0), ("peak", 2800, 0.8, -2.5), ("highshelf", 7000, 0.7, -3.0)]),
    49: ("strings_line", 3.0, [("highpass", 120, 0.7), ("peak", 420, 0.8, -1.5), ("peak", 2800, 0.8, -2.0), ("highshelf", 7500, 0.7, -2.0)]),
    52: ("choir", 2.0, [("highpass", 140, 0.7), ("peak", 450, 0.8, -1.5), ("highshelf", 7000, 0.7, -2.0)]),
    10: ("music_box", -5.0, [("highpass", 200, 0.7), ("peak", 900, 1.0, 1.0)]),
    9: ("glockenspiel", -8.0, [("highpass", 400, 0.7), ("highshelf", 9000, 0.7, -3.0)]),
    46: ("harp", -1.0, [("highpass", 70, 0.7)]),
    14: ("tubular_bell", 0.0, [("highpass", 150, 0.7)]),
    119: ("reverse_cymbal", -4.0, [("highpass", 400, 0.7)]),
}

# GM drum note -> (sound, pan, room send, hall send, level trim dB)
DRUMS = {
    36: ("kick", 0.0, 0.10, 0.00, 0.0),
    37: ("side_stick", -0.08, 0.60, 0.10, -4.0),
    38: ("snare", -0.05, 1.00, 0.25, -1.0),
    42: ("hat", 0.32, 0.25, 0.00, -10.0),
    44: ("hat_pedal", 0.32, 0.20, 0.00, -11.0),
    46: ("hat_open", 0.32, 0.30, 0.05, -10.0),
    49: ("crash", -0.30, 0.40, 0.25, -9.0),
    45: ("tom_low", -0.30, 0.60, 0.15, -2.0),
    47: ("tom_mid", 0.00, 0.60, 0.15, -2.0),
    50: ("tom_high", 0.30, 0.60, 0.15, -2.0),
    54: ("tambourine", -0.45, 0.40, 0.20, -11.0),
    80: ("triangle_muted", 0.55, 0.40, 0.40, -8.0),
    81: ("triangle", 0.55, 0.30, 0.60, -8.0),
    83: ("jingles", 0.38, 0.30, 0.35, -5.0),
    84: ("bell_tree", 0.00, 0.20, 0.70, 0.0),
}


def db(value):
    return 10 ** (value / 20)


# --- MIDI to per-channel events -----------------------------------------------


class Channel:
    def __init__(self, number):
        self.number = number
        self.program = 0
        self.name = f"channel {number + 1}"
        self.notes = []
        self.controls = {}

    def control(self, number, default):
        events = self.controls.get(number)
        return events[0][1] if events else default


def load(path):
    song = smf.read(path)
    channels = {}

    def channel(number):
        return channels.setdefault(number, Channel(number))

    for _, number, program in song.programs:
        channel(number).program = program
    for tick, number, controller, value in song.controls:
        channel(number).controls.setdefault(controller, []).append((LEAD + song.seconds(tick), value))
    names = dict(song.names)
    for start, end, number, pitch, velocity, track in song.notes:
        item = channel(number)
        item.notes.append((LEAD + song.seconds(start), LEAD + song.seconds(end), pitch, velocity))
        item.name = names.get(track, item.name)
    end = max(note[1] for item in channels.values() for note in item.notes)
    return song, channels, end


def pedal(notes, events):
    """Hold note-offs while the sustain pedal is down; a re-struck key cuts its old note."""
    spans, down = [], None
    for moment, value in sorted(events):
        if value >= 64 and down is None:
            down = moment
        elif value < 64 and down is not None:
            spans.append((down, moment))
            down = None
    if down is not None:
        spans.append((down, float("inf")))
    held = []
    for start, end, pitch, velocity in notes:
        for first, last in spans:
            if first <= end < last:
                end = last
                break
        held.append([start, end, pitch, velocity])
    held.sort()
    latest = {}
    for item in held:
        previous = latest.get(item[2])
        if previous is not None and previous[1] > item[0]:
            previous[1] = item[0] + 0.02
        latest[item[2]] = item
    return [tuple(item) for item in held]


def curve(events, total, default=127, seconds=0.03):
    """Per-sample gain from a controller (squared, as General MIDI volume curves)."""
    if not events:
        return None
    moments = np.array([int(moment * FS) for moment, _ in events])
    values = np.array([value for _, value in events], dtype=float)
    index = np.searchsorted(moments, np.arange(total), side="right") - 1
    level = np.where(index >= 0, values[np.maximum(index, 0)], default)
    return ins.smooth((level / 127) ** 2, seconds)


# --- Effects --------------------------------------------------------------------


def eq(audio, bands):
    for band in bands:
        audio = ins.filt(audio, *band)
    return audio


def place(target, audio, start):
    first = int(round(start * FS))
    if first >= target.shape[-1]:
        return
    audio = audio[..., : target.shape[-1] - first]
    target[..., first : first + audio.shape[-1]] += audio


def balance(stereo, pan):
    left = min(1.0, 1.0 - pan) if pan > 0 else 1.0
    right = min(1.0, 1.0 + pan) if pan < 0 else 1.0
    return stereo * np.array([[left], [right]])


def chorus(stereo, mix, rate=0.7, depth=0.0022, base=0.0095):
    n = stereo.shape[1]
    moments = np.arange(n) / FS
    out = stereo.copy()
    for side, offset in ((0, 0.0), (1, np.pi / 2)):
        position = np.arange(n) - (base + depth * np.sin(ins.TAU * rate * moments + offset)) * FS
        index = np.floor(position).astype(np.int64)
        fraction = position - index
        valid = index >= 0
        index = np.clip(index, 0, n - 2)
        source = stereo[1 - side]
        wet = (source[index] * (1 - fraction) + source[index + 1] * fraction) * valid
        out[side] = stereo[side] + mix * wet
    return out / (1 + 0.5 * mix)


def ping_pong(mono, seconds, feedback=0.33, taps=4, cutoff=3200):
    n = len(mono)
    out = np.zeros((2, n))
    echo = mono
    for tap in range(1, taps + 1):
        echo = ins.filt(echo, "lowpass", cutoff) * (feedback if tap > 1 else 1.0)
        shift = int(round(tap * seconds * FS))
        if shift >= n:
            break
        out[(tap + 1) % 2, shift:] += echo[: n - shift]
    return out


def impulse(decays, predelay, seconds, rng, early=10):
    """Stereo reverb impulse: decorrelated noise decaying faster in the treble."""
    n = int(seconds * FS)
    moments = np.arange(n) / FS
    splits = [250, 1000, 4000, 8000]
    tilt = [0.7, 1.0, 1.0, 0.8, 0.55]
    sides = []
    for _ in range(2):
        noise = rng.standard_normal(n)
        bands = [ins.filt(ins.filt(noise, "lowpass", splits[0]), "lowpass", splits[0])]
        for low, high in zip(splits, splits[1:]):
            bands.append(ins.filt(ins.filt(noise, "highpass", low), "lowpass", high))
        bands.append(ins.filt(ins.filt(noise, "highpass", splits[-1]), "highpass", splits[-1]))
        tail = sum(gain * band * np.exp(-6.9078 * moments / decay) for gain, band, decay in zip(tilt, bands, decays))
        tail *= 1 - np.exp(-moments / 0.012)
        for _ in range(early):
            moment = rng.uniform(0.004, 0.07)
            tail[int(moment * FS)] += rng.choice([-1, 1]) * 6.0 * np.exp(-moment / 0.035)
        tail = ins.filt(tail, "lowpass", 11000)
        sides.append(np.concatenate([np.zeros(int(predelay * FS)), tail]))
    ir = np.vstack(sides)
    return ir / np.sqrt((ir**2).sum() / 2)


def reverb(send, ir):
    mono = send.mean(axis=0)
    return np.vstack([signal.oaconvolve(mono, ir[side])[: len(mono)] for side in range(2)])


# --- Loudness and dynamics ------------------------------------------------------


def k_weighted(audio):
    f0, gain, q = 1681.974450955533, 3.999843853973347, 0.7071752369554196
    k = np.tan(np.pi * f0 / FS)
    high = 10 ** (gain / 20)
    low = high**0.4996667741545416
    a0 = 1 + k / q + k * k
    b = [(high + low * k / q + k * k) / a0, 2 * (k * k - high) / a0, (high - low * k / q + k * k) / a0]
    a = [1, 2 * (k * k - 1) / a0, (1 - k / q + k * k) / a0]
    audio = signal.lfilter(b, a, audio, axis=-1)
    f0, q = 38.13547087602444, 0.5003270373238773
    k = np.tan(np.pi * f0 / FS)
    a0 = 1 + k / q + k * k
    return signal.lfilter([1, -2, 1], [1, 2 * (k * k - 1) / a0, (1 - k / q + k * k) / a0], audio, axis=-1)


def block_loudness(audio, size=0.4, hop=0.1):
    weighted = k_weighted(audio)
    power = np.concatenate([[0.0], np.cumsum((weighted**2).sum(axis=0))])
    width, step = int(size * FS), int(hop * FS)
    starts = np.arange(0, max(1, weighted.shape[1] - width + 1), step)
    return (power[starts + width] - power[starts]) / width


def integrated_loudness(audio):
    blocks = block_loudness(audio)
    blocks = blocks[blocks > 10 ** ((-70 + 0.691) / 10)]
    if not len(blocks):
        return -np.inf
    relative = 10 ** ((-0.691 + 10 * np.log10(blocks.mean()) - 10 + 0.691) / 10)
    return -0.691 + 10 * np.log10(blocks[blocks > relative].mean())


def true_peak(audio, chunk=FS * 10):
    peak = 0.0
    for side in audio:
        for first in range(0, len(side), chunk):
            piece = side[max(0, first - 64) : first + chunk + 64]
            peak = max(peak, np.abs(signal.resample_poly(piece, 4, 1)).max())
    return peak


def control_rate(values, hop):
    size = len(values) // hop * hop
    blocks = values[:size].reshape(-1, hop)
    if size < len(values):
        return blocks, values[size:]
    return blocks, None


def glue(audio, threshold=-19.0, ratio=1.5, attack=0.02, release=0.25):
    """Gentle bus compression driven by a 1 ms RMS detector."""
    hop = FS // 1000
    power = (audio**2).mean(axis=0)
    blocks, rest = control_rate(power, hop)
    level = blocks.mean(axis=1)
    if rest is not None:
        level = np.append(level, rest.mean())
    rise, fall = np.exp(-1 / (attack * 1000)), np.exp(-1 / (release * 1000))
    envelope = np.empty_like(level)
    state = level[0]
    for index, value in enumerate(level):
        state = value + (state - value) * (rise if value > state else fall)
        envelope[index] = state
    over = np.maximum(0, 10 * np.log10(envelope + 1e-12) - threshold)
    gain = db(-over * (1 - 1 / ratio))
    return audio * np.interp(np.arange(audio.shape[1]), np.arange(len(gain)) * hop + hop / 2, gain)


def limit(audio, ceiling=CEILING, lookahead=0.005, release=0.12):
    """Look-ahead peak limiter; the gain never lets a sample pass the ceiling."""
    need = np.minimum(1.0, ceiling / np.maximum(np.abs(audio).max(axis=0), 1e-9))
    size = int(lookahead * FS)
    ahead = ndimage.minimum_filter1d(need, 2 * size + 1, mode="nearest")
    hop = 32
    blocks, rest = control_rate(ahead, hop)
    targets = blocks.min(axis=1)
    if rest is not None:
        targets = np.append(targets, rest.min())
    coef = np.exp(-hop / (release * FS))
    gains = np.empty_like(targets)
    state = 1.0
    for index, target in enumerate(targets):
        state = target if target < state else target + (state - target) * coef
        gains[index] = state
    gain = np.repeat(gains, hop)[: audio.shape[1]]
    gain = ndimage.uniform_filter1d(gain, size, mode="nearest")
    return audio * np.minimum(gain, ahead), float(gain.min())


# --- Rendering --------------------------------------------------------------------


def render_voice(kind, item, total, rng):
    """Render one pitched channel into a stereo buffer."""
    out = np.zeros((2, total))
    notes = item.notes
    if kind == "flute":
        phrases, current = [], [notes[0]]
        for note in notes[1:]:
            if note[0] - current[-1][1] < 0.06:
                current.append(note)
            else:
                phrases.append(current)
                current = [note]
        phrases.append(current)
        for group in phrases:
            origin = group[0][0]
            shifted = [(start - origin, end - origin, pitch, velocity) for start, end, pitch, velocity in group]
            place(out, np.vstack([ins.flute_phrase(shifted, rng)] * 2) * 0.7071, origin)
        return out
    if kind == "electric_piano":
        notes = pedal(notes, item.controls.get(64, []))
    for start, end, pitch, velocity in notes:
        duration = max(0.02, end - start)
        if kind in ("strings", "strings_line"):
            sound = ins.strings(pitch, velocity, duration, rng, line=kind == "strings_line")
        elif kind == "choir":
            sound = ins.choir(pitch, velocity, duration, rng)
        elif kind == "reverse_cymbal":
            sound = ins.reverse_cymbal(velocity / 127, duration, rng)
        else:
            mono = getattr(ins, kind)(pitch, velocity, duration, rng)
            spread = {"harp": 0.5, "glockenspiel": 0.35, "music_box": 0.25}.get(kind, 0.0)
            gains = ins.pan_gains(np.clip((pitch - 72) / 24, -1, 1) * spread)
            sound = np.vstack([mono * gains[0], mono * gains[1]])
        place(out, sound, start)
    return out


def render_drums(item, total, rng):
    dry = np.zeros((2, total))
    room = np.zeros((2, total))
    hall = np.zeros((2, total))
    makers = {
        "kick": ins.kick,
        "side_stick": ins.side_stick,
        "snare": ins.snare,
        "hat": lambda v, r: ins.hat(v, r, 0.032 + 0.018 * v),
        "hat_pedal": lambda v, r: ins.hat(v, r, 0.022),
        "hat_open": lambda v, r: ins.hat(v, r, 0.3),
        "crash": ins.crash,
        "tom_low": lambda v, r: ins.tom(v, r, 98),
        "tom_mid": lambda v, r: ins.tom(v, r, 124),
        "tom_high": lambda v, r: ins.tom(v, r, 158),
        "tambourine": ins.tambourine,
        "triangle": ins.triangle,
        "triangle_muted": lambda v, r: ins.triangle(v, r, muted=True),
        "jingles": ins.jingles,
        "bell_tree": ins.bell_tree,
    }
    for start, _, pitch, velocity in item.notes:
        if pitch not in DRUMS:
            continue
        name, pan, room_send, hall_send, trim = DRUMS[pitch]
        sound = makers[name](velocity / 127, rng) * db(trim)
        if sound.ndim == 1:
            left, right = ins.pan_gains(pan)
            sound = np.vstack([sound * left, sound * right])
        else:
            sound = balance(sound, pan)
        place(dry, sound, start)
        if room_send:
            place(room, sound * room_send, start)
        if hall_send:
            place(hall, sound * hall_send, start)
    return dry, room, hall


def write_wav(path, audio, bits=24):
    path.parent.mkdir(parents=True, exist_ok=True)
    scale = 2 ** (bits - 1) - 1
    ints = np.ascontiguousarray(np.clip(np.round(audio.T * scale), -scale - 1, scale).astype("<i4"))
    if bits == 24:
        data = ints.view(np.uint8).reshape(-1, 4)[:, :3].tobytes()
    else:
        data = ints.astype("<i2").tobytes()
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(bits // 8)
        handle.setframerate(FS)
        handle.writeframes(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stems", action="store_true", help="write per-track WAVs to build/stems")
    parser.add_argument("--no-mp3", action="store_true", help="stop after writing the WAV")
    args = parser.parse_args()

    clock = time.perf_counter()
    song, channels, end = load(MIDI_PATH)
    total = int((end + TAIL) * FS)
    rng = np.random.default_rng(SEED)
    beat = song.tempos[0][1] / 1e6 if song.tempos else 0.5
    hall_ir = impulse([2.8, 2.6, 2.2, 1.6, 1.0], 0.024, 3.8, rng)
    room_ir = impulse([1.3, 1.2, 1.0, 0.8, 0.55], 0.008, 1.8, rng, early=14)
    mix = np.zeros((2, total))
    hall = np.zeros((2, total))
    room = np.zeros((2, total))
    stems = {}

    for number in sorted(channels):
        item = channels[number]
        if not item.notes:
            continue
        started = time.perf_counter()
        volume = (item.control(7, 100) / 127) ** 2
        pan = (item.control(10, 64) - 64) / 63
        send = item.control(91, 40) / 127
        depth = item.control(93, 0) / 127
        if number == 9:
            dry, drum_room, drum_hall = render_drums(item, total, rng)
            volume *= db(KIT_TRIM)
            dry *= volume
            room += drum_room * volume * send * 1.6
            hall += drum_hall * volume * send * 1.2
            track = dry
        else:
            kind, trim, bands = VOICES.get(item.program, VOICES[5])
            track = render_voice(kind, item, total, rng)
            track = eq(track, bands)
            expression = curve(item.controls.get(11), total)
            if expression is not None:
                track *= expression
            track = balance(track, pan) * volume * db(trim)
            if depth:
                track = chorus(track, depth * 0.8)
            if kind == "flute":
                echoes = ping_pong(track.mean(axis=0), 0.75 * beat)
                track = track + 0.16 * echoes
            hall += track * send * 0.9
        mix += track
        stems[item.name] = track
        print(f"  {item.name:22s} {len(item.notes):5d} notes  {time.perf_counter() - started:5.1f}s")

    mix += reverb(hall, hall_ir) * 0.7 + reverb(room, room_ir) * 0.8
    mix = ins.filt(mix, "highpass", 28, 0.7)
    gain = db(-20 - integrated_loudness(mix))
    mix = glue(mix * gain)
    lift = db(TARGET_LUFS - integrated_loudness(mix))
    mix *= lift
    gain *= lift
    mix, lowest = limit(mix)
    peak = true_peak(mix)
    if peak > db(TRUE_PEAK):
        mix *= db(TRUE_PEAK) / peak
        peak = true_peak(mix)

    audible = np.nonzero(np.abs(mix).max(axis=0) > db(-72))[0]
    stop = min(total, audible[-1] + int(0.5 * FS)) if len(audible) else total
    mix = mix[:, :stop]
    fade = int(2.0 * FS)
    mix[:, -fade:] *= np.linspace(1, 0, fade) ** 2

    wav = BUILD / "snowlit-eve.wav"
    write_wav(wav, mix)
    loudness = integrated_loudness(mix)
    print(
        f"mix: {mix.shape[1] / FS:.2f}s, {loudness:.2f} LUFS, true peak {20 * np.log10(peak):.2f} dBTP, "
        f"limiter {20 * np.log10(lowest):.2f} dB at most"
    )
    if args.stems:
        # Dry tracks at mix gain, before the shared reverbs, bus compression and limiting.
        for name, track in stems.items():
            write_wav(BUILD / "stems" / f"{name.replace(' ', '-').lower()}.wav", track[:, :stop] * gain)
    if not args.no_mp3:
        if not shutil.which("ffmpeg"):
            raise SystemExit("ffmpeg is required for the MP3 step")
        subprocess.run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(wav),
                "-codec:a", "libmp3lame", "-b:a", "192k", "-fflags", "+bitexact", "-flags:a", "+bitexact",
                "-metadata", "title=Snowlit Eve (雪明かりのイブ)",
                "-metadata", "comment=Composed and rendered in code for Variora (christmas-eve, claude-opus-5-5)",
                str(MP3_PATH),
            ],
            check=True,
        )
        print(f"wrote {MP3_PATH.name}")
    print(f"done in {time.perf_counter() - clock:.1f}s")


if __name__ == "__main__":
    main()
