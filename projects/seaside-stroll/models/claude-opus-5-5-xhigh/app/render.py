"""Render seaside_stroll.mid to seaside_stroll.mp3 with sample-free synthesis.

The renderer reads only the MIDI file (through smf.read_midi) and synthesizes
each General MIDI program it uses with NumPy and SciPy:

  Ocarina (79)          monophonic phrases with glides, delayed vibrato, and breath
  Glockenspiel (9)      inharmonic bar partials and a mallet click
  Nylon guitar (24)     Karplus-Strong strings tuned with an allpass, plus body EQ
  Electric piano (4)    two-operator FM with a tine ping and stereo tremolo
  Strings (48, 49)      detuned band-limited sawtooth ensembles
  Finger bass (33)      additive partials with a plucked thump
  Seashore (122)        filtered noise swells, one per note
  Bird tweet (123)      distant gull calls from swept harmonics
  Percussion (ch. 10)   kick, side stick, snare, hats, crash, tambourine, shaker,
                        triangle, and toms

Volume (CC7), expression (CC11), pan (CC10), and reverb send (CC91) come from
the MIDI file. A synthetic stereo impulse response provides the reverb. The
master is normalized to -16 LUFS (ITU-R BS.1770 gating) with a lookahead peak
limiter, and ffmpeg (libmp3lame) encodes the MP3.

Run `python render.py` after `python compose.py`. Noise uses a fixed seed, so
rendering the same MIDI file again gives the same audio.
"""

from functools import lru_cache
from pathlib import Path
import subprocess
import time

import numpy as np
from scipy import signal
from scipy.ndimage import minimum_filter1d, uniform_filter1d

from smf import read_midi

HERE = Path(__file__).resolve().parent
MIDI = HERE / "seaside_stroll.mid"
OUTPUT = HERE / "seaside_stroll.mp3"
SR = 44100
SEED = 20260924
TARGET_LUFS = -16.0
CEILING_DB = -1.5
TAIL = 3.0  # seconds rendered after the last note ends
WET = 0.8  # reverb return level

rng = np.random.default_rng(SEED)
TAU = 2 * np.pi

# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def hz(pitch):
    return 440.0 * 2.0 ** ((np.asarray(pitch, dtype=float) - 69) / 12)


def times(seconds):
    return np.arange(int(round(seconds * SR))) / SR


def loud(velocity):
    """Amplitude for a MIDI velocity."""
    return (np.asarray(velocity, dtype=float) / 127) ** 1.6


def db(value):
    return 20 * np.log10(max(value, 1e-12))


@lru_cache(maxsize=None)
def design(kind, cutoff, order):
    return signal.butter(order, cutoff, kind, fs=SR, output="sos")


def lowpass(x, cutoff, order=2):
    return signal.sosfilt(design("lowpass", float(min(cutoff, 0.45 * SR)), order), x)


def highpass(x, cutoff, order=2):
    return signal.sosfilt(design("highpass", float(cutoff), order), x)


def bandpass(x, low, high, order=2):
    return signal.sosfilt(design("bandpass", (float(low), float(min(high, 0.45 * SR))), order), x)


def peak_eq(x, freq, gain_db, q):
    """RBJ peaking equalizer."""
    a = 10 ** (gain_db / 40)
    w = TAU * freq / SR
    alpha = np.sin(w) / (2 * q)
    return signal.lfilter([1 + alpha * a, -2 * np.cos(w), 1 - alpha * a],
                          [1 + alpha / a, -2 * np.cos(w), 1 - alpha / a], x)


def gate(length, held, attack, fade):
    """1 while a note is held, with a linear attack and a smooth release after note-off."""
    t = np.arange(length) / SR
    rise = np.clip(t / attack, 0, 1) if attack > 0 else 1.0
    return rise * np.clip(1 - (t - held) / fade, 0, 1) ** 2


def smooth(x, seconds):
    size = max(1, int(seconds * SR))
    return uniform_filter1d(uniform_filter1d(x, size, mode="nearest"), size, mode="nearest")


def pan_gains(pan):
    angle = (np.clip(pan, -1, 1) + 1) * np.pi / 4
    return np.cos(angle), np.sin(angle)


# --------------------------------------------------------------------------
# Pitched voices: (pitch, velocity, seconds held) -> mono samples
# --------------------------------------------------------------------------


def nylon(pitch, velocity, held):
    """Karplus-Strong string: the loop runs one period per block, so NumPy does the work."""
    f = float(hz(pitch))
    period = SR / f
    delay = int(period - 0.6)
    frac = period - 0.5 - delay  # the averaging filter adds 0.5; the allpass supplies the rest
    coef = (1 - frac) / (1 + frac)
    t60 = float(np.interp(pitch, [40, 84], [5.0, 1.8]))
    feedback = 10 ** (-3 / (f * t60))
    size = int((held + 0.09) * SR)
    burst = lowpass(rng.uniform(-1, 1, delay), 900 + 3000 * velocity / 127, 1)
    burst -= 0.7 * np.roll(burst, max(1, int(0.18 * delay)))  # plucking point
    burst -= burst.mean()
    burst /= np.sqrt(np.mean(burst ** 2)) + 1e-9
    b = feedback * 0.5 * np.array([coef, 1 + coef, 1.0])
    a = np.array([1.0, coef])
    state = np.zeros(2)
    blocks = -(-size // delay)
    out = np.empty(blocks * delay)
    previous = np.zeros(delay)
    for index in range(blocks):
        looped, state = signal.lfilter(b, a, previous, zi=state)
        current = looped + burst if index == 0 else looped
        out[index * delay:(index + 1) * delay] = current
        previous = current
    return 0.3 * loud(velocity) * out[:size] * gate(size, held, 0.0005, 0.08)


def epiano(pitch, velocity, held):
    f = float(hz(pitch))
    v = velocity / 127
    t = times(held + 0.3)
    index = (0.5 + 2.2 * v) * np.exp(-t / 0.4) + 0.25
    y = np.sin(TAU * f * t + index * np.sin(TAU * f * t))
    if 14 * f < 0.45 * SR:
        y += 0.25 * v * np.sin(TAU * 14 * f * t) * np.exp(-t / 0.015)
    decay = float(np.interp(pitch, [48, 86], [3.2, 1.1]))
    return 0.3 * loud(velocity) * y * np.exp(-t / decay) * gate(len(t), held, 0.002, 0.18)


BAR_PARTIALS = [(1.0, 1.0, 1.0), (2.756, 0.28, 0.45), (5.404, 0.1, 0.22), (8.933, 0.04, 0.12)]


def glockenspiel(pitch, velocity, held):
    f = float(hz(pitch))
    ring = float(np.interp(pitch, [79, 108], [1.8, 0.7]))
    t = times(held + 2 * ring)
    y = sum(amp * np.sin(TAU * f * ratio * t) * np.exp(-t / (ring * decay))
            for ratio, amp, decay in BAR_PARTIALS if f * ratio < 0.45 * SR)
    click = highpass(rng.standard_normal(int(0.02 * SR)), 3000) * np.exp(-t[:int(0.02 * SR)] / 0.002)
    y[:len(click)] += 0.15 * click
    return 0.25 * loud(velocity) * y * gate(len(t), held + ring, 0.0005, ring)


TABLE = 2048
TABLE_INDEX = np.arange(TABLE + 1)


def ensemble(pitch, velocity, held, attack, fade, brightness):
    """Three detuned band-limited sawtooth voices read from a per-note wavetable."""
    f = float(hz(pitch))
    t = times(held + fade)
    k = np.arange(1, max(2, int(min(0.4 * SR, 12000) / f)) + 1)
    amps = 1 / k / (1 + (k * f / brightness) ** 2)
    table = amps @ np.sin(TAU * np.outer(k, TABLE_INDEX / TABLE))
    table /= np.abs(table).max()
    vibrato = 0.1 * np.clip((t - 0.25) / 0.4, 0, 1) * np.sin(TAU * 5.2 * t + rng.uniform(0, TAU))
    y = np.zeros(len(t))
    for detune in (-0.07, 0.0, 0.08):
        phase = (rng.uniform() + np.cumsum(f * 2 ** ((detune + vibrato) / 12)) / SR) % 1.0
        y += np.interp(phase * TABLE, TABLE_INDEX, table)
    return 0.12 * loud(velocity) * y * gate(len(t), held, attack, fade)


def string_pad(pitch, velocity, held):
    return ensemble(pitch, velocity, held, 0.35, 0.5, 2600)


def string_legato(pitch, velocity, held):
    return ensemble(pitch, velocity, held, 0.07, 0.25, 3800)


def finger_bass(pitch, velocity, held):
    f = float(hz(pitch))
    v = velocity / 127
    t = times(held + 0.08)
    y = np.zeros(len(t))
    total = 0.0
    for k in range(1, int(min(24, 3000 / f)) + 1):
        amp = k ** -1.25 * (0.55 + 0.45 * v) ** (k - 1)
        y += amp * np.sin(TAU * k * f * t) * np.exp(-t * (0.5 + 0.6 * k))
        total += amp
    y /= total
    y += 0.25 * lowpass(rng.standard_normal(len(t)), 900) * np.exp(-t / 0.01)
    y = np.tanh(2 * y) / np.tanh(2)
    return 0.45 * loud(velocity) * y * gate(len(t), held, 0.004, 0.07)


def fallback(pitch, velocity, held):
    """A plain organ-like tone for programs this renderer has no voice for."""
    f = float(hz(pitch))
    t = times(held + 0.1)
    y = np.sin(TAU * f * t) + 0.3 * np.sin(TAU * 2 * f * t) + 0.1 * np.sin(TAU * 3 * f * t)
    return 0.15 * loud(velocity) * y * gate(len(t), held, 0.01, 0.1)


def gull(pitch, velocity, held):
    base = float(hz(pitch))
    calls = max(1, int(round(held / 0.4)))
    syllable, gap = 0.28, 0.1
    y = np.zeros(int((calls * (syllable + gap) + 0.1) * SR))
    t = times(syllable)
    u = t / syllable
    contour = np.where(u < 0.25, 0.82 + 0.48 * u / 0.25, 1.3 - 0.6 * (u - 0.25) / 0.75)
    for call in range(calls):
        phase = TAU * np.cumsum(base * contour * (1 - 0.04 * call)) / SR
        voice = sum(amp * np.sin(k * phase) for k, amp in enumerate([1, 0.7, 0.45, 0.25, 0.12], 1)
                    if k * base * 1.3 < 0.45 * SR)
        voice *= (1 + 0.35 * np.sin(TAU * 36 * t)) * np.sin(np.pi * u) ** 0.8 * (1 - 0.2 * call)
        start = int(call * (syllable + gap) * SR)
        y[start:start + len(t)] += voice
    return 0.1 * loud(velocity) * lowpass(y, 3500)


def wave(pitch, velocity, held):
    """One breaking wave in stereo: low rumble swells first, foam and hiss peak at the crest."""
    n = int((held + 0.6) * SR)
    t = np.arange(n) / SR
    crest = held * float(np.clip(0.3 + 0.03 * (pitch - 57), 0.25, 0.55))
    body = np.clip(t / crest, 0, 1) ** 2 * np.exp(-np.maximum(t - crest, 0) / (0.35 * (held - crest) + 0.05))
    body *= np.clip((held + 0.6 - t) / 0.6, 0, 1)
    white = rng.standard_normal((2, n))
    bands = [lowpass(white, 380), bandpass(white, 380, 2200), bandpass(white, 2200, 9000)]
    bands = [band / np.sqrt(np.mean(band ** 2)) for band in bands]
    foam = lowpass(rng.standard_normal((2, n)), 14)
    foam = 1 + 0.6 * foam / np.abs(foam).max()
    y = bands[0] * body + 0.55 * bands[1] * body ** 1.6 + 0.3 * bands[2] * foam * body ** 3
    side = rng.uniform(-0.45, 0.45)
    y[0] *= 1 - side
    y[1] *= 1 + side
    return 0.1 * loud(velocity) * y


# --------------------------------------------------------------------------
# Ocarina: each legato phrase is one continuous tone
# --------------------------------------------------------------------------


def ocarina(notes, size):
    out = np.zeros(size)
    phrases, current = [], []
    for note in notes:
        if current and note["t0"] - current[-1]["t1"] > 0.1:
            phrases.append(current)
            current = []
        current.append(note)
    if current:
        phrases.append(current)
    for phrase in phrases:
        first = int((phrase[0]["t0"] - 0.03) * SR)
        stop = min(size, int((phrase[-1]["t1"] + 0.25) * SR))
        t = np.arange(first, stop) / SR
        onsets = np.array([note["t0"] for note in phrase])
        ends = np.array([note["t1"] for note in phrase])
        index = np.clip(np.searchsorted(onsets, t, "right") - 1, 0, len(phrase) - 1)
        since = t - onsets[index]
        depth = np.clip((since - 0.2) / 0.35, 0, 1)
        pitch = smooth(np.array([note["pitch"] for note in phrase], dtype=float)[index], 0.02)
        phase = TAU * np.cumsum(hz(pitch + 0.12 * depth * np.sin(TAU * 5.1 * t))) / SR
        level = smooth(loud([note["velocity"] for note in phrase])[index], 0.03)
        held = np.where(t < ends[index], 1.0, 0.35)
        held[(t < onsets[0]) | (t >= ends[-1])] = 0
        held = smooth(held, 0.012)
        bright = np.clip(level, 0, 1)
        tone = (np.sin(phase) + (0.08 + 0.1 * bright) * np.sin(2 * phase)
                + (0.04 + 0.05 * bright) * np.sin(3 * phase) + 0.015 * np.sin(4 * phase))
        tone *= 1 + 0.05 * depth * np.sin(TAU * 5.1 * t + 0.6)
        breath = bandpass(rng.standard_normal(len(t)), 900, 4500) * (0.03 + 0.1 * np.exp(-since / 0.025))
        out[first:stop] += (tone + breath) * held * level
    return 0.3 * lowpass(out, 6000)


# --------------------------------------------------------------------------
# Percussion
# --------------------------------------------------------------------------

METAL = [3150, 4230, 5470, 6820, 8130, 9510, 11200]
TOMS = {50: 200, 47: 150, 45: 120, 43: 95}
KIT_PAN = {36: 0, 37: 0.1, 38: 0.05, 42: 0.3, 46: 0.3, 49: -0.35, 54: 0.4, 70: -0.3, 81: 0.45,
           50: -0.2, 47: 0.0, 45: 0.2, 43: 0.3}


def metal(t):
    return sum(np.sin(TAU * f * t + rng.uniform(0, TAU)) for f in METAL) / len(METAL)


def drum(key, velocity):
    def noise(t):
        return rng.standard_normal(len(t))

    if key == 36:
        t = times(0.4)
        y = np.sin(TAU * np.cumsum(46 + 80 * np.exp(-t / 0.03)) / SR) * np.exp(-t / 0.18)
        y += 0.25 * lowpass(noise(t), 2500) * np.exp(-t / 0.004)
        gain = 0.45
    elif key == 37:
        t = times(0.15)
        y = (0.6 * np.sin(TAU * 1700 * t) + 0.5 * np.sin(TAU * 480 * t)) * np.exp(-t / 0.02)
        y += 0.8 * bandpass(noise(t), 1500, 7000) * np.exp(-t / 0.012)
        gain = 0.3
    elif key == 38:
        t = times(0.35)
        y = 0.8 * bandpass(noise(t), 1500, 9000) * np.exp(-t / 0.12) + 0.6 * np.sin(TAU * 190 * t) * np.exp(-t / 0.05)
        gain = 0.32
    elif key in (42, 46):
        t = times(0.08 if key == 42 else 0.6)
        y = (highpass(noise(t), 7000) + 0.5 * metal(t)) * np.exp(-t / (0.03 if key == 42 else 0.28))
        gain = 0.16
    elif key == 49:
        t = times(2.8)
        y = (highpass(noise(t), 3000) * np.exp(-t / 0.8) + 0.4 * metal(t) * np.exp(-t / 1.1)) * (1 - np.exp(-t / 0.003))
        gain = 0.11
    elif key == 54:
        t = times(0.25)
        shake = np.exp(-t / 0.07) + 0.5 * (t > 0.012) * np.exp(-np.maximum(t - 0.012, 0) / 0.05)
        y = bandpass(noise(t), 5500, 13000) * shake + 0.3 * metal(t) * np.exp(-t / 0.08)
        gain = 0.11
    elif key == 70:
        t = times(0.12)
        y = bandpass(noise(t), 4000, 11000) * (1 - np.exp(-t / 0.006)) * np.exp(-t / 0.035)
        gain = 0.13
    elif key == 81:
        t = times(2.5)
        y = sum(amp * np.sin(TAU * 1318 * ratio * t) * np.exp(-t * ratio ** 0.5 / 1.6)
                for ratio, amp in [(1, 1), (2.02, 0.5), (3.05, 0.55), (4.1, 0.3), (5.2, 0.25)])
        gain = 0.08
    elif key in TOMS:
        t = times(0.5)
        y = np.sin(TAU * np.cumsum(TOMS[key] * (1 + 0.5 * np.exp(-t / 0.04))) / SR) * np.exp(-t / 0.22)
        y += 0.2 * lowpass(noise(t), 3000) * np.exp(-t / 0.01)
        gain = 0.35
    else:
        return None
    return gain * loud(velocity) * y


def percussion(notes, size):
    out = np.zeros((2, size))
    for note in notes:
        y = drum(note["pitch"], note["velocity"])
        if y is None:
            continue
        start = int(round(note["t0"] * SR))
        stop = min(size, start + len(y))
        left, right = pan_gains(KIT_PAN.get(note["pitch"], 0))
        out[0, start:stop] += left * y[:stop - start]
        out[1, start:stop] += right * y[:stop - start]
    return out


# --------------------------------------------------------------------------
# Tracks, mix, and master
# --------------------------------------------------------------------------


def guitar_body(x):
    return lowpass(peak_eq(peak_eq(x, 105, 4, 1.2), 220, 2.5, 1.4), 5500)


# GM program -> (name, voice, calibration gain, Haas delay in seconds, tremolo depth, post-processing)
VOICES = {
    4: ("Electric piano", epiano, 1.0, 0, 0.2, None),
    9: ("Glockenspiel", glockenspiel, 1.4, 0, 0, None),
    24: ("Nylon guitar", nylon, 0.75, 0, 0, guitar_body),
    33: ("Finger bass", finger_bass, 0.75, 0, 0, None),
    48: ("String pad", string_pad, 1.25, 0.012, 0, lambda x: lowpass(x, 7000)),
    49: ("Legato strings", string_legato, 1.4, 0.009, 0, lambda x: lowpass(x, 8000)),
    79: ("Ocarina", None, 1.0, 0, 0, None),
    122: ("Seashore", wave, 1.6, 0, 0, None),
    123: ("Gulls", gull, 4.0, 0, 0, None),
}


def voiced(notes, voice, size):
    out = None
    for note in notes:
        y = voice(note["pitch"], note["velocity"], note["t1"] - note["t0"])
        if out is None:
            out = np.zeros(y.shape[:-1] + (size,))
        start = int(round(note["t0"] * SR))
        stop = min(size, start + y.shape[-1])
        out[..., start:stop] += y[..., :stop - start]
    return out


def automation(events, controller, default, size):
    """A controller as a per-sample gain: MIDI steps, smoothed over 30 ms to avoid zipper noise."""
    points = [(when, value) for when, number, value in events if number == controller]
    if not points:
        return (default / 127) ** 2
    when = np.array([p[0] for p in points])
    value = np.array([p[1] for p in points], dtype=float)
    index = np.searchsorted(when, np.arange(size) / SR, "right") - 1
    curve = np.where(index >= 0, value[np.maximum(index, 0)], default)
    return uniform_filter1d((curve / 127) ** 2, int(0.03 * SR), mode="nearest")


def initial(events, controller, default):
    return next((value for _, number, value in events if number == controller), default)


def track(channel, program, notes, events, size):
    if channel == 9:
        name, gain = "Percussion", 1.0
        stereo = percussion(notes, size)
    else:
        name, voice, gain, haas, tremolo, post = VOICES.get(program, (f"Program {program}", fallback, 1.0, 0, 0, None))
        mono = ocarina(notes, size) if program == 79 else voiced(notes, voice, size)
        if post:
            mono = post(mono)
        pan = (initial(events, 10, 64) - 64) / 63
        if mono.ndim == 2:
            stereo = mono * np.array([[min(1, 1 - pan)], [min(1, 1 + pan)]])
        else:
            left, right = pan_gains(pan)
            shifted = np.concatenate([np.zeros(int(haas * SR)), mono[:size - int(haas * SR)]]) if haas else mono
            stereo = np.array([left * mono, right * shifted])
            if tremolo:
                wobble = tremolo * np.sin(TAU * 4.2 * np.arange(size) / SR)
                stereo[0] *= 1 + wobble
                stereo[1] *= 1 - wobble
    stereo *= gain * automation(events, 7, 100, size) * automation(events, 11, 127, size)
    return name, stereo, initial(events, 91, 40) / 127


def impulse_response(length=2.6):
    t = times(length)
    delay = int(0.022 * SR)
    out = np.zeros((2, len(t)))
    for side in range(2):
        noise = rng.standard_normal(len(t))
        tail = (lowpass(noise, 700) * 10 ** (-3 * t / 2.3) + bandpass(noise, 700, 4500) * 10 ** (-3 * t / 1.7)
                + highpass(noise, 4500) * 10 ** (-3 * t / 0.8))
        tail *= 1 - np.exp(-t / 0.025)
        out[side, delay:] = tail[:len(t) - delay]
        out[side] /= np.sqrt(np.sum(out[side] ** 2))
    return out


def k_weighting():
    """BS.1770 pre-filter (high shelf) and RLB high-pass as biquads for SR."""
    shelf_gain, shelf_freq, shelf_q = 4.0, 1500.0, 1 / np.sqrt(2)
    a = 10 ** (shelf_gain / 40)
    w = TAU * shelf_freq / SR
    alpha = np.sin(w) / (2 * shelf_q)
    shelf = ([a * ((a + 1) + (a - 1) * np.cos(w) + 2 * np.sqrt(a) * alpha),
              -2 * a * ((a - 1) + (a + 1) * np.cos(w)),
              a * ((a + 1) + (a - 1) * np.cos(w) - 2 * np.sqrt(a) * alpha)],
             [(a + 1) - (a - 1) * np.cos(w) + 2 * np.sqrt(a) * alpha,
              2 * ((a - 1) - (a + 1) * np.cos(w)),
              (a + 1) - (a - 1) * np.cos(w) - 2 * np.sqrt(a) * alpha])
    w = TAU * 38.0 / SR
    alpha = np.sin(w) / (2 * 0.5)
    rlb = ([(1 + np.cos(w)) / 2, -(1 + np.cos(w)), (1 + np.cos(w)) / 2],
           [1 + alpha, -2 * np.cos(w), 1 - alpha])
    return shelf, rlb


def k_weighted(stereo):
    for b, a in k_weighting():
        stereo = signal.lfilter(b, a, stereo)
    return stereo


def active_loudness(stereo):
    """K-weighted loudness of the 400 ms blocks within 30 dB of the loudest one, i.e. while the part plays."""
    y = k_weighted(stereo)
    block = int(0.4 * SR)
    power = np.sum(np.mean(y[:, :y.shape[1] // block * block].reshape(2, -1, block) ** 2, axis=2), axis=0)
    if power.max() <= 0:
        return -np.inf
    return -0.691 + 10 * np.log10(np.mean(power[power > power.max() * 1e-3]))


def loudness(stereo):
    """Integrated loudness in LUFS with the BS.1770 absolute and relative gates."""
    y = k_weighted(stereo)
    block, hop = int(0.4 * SR), int(0.1 * SR)
    energy = np.concatenate([[0.0], np.cumsum(np.sum(y ** 2, axis=0))])
    starts = np.arange(0, y.shape[1] - block + 1, hop)
    power = (energy[starts + block] - energy[starts]) / block
    power = power[-0.691 + 10 * np.log10(power + 1e-20) > -70]
    relative = -0.691 + 10 * np.log10(np.mean(power)) - 10
    return -0.691 + 10 * np.log10(np.mean(power[-0.691 + 10 * np.log10(power) > relative]))


def limit(stereo, lookahead=0.005, hold=0.03):
    """Lookahead peak limiter: the gain never exceeds what keeps each sample under the ceiling."""
    ceiling = 10 ** (CEILING_DB / 20)
    want = np.minimum(1.0, ceiling / np.maximum(np.abs(stereo).max(axis=0), 1e-12))
    gain = minimum_filter1d(want, 2 * int(hold * SR) + 1)
    gain = uniform_filter1d(gain, int(lookahead * SR) + 1)
    return stereo * gain, db(gain.min())


def encode(stereo, path):
    pcm = np.ascontiguousarray(stereo.T, dtype="<f4").tobytes()
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2",
               "-i", "pipe:0", "-codec:a", "libmp3lame", "-q:a", "2", "-map_metadata", "-1",
               "-metadata", "title=Seaside Stroll", "-id3v2_version", "3", str(path)]
    subprocess.run(command, input=pcm, check=True)


def main():
    began = time.perf_counter()
    song = read_midi(MIDI)
    tempo = song["tempo_map"]
    size = int((max(note["t1"] for note in song["notes"]) + TAIL) * SR)
    programs, events = {}, {}
    for _, channel, program in song["programs"]:
        programs.setdefault(channel, program)
    for tick, channel, controller, value in song["controls"]:
        events.setdefault(channel, []).append((tempo.time(tick), controller, value))
    mix = np.zeros((2, size))
    send = np.zeros((2, size))
    for channel in sorted({note["channel"] for note in song["notes"]}):
        notes = [note for note in song["notes"] if note["channel"] == channel]
        name, stereo, reverb = track(channel, programs.get(channel, 0), notes, events.get(channel, []), size)
        print(f"  {name:<16} {len(notes):5d} notes   {active_loudness(stereo):6.1f} LUFS while playing"
              f"   peak {db(np.abs(stereo).max()):6.1f} dBFS   reverb {reverb:.2f}")
        mix += stereo
        send += reverb * stereo
    ir = impulse_response()
    wet = np.array([signal.oaconvolve(channel, response)[:size] for channel, response in zip(highpass(send, 180), ir)])
    master = highpass(mix + WET * wet, 25)
    master *= np.clip(np.arange(size) / (0.05 * SR), 0, 1) * np.clip((size - np.arange(size)) / (2.5 * SR), 0, 1)
    before = loudness(master)
    master, reduction = limit(master * 10 ** ((TARGET_LUFS - before) / 20))
    encode(master, OUTPUT)
    print(f"Wrote {OUTPUT.name}: {size / SR:.1f} s, {loudness(master):.1f} LUFS, "
          f"peak {db(np.abs(master).max()):.1f} dBFS, limiter {reduction:.1f} dB, "
          f"rendered in {time.perf_counter() - began:.0f} s")


if __name__ == "__main__":
    main()
