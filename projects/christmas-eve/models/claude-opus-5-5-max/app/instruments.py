"""Synthesizers for Snowlit Eve.

Every sound is built from oscillators, noise and filters: an FM electric
piano, a breathy flute that is rendered a phrase at a time, bowed and sung
ensembles, plucked and struck additive voices, and a small synthesized
percussion kit with sleigh bells. No recordings or sound banks are used.
"""

import numpy as np
from scipy import signal

FS = 44100
TAU = 2 * np.pi


def hz(pitch):
    return 440.0 * 2.0 ** ((np.asarray(pitch, dtype=float) - 69.0) / 12.0)


def times(seconds):
    return np.arange(int(seconds * FS) + 1) / FS


# --- Filters ------------------------------------------------------------------


def biquad(kind, freq, q=0.7071, gain=0.0):
    """RBJ cookbook biquad coefficients."""
    freq = min(freq, FS * 0.45)
    w = TAU * freq / FS
    cos, sin = np.cos(w), np.sin(w)
    alpha = sin / (2 * q)
    amp = 10 ** (gain / 40)
    if kind == "lowpass":
        b = [(1 - cos) / 2, 1 - cos, (1 - cos) / 2]
        a = [1 + alpha, -2 * cos, 1 - alpha]
    elif kind == "highpass":
        b = [(1 + cos) / 2, -(1 + cos), (1 + cos) / 2]
        a = [1 + alpha, -2 * cos, 1 - alpha]
    elif kind == "bandpass":
        b = [alpha, 0.0, -alpha]
        a = [1 + alpha, -2 * cos, 1 - alpha]
    elif kind == "peak":
        b = [1 + alpha * amp, -2 * cos, 1 - alpha * amp]
        a = [1 + alpha / amp, -2 * cos, 1 - alpha / amp]
    elif kind in ("lowshelf", "highshelf"):
        root = 2 * np.sqrt(amp) * alpha
        if kind == "lowshelf":
            b = [
                amp * ((amp + 1) - (amp - 1) * cos + root),
                2 * amp * ((amp - 1) - (amp + 1) * cos),
                amp * ((amp + 1) - (amp - 1) * cos - root),
            ]
            a = [
                (amp + 1) + (amp - 1) * cos + root,
                -2 * ((amp - 1) + (amp + 1) * cos),
                (amp + 1) + (amp - 1) * cos - root,
            ]
        else:
            b = [
                amp * ((amp + 1) + (amp - 1) * cos + root),
                -2 * amp * ((amp - 1) + (amp + 1) * cos),
                amp * ((amp + 1) + (amp - 1) * cos - root),
            ]
            a = [
                (amp + 1) - (amp - 1) * cos + root,
                2 * ((amp - 1) - (amp + 1) * cos),
                (amp + 1) - (amp - 1) * cos - root,
            ]
    else:
        raise ValueError(kind)
    b, a = np.array(b), np.array(a)
    return b / a[0], a / a[0]


def filt(x, kind, freq, q=0.7071, gain=0.0):
    b, a = biquad(kind, freq, q, gain)
    return signal.lfilter(b, a, x, axis=-1)


def smooth(x, seconds):
    """One-pole smoothing that starts settled on the first value."""
    coef = np.exp(-1.0 / max(1.0, seconds * FS))
    out, _ = signal.lfilter([1 - coef], [1, -coef], x, zi=[coef * x[0]])
    return out


def wander(n, rate, rng):
    """Smooth random motion in [-1, 1] changing about `rate` times a second."""
    points = max(2, int(n / FS * rate) + 2)
    knots = rng.uniform(-1, 1, points)
    return np.interp(np.linspace(0, points - 1, n), np.arange(points), knots)


def saw(phase, step):
    """Band-limited sawtooth (PolyBLEP) for a phase in [0, 1) and step f/FS."""
    out = 2.0 * phase - 1.0
    low = phase < step
    x = phase[low] / step[low]
    out[low] -= x + x - x * x - 1.0
    high = phase > 1.0 - step
    x = (phase[high] - 1.0) / step[high]
    out[high] -= x * x + x + x + 1.0
    return out


def fade_tail(sound, seconds):
    """Taper the end of a note so a buffer that stops early never clicks."""
    size = min(sound.shape[-1], max(8, int(seconds * FS)))
    sound[..., -size:] *= np.cos(np.linspace(0, np.pi / 2, size)) ** 2
    return sound


def pan_gains(pan):
    angle = (np.clip(pan, -1, 1) + 1) * np.pi / 4
    return np.cos(angle), np.sin(angle)


# --- Electric piano ---------------------------------------------------------


def electric_piano(pitch, velocity, duration, rng):
    """Two-operator FM stacks in the manner of a classic FM tine piano."""
    f = float(hz(pitch))
    v = velocity / 127
    ring = float(np.clip(7.5 * (130.0 / f) ** 0.6, 1.4, 9.0))
    length = min(duration, ring * 0.9)
    t = times(length + 0.25)
    body_env = 0.7 * np.exp(-t * 6.9 / ring) + 0.3 * np.exp(-t / 0.45)
    keys = float(np.clip((440.0 / f) ** 0.3, 0.55, 1.25))
    index = (0.25 + 1.55 * v**1.7) * keys * (0.3 + 0.7 * np.exp(-t / 0.55))
    phase = TAU * f * t + rng.uniform(0, TAU)
    body = np.sin(phase + index * np.sin(phase))
    detuned = TAU * f * 1.0011 * t + rng.uniform(0, TAU)
    body2 = np.sin(detuned + 0.6 * index * np.sin(detuned))
    tine_index = (0.3 + 1.5 * v) * float(np.clip(900.0 / f, 0.2, 1.0)) * np.exp(-t / 0.03)
    tine = np.sin(phase + tine_index * np.sin(14.0 * phase)) * np.exp(-t / 0.9)
    tone = body_env * (0.52 * body + 0.3 * body2) + 0.32 * tine
    attack = 1 - np.exp(-t / 0.0012)
    release = np.ones_like(t)
    after = t > length
    release[after] = np.exp(-(t[after] - length) / 0.06)
    return fade_tail(tone * attack * release * (0.15 + 0.85 * v**1.4), 0.12)


# --- Flute ------------------------------------------------------------------


def flute_phrase(notes, rng):
    """Render a run of joined notes [(start, end, pitch, velocity)] as one breath.

    Notes are re-tongued, glide into each other, and grow vibrato as they
    are held. Start and end are in seconds from the first note.
    """
    end = notes[-1][1]
    t = times(end + 0.2)
    n = len(t)
    target = np.empty(n)
    level = np.empty(n)
    onsets = []
    for index, (start, stop, pitch, velocity) in enumerate(notes):
        first = int(start * FS)
        last = int(notes[index + 1][0] * FS) if index + 1 < len(notes) else n
        target[first:last] = pitch
        level[first:last] = velocity / 127
        onsets.append((first, int(stop * FS), velocity / 127))
    target[: int(notes[0][0] * FS)] = notes[0][2]
    level[: int(notes[0][0] * FS)] = notes[0][3] / 127
    glide = smooth(target, 0.016)
    loud = smooth(level, 0.04)

    depth = np.zeros(n)
    articulation = np.ones(n)
    for index, (first, stop, _) in enumerate(onsets):
        held = np.arange(stop - first) / FS
        depth[first:stop] = 0.17 * np.clip((held - 0.22) / 0.5, 0, 1)
        seconds = (stop - first) / FS
        if seconds > 0.55:
            share = held / seconds
            articulation[first:stop] *= 0.9 + 0.18 * np.sin(np.pi * share) ** 1.5
        if index:
            around = np.arange(max(0, first - 900), min(n, first + 1400))
            offset = (around - first) / FS + 0.004
            articulation[around] *= 1 - 0.5 * np.exp(-((offset / 0.02) ** 2))
    depth = smooth(depth, 0.08)
    rate = 5.2 + 0.35 * wander(n, 1.5, rng)
    vibrato = np.sin(TAU * np.cumsum(rate) / FS + rng.uniform(0, TAU))
    scoop = -0.3 * np.exp(-t / 0.04)
    freq = hz(glide + depth * vibrato + scoop + 0.03 * wander(n, 0.7, rng))
    phase = TAU * np.cumsum(freq) / FS
    bright = loud
    tone = (
        np.sin(phase)
        + (0.30 + 0.20 * bright) * np.sin(2 * phase + 0.4)
        + (0.13 + 0.14 * bright) * np.sin(3 * phase + 1.3)
        + (0.05 + 0.07 * bright) * np.sin(4 * phase + 0.6)
        + (0.02 + 0.04 * bright) * np.sin(5 * phase + 2.2)
    )
    noise = rng.standard_normal(n)
    breath = filt(filt(noise, "bandpass", 2400, 0.55), "highpass", 900) * 0.05
    air = filt(rng.standard_normal(n), "lowpass", 260) * np.sin(phase) * 0.5
    chiff = np.zeros(n)
    for first, _, loudness in onsets:
        size = min(n - first, int(0.05 * FS))
        burst = filt(rng.standard_normal(size), "bandpass", 1800 + 1400 * loudness, 1.2)
        chiff[first : first + size] += burst * np.exp(-np.arange(size) / FS / 0.012) * 0.22
    swell = 1 + 0.08 * (depth / 0.17) * np.sin(TAU * np.cumsum(rate) / FS + 0.9)
    envelope = 1 - np.exp(-np.maximum(0, t - notes[0][0]) / 0.03)
    envelope[t < notes[0][0]] = 0
    stop = int(end * FS)
    envelope[stop:] *= np.exp(-(t[stop:] - end) / 0.06)
    body = tone + breath + air * 0.08 + chiff
    return fade_tail(body * envelope * articulation * swell * (0.2 + 0.8 * loud**1.3), 0.1)


# --- Ensembles ----------------------------------------------------------------


def ensemble(pitch, velocity, duration, rng, voices, spread, vibrato, attack, release, width):
    """Detuned band-limited saws spread across the stereo field."""
    f0 = float(hz(pitch))
    t = times(duration + release)
    n = len(t)
    left = np.zeros(n)
    right = np.zeros(n)
    fade_in = np.clip((t - 0.12) / 0.6, 0, 1)
    for voice in range(voices):
        share = voice / (voices - 1) if voices > 1 else 0.5
        cents = spread * (2 * share - 1) + rng.normal(0, spread * 0.15)
        vib = vibrato * fade_in * np.sin(TAU * rng.uniform(4.6, 5.9) * t + rng.uniform(0, TAU))
        drift = 0.05 * wander(n, 1.2, rng)
        freq = f0 * 2.0 ** ((cents / 100 + vib + drift) / 12)
        step = freq / FS
        phase = (rng.uniform() + np.cumsum(step)) % 1.0
        wave = saw(phase, step)
        gain_left, gain_right = pan_gains(width * (2 * share - 1))
        left += gain_left * wave
        right += gain_right * wave
    swell = 1 - np.exp(-t / (attack / 3))
    fade = np.ones(n)
    after = t > duration
    fade[after] = np.exp(-(t[after] - duration) / (release / 3))
    scale = swell * fade / np.sqrt(voices)
    return fade_tail(np.vstack([left * scale, right * scale]), min(0.2, release / 2))


def strings(pitch, velocity, duration, rng, line=False):
    v = velocity / 127
    f = float(hz(pitch))
    attack = (0.16 if line else 0.34) * (1.4 - 0.6 * v)
    out = ensemble(
        pitch, velocity, duration, rng,
        voices=5, spread=7.0 if line else 9.0, vibrato=0.09 if line else 0.06,
        attack=attack, release=0.35 if line else 0.5, width=0.5 if line else 0.8,
    )
    cutoff = f * (2.2 + 3.5 * v) + (1500 if line else 1100)
    out = filt(filt(out, "lowpass", cutoff, 0.6), "lowpass", cutoff * 1.4, 0.5)
    out = filt(out, "highpass", 90)
    return out * (0.35 + 0.65 * v)


FORMANTS = [(650, 80, 1.0), (1050, 90, 0.5), (2750, 120, 0.13), (3500, 140, 0.05)]


def choir(pitch, velocity, duration, rng):
    v = velocity / 127
    out = ensemble(
        pitch, velocity, duration, rng,
        voices=4, spread=13.0, vibrato=0.16, attack=0.45, release=0.7, width=0.7,
    )
    n = out.shape[1]
    onset = 1 - np.exp(-np.arange(n) / FS / 0.15)
    breath = filt(rng.standard_normal((2, n)), "highpass", 500) * 0.05 * onset
    source = out + breath * np.abs(out).mean()
    sung = np.zeros_like(source)
    for freq, width, gain in FORMANTS:
        sung += gain * filt(source, "bandpass", freq, freq / width)
    sung = filt(sung, "lowpass", 5200)
    return fade_tail(sung * 3.2 * (0.3 + 0.7 * v), 0.25)


# --- Plucked and struck voices ----------------------------------------------


def partials(t, f, table, rng):
    """Sum decaying sine partials: table rows are (ratio, amplitude, decay)."""
    out = np.zeros(len(t))
    for ratio, amplitude, decay in table:
        freq = f * ratio
        if freq > 17000 or amplitude <= 0:
            continue
        stop = min(len(t), int(decay * 8 * FS) + 1)
        seg = t[:stop]
        out[:stop] += amplitude * np.exp(-seg / decay) * np.sin(TAU * freq * seg + rng.uniform(0, TAU))
    return out


def plucked(pitch, velocity, duration, rng, ring, place, bright, release, stretch=0.00004, cap=9000):
    f = float(hz(pitch))
    v = velocity / 127
    length = min(duration + release, ring * 3.0)
    t = times(length)
    count = int(max(1, min(30, cap / f)))
    table = []
    for k in range(1, count + 1):
        ratio = k * np.sqrt(1 + stretch * k * k)
        amplitude = abs(np.sin(np.pi * k * place)) / k**1.1 * np.exp(-(k - 1) * bright * (1.25 - v))
        table.append((ratio, amplitude, ring / (1 + 0.09 * (k - 1) ** 1.5)))
    out = partials(t, f, table, rng)
    out *= 1 - np.exp(-t / 0.0015)
    after = t > duration
    out[after] *= np.exp(-(t[after] - duration) / (release / 4))
    return fade_tail(out * (0.2 + 0.8 * v**1.2), 0.12)


def bass(pitch, velocity, duration, rng):
    f = float(hz(pitch))
    v = velocity / 127
    ring = 1.9 * (41.2 / f) ** 0.15
    out = plucked(pitch, velocity, duration, rng, ring, place=0.23, bright=0.12, release=0.1, stretch=0.00012, cap=4200)
    thump = filt(rng.standard_normal(len(out)), "lowpass", 900) * np.exp(-np.arange(len(out)) / FS / 0.006)
    out = out + 0.05 * v * thump
    return np.tanh(1.4 * out) / 1.4


def harp(pitch, velocity, duration, rng):
    f = float(hz(pitch))
    ring = float(np.clip(4.0 * (196.0 / f) ** 0.55, 0.9, 6.0))
    out = plucked(pitch, velocity, duration, rng, ring, place=0.28, bright=0.08, release=0.9)
    return filt(out, "lowpass", 7000)


def music_box(pitch, velocity, duration, rng):
    """A plucked comb tine with a twin for shimmer; it rings out whatever the written length."""
    f = float(hz(pitch))
    v = velocity / 127
    ring = float(np.clip(2.6 * (523.0 / f) ** 0.45, 0.6, 4.0))
    t = times(ring * 2.5)
    out = partials(t, f, [
        (1.0, 1.0, ring),
        (1.0017, 0.35, ring * 0.9),
        (2.0, 0.06, ring * 0.35),
        (5.93, 0.28 * (0.6 + 0.4 * v), 0.1),
        (16.4, 0.07 * v, 0.03),
    ], rng)
    click = filt(rng.standard_normal(len(t)), "highpass", 3000) * np.exp(-t / 0.0015)
    out = (out + 0.12 * v * click) * (1 - np.exp(-t / 0.0004))
    return fade_tail(out * (0.25 + 0.75 * v), ring * 0.8)


def glockenspiel(pitch, velocity, duration, rng):
    """A struck bar with its inharmonic overtones; it rings out whatever the written length."""
    f = float(hz(pitch))
    v = velocity / 127
    ring = float(np.clip(3.2 * (1047.0 / f) ** 0.5, 0.8, 4.5))
    t = times(ring * 2.5)
    out = partials(t, f, [
        (1.0, 1.0, ring),
        (2.756, 0.28 * (0.5 + 0.5 * v), ring * 0.22),
        (5.404, 0.12 * v, ring * 0.08),
        (8.933, 0.05 * v, ring * 0.04),
    ], rng)
    click = filt(rng.standard_normal(len(t)), "bandpass", 5000, 0.8) * np.exp(-t / 0.002)
    out = (out + 0.2 * v * click) * (1 - np.exp(-t / 0.0005))
    return fade_tail(out * (0.25 + 0.75 * v), ring * 0.8)


TUBE_MODES = [
    (0.617, 0.05, 1.2), (1.21, 0.1, 1.0), (2.0, 1.0, 4.5), (2.99, 0.7, 3.2),
    (4.17, 0.4, 2.2), (5.56, 0.22, 1.5), (7.14, 0.1, 0.9),
]


def tubular_bell(pitch, velocity, duration, rng):
    """Tube modes relative to the strike note, each split into a slowly beating pair."""
    f = float(hz(pitch))
    v = velocity / 127
    t = times(9.0)
    table = []
    for ratio, amplitude, decay in TUBE_MODES:
        split = rng.uniform(0.0004, 0.0012)
        table.append((ratio, amplitude * 0.7, decay))
        table.append((ratio * (1 + split), amplitude * 0.3, decay * 0.9))
    out = partials(t, f, table, rng)
    strike = filt(rng.standard_normal(len(t)), "bandpass", 2500, 1.0) * np.exp(-t / 0.008)
    out = (out + 0.15 * strike) * (1 - np.exp(-t / 0.001))
    return fade_tail(out * (0.3 + 0.7 * v) * 0.5, 3.0)


# --- Percussion ---------------------------------------------------------------


def _noise(n, rng):
    return rng.standard_normal(n)


def kick(v, rng):
    t = times(0.8)
    freq = 47 + 72 * np.exp(-t / 0.035) + 28 * np.exp(-t / 0.006)
    body = np.sin(TAU * np.cumsum(freq) / FS) * np.exp(-t / 0.28)
    click = filt(_noise(len(t), rng), "bandpass", 2800, 0.8) * np.exp(-t / 0.003)
    out = np.tanh(1.6 * (0.9 * body + 0.25 * click)) / np.tanh(1.6)
    return fade_tail(out * (1 - np.exp(-t / 0.0008)) * (0.2 + 0.8 * v**1.2), 0.25)


def snare(v, rng):
    t = times(0.7)
    freq = 182 * (1 + 0.18 * np.exp(-t / 0.012))
    tone = 0.7 * np.sin(TAU * np.cumsum(freq) / FS) * np.exp(-t / 0.08)
    tone += 0.3 * np.sin(TAU * 331 * t) * np.exp(-t / 0.05)
    wires = filt(filt(_noise(len(t), rng), "bandpass", 3800, 0.55), "highpass", 1200)
    wires *= np.exp(-t / (0.14 + 0.05 * v))
    out = 0.55 * tone + (0.65 + 0.3 * v) * wires
    return fade_tail(out * (1 - np.exp(-t / 0.0006)) * (0.12 + 0.88 * v**1.3), 0.2)


def side_stick(v, rng):
    t = times(0.15)
    click = filt(_noise(len(t), rng), "bandpass", 2100, 2.0) * np.exp(-t / 0.007)
    tone = 0.6 * np.sin(TAU * 420 * t) * np.exp(-t / 0.016)
    tone += 0.3 * np.sin(TAU * 1480 * t) * np.exp(-t / 0.009)
    return fade_tail((1.4 * click + tone) * (0.2 + 0.8 * v), 0.04)


def metal(t, rng, freqs=(205.3, 304.4, 369.6, 522.7, 540.0, 800.0), scale=1.9):
    out = np.zeros(len(t))
    for freq in freqs:
        out += np.sign(np.sin(TAU * freq * scale * t + rng.uniform(0, TAU)))
    return out / len(freqs)


def hat(v, rng, decay):
    t = times(max(0.15, decay * 7))
    raw = 0.55 * metal(t, rng) + 0.5 * _noise(len(t), rng)
    out = filt(filt(raw, "highpass", 7000), "highpass", 6500)
    out = filt(out, "peak", 10500, 1.0, 3.0)
    out = out * np.exp(-t / decay) * (1 - np.exp(-t / 0.0005)) * (0.15 + 0.85 * v)
    return fade_tail(out, len(t) / FS * 0.3)


def crash(v, rng, seconds=3.5):
    t = times(seconds)
    sides = []
    for _ in range(2):
        raw = 0.5 * metal(t, rng, scale=rng.uniform(2.2, 2.8)) + _noise(len(t), rng)
        tone = filt(filt(raw, "highpass", 2600), "peak", 7500, 0.8, 4.0)
        env = 0.75 * np.exp(-t / 1.25) + 0.6 * np.exp(-t / 0.09)
        sides.append(tone * env * (1 - np.exp(-t / 0.002)))
    return fade_tail(np.vstack(sides) * (0.2 + 0.8 * v) * 0.6, min(1.2, seconds / 3))


def reverse_cymbal(v, seconds, rng):
    swell = crash(v, rng, seconds + 0.3)[:, ::-1]
    swell = swell[:, -int(seconds * FS):]
    size = swell.shape[1]
    fade = np.ones(size)
    rise = int(size * 0.4)
    fade[:rise] = np.sin(np.linspace(0, np.pi / 2, rise)) ** 2
    fade[-int(0.012 * FS):] = np.linspace(1, 0, int(0.012 * FS))
    return swell * fade


def tom(v, rng, base):
    t = times(0.9)
    freq = base * (1 + 0.45 * np.exp(-t / 0.04))
    body = np.sin(TAU * np.cumsum(freq) / FS) * np.exp(-t / 0.3)
    skin = filt(_noise(len(t), rng), "bandpass", base * 5, 0.7) * np.exp(-t / 0.03)
    return fade_tail((0.9 * body + 0.3 * skin) * (1 - np.exp(-t / 0.001)) * (0.15 + 0.85 * v**1.2), 0.3)


def jingles(v, rng):
    """Sleigh bells: a handful of small bells shaken together."""
    t = times(0.45)
    n = len(t)
    out = np.zeros(n)
    count = int(10 + 12 * v)
    for _ in range(count):
        start = int((abs(rng.normal(0, 0.01)) + rng.uniform(0, 0.022)) * FS)
        f = rng.uniform(2700, 5400)
        decay = rng.uniform(0.045, 0.13)
        seg = t[: n - start]
        ring = np.sin(TAU * f * seg) + 0.5 * np.sin(TAU * 1.53 * f * seg + 1.0)
        ring += 0.22 * np.sin(TAU * 2.26 * f * seg + 2.0)
        out[start:] += rng.uniform(0.4, 1.0) * np.exp(-seg / decay) * ring
    rattle = filt(_noise(n, rng), "highpass", 5000) * np.exp(-t / 0.025)
    out = out / np.sqrt(count) + 0.6 * rattle
    return fade_tail(filt(out, "highpass", 1800) * (0.15 + 0.85 * v) * 0.5, 0.12)


def tambourine(v, rng):
    t = times(0.35)
    n = len(t)
    out = np.zeros(n)
    for delay in (0.0, 0.006, 0.013):
        start = int(delay * FS)
        seg = t[: n - start]
        for _ in range(5):
            out[start:] += np.sin(TAU * rng.uniform(6000, 11000) * seg) * np.exp(-seg / rng.uniform(0.05, 0.11))
    hiss = filt(_noise(n, rng), "highpass", 6000) * np.exp(-t / 0.05)
    return fade_tail(filt(0.12 * out + 0.7 * hiss, "highpass", 3000) * (0.15 + 0.85 * v), 0.1)


TRIANGLE_RATIOS = [1.0, 1.18, 2.02, 2.61, 3.16, 3.93, 4.71, 5.43, 6.28, 7.35, 8.62, 9.9]


def triangle(v, rng, muted=False):
    t = times(0.35 if muted else 4.5)
    table = []
    for index, ratio in enumerate(TRIANGLE_RATIOS):
        decay = (3.2 - 2.2 * index / len(TRIANGLE_RATIOS)) * (0.05 if muted else 1.0)
        table.append((ratio, 1 / np.sqrt(index + 1), decay))
    out = partials(t, 1320.0, table, rng)
    return fade_tail(out * (1 - np.exp(-t / 0.0004)) * (0.15 + 0.85 * v) * 0.25, 0.1 if muted else 1.5)


def bell_tree(v, rng):
    """A rising sweep across a mark tree of tiny chimes."""
    t = times(2.6)
    n = len(t)
    left = np.zeros(n)
    right = np.zeros(n)
    count = 26
    for index in range(count):
        share = index / (count - 1)
        start = int(share**1.3 * 0.9 * FS)
        f = 2200 * (7600 / 2200) ** share * rng.uniform(0.98, 1.02)
        seg = t[: n - start]
        chime = np.sin(TAU * f * seg) + 0.35 * np.sin(TAU * 2.71 * f * seg + 1.0)
        chime *= np.exp(-seg / rng.uniform(0.35, 0.8)) * (0.6 + 0.4 * share)
        gain_left, gain_right = pan_gains(1.6 * share - 0.8)
        left[start:] += gain_left * chime
        right[start:] += gain_right * chime
    return fade_tail(np.vstack([left, right]) * (0.15 + 0.85 * v) * 0.08, 0.8)
