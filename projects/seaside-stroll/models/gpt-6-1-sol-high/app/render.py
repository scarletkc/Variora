"""Render the committed MIDI itself using original, sample-free synthesis.

NumPy/SciPy -> stereo PCM -> two-pass FFmpeg loudnorm -> 256 kb/s MP3.
No note list or score is imported from compose.py.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import shutil
import subprocess
import tempfile
import time
import wave

import imageio_ffmpeg
import mido
import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

HERE = Path(__file__).resolve().parent
SR = 44100
SEED = 14062026
TAU = 2 * np.pi


def ffmpeg():
    return shutil.which("ffmpeg") or imageio_ffmpeg.get_ffmpeg_exe()


def read_notes(path):
    mid = mido.MidiFile(path)
    program = [0] * 16
    volume = [100] * 16
    pan = [64] * 16
    active = {}
    notes = []
    now = 0.0
    # Mido iteration merges tracks and converts ticks with the tempo map.
    for message in mid:
        now += message.time
        if message.is_meta:
            continue
        channel = message.channel
        if message.type == "program_change":
            program[channel] = message.program
        elif message.type == "control_change" and message.control == 7:
            volume[channel] = message.value
        elif message.type == "control_change" and message.control == 10:
            pan[channel] = message.value
        elif message.type == "note_on" and message.velocity > 0:
            identity = (channel, message.note)
            active.setdefault(identity, []).append((now, message.velocity, program[channel], volume[channel], pan[channel]))
        elif message.type == "note_off" or (message.type == "note_on" and message.velocity == 0):
            identity = (channel, message.note)
            if not active.get(identity):
                raise ValueError(f"Unmatched note-off: {identity}")
            onset, velocity, instrument, level, position = active[identity].pop(0)
            notes.append((onset, max(0.01, now - onset), message.note, velocity, channel, instrument, level, position))
    if any(active.values()):
        raise ValueError("MIDI has unclosed notes")
    return sorted(notes), now


def envelope(t, duration, attack, release):
    rise = np.minimum(1, t / max(attack, 1 / SR))
    fall = np.exp(-np.maximum(t - duration, 0) / release * 6)
    return rise * fall


def filtered_noise(size, rng, cutoff, highpass=False):
    noise = rng.standard_normal(size).astype(np.float32)
    sos = butter(2, cutoff, "highpass" if highpass else "lowpass", fs=SR, output="sos")
    return sosfilt(sos, noise).astype(np.float32)


def percussion(key, velocity, rng):
    duration = {36:0.42, 37:0.13, 38:0.28, 42:0.13, 49:2.4, 54:0.19}.get(key, 0.38)
    t = np.arange(round(duration * SR), dtype=np.float32) / SR
    if key == 36:
        # A tuned low kick: exponential pitch sweep, with a restrained beater.
        phase = TAU * (46 * t + 82 * 0.026 * (1 - np.exp(-t / 0.026)))
        signal = np.sin(phase) * np.exp(-t / 0.095)
        signal += 0.10 * filtered_noise(len(t), rng, 1800) * np.exp(-t / 0.011)
    elif key in (37, 38):
        signal = 0.7 * filtered_noise(len(t), rng, 1700, True) * np.exp(-t / (0.034 if key == 37 else 0.065))
        signal += 0.33 * np.sin(TAU * (440 if key == 37 else 185) * t) * np.exp(-t / 0.031)
    elif key in (42, 49, 54):
        signal = filtered_noise(len(t), rng, 5600 if key == 42 else 2800, True)
        metal = sum(np.sin(TAU * frequency * t) for frequency in (3217, 4511, 6119, 7433)) * 0.10
        signal = (signal * 0.40 + metal) * np.exp(-t / {42:0.027, 49:0.56, 54:0.047}[key])
    else:
        frequency = {45:105, 47:131, 50:165}.get(key, 150)
        signal = (np.sin(TAU * frequency * t) + 0.3 * np.sin(TAU * frequency * 1.48 * t)) * np.exp(-t / 0.090)
    signal *= np.minimum(1, t * SR / 16)
    return signal.astype(np.float32) * (velocity / 127) ** 1.4


def voice(key, duration, velocity, program, rng):
    release = {0:1.5, 24:0.55, 11:1.3, 48:0.95, 8:1.45, 32:0.22, 73:0.25, 71:0.23}.get(program, 0.3)
    t = np.arange(round((duration + release) * SR), dtype=np.float32) / SR
    frequency = 440 * 2 ** ((key - 69) / 12)
    phase = TAU * frequency * t
    strength = (velocity / 127) ** 1.35
    signal = np.zeros(len(t), dtype=np.float32)
    if program in (73, 71):
        # Slow-onset vibrato and a very quiet breath/reed component.
        depth = np.minimum(1, t / 0.32)
        phase = phase + depth * (0.030 if program == 73 else 0.022) * np.sin(TAU * 5.15 * t)
        partials = [1, 0.18, 0.065, 0.028] if program == 73 else [1, 0.045, 0.30, 0.025, 0.10]
        for harmonic, weight in enumerate(partials, 1):
            signal += weight * np.sin(harmonic * phase)
        signal += filtered_noise(len(t), rng, 2400) * 0.020
        signal *= envelope(t, duration, 0.030 if program == 73 else 0.017, release)
        signal *= 0.20 if program == 73 else 0.17
    elif program == 0:
        # Hammer-excited inharmonic strings, with independent partial decay.
        for harmonic in range(1, 11):
            if frequency * harmonic > SR * 0.44:
                break
            decay = (1.65 + 14 / math.sqrt(frequency)) / (1 + harmonic * 0.30)
            inharmonic = harmonic * math.sqrt(1 + 0.000045 * harmonic ** 2)
            beating = 1 + 0.12 * np.sin(TAU * 0.75 * t + harmonic)
            signal += (1 / harmonic ** 1.45) * np.sin(phase * inharmonic) * np.exp(-t / decay) * beating
        signal += filtered_noise(len(t), rng, 2300) * 0.12 * np.exp(-t / 0.014)
        signal *= envelope(t, duration, 0.003, release * 0.30) * 0.26
    elif program == 24:
        # Nylon pluck: the upper harmonics decay faster than the fundamental.
        for harmonic in range(1, 11):
            if frequency * harmonic >= SR * 0.43:
                break
            weight = np.sin(np.pi * harmonic * 0.22) / harmonic ** 1.40
            signal += weight * np.sin(phase * harmonic) * np.exp(-t * (1.0 + harmonic * 0.95))
        signal *= envelope(t, duration, 0.002, release) * 0.44
    elif program in (11, 8):
        # Struck bars / bell tines, including the characteristic 2.76 mode.
        for ratio, weight, decay in ((1, 1, 1.20), (2.76, .29, .55), (5.4, .09, .25), (8.93, .035, .13)):
            if frequency * ratio < SR * 0.44:
                signal += weight * np.sin(phase * ratio) * np.exp(-t / decay)
        if program == 11:
            signal *= 0.86 + 0.14 * np.cos(TAU * 5.4 * t)
        signal *= envelope(t, duration, 0.002, release) * (0.19 if program == 11 else 0.12)
    elif program == 48:
        # A band-limited additive string section, detuned in opposite directions.
        for harmonic in range(1, 9):
            if frequency * harmonic >= SR * 0.42:
                break
            weight = 1 / harmonic ** 1.6
            signal += weight * (np.sin(phase * harmonic * 1.0013 + 0.09 * np.sin(TAU * 4.7 * t))
                                + np.sin(phase * harmonic * 0.9988 + 0.09 * np.sin(TAU * 5.3 * t))) * 0.5
        signal *= envelope(t, duration, 0.26, release) * 0.082
    elif program == 32:
        signal = np.sin(phase) + 0.36 * np.sin(phase * 2) * np.exp(-t / 0.14) + 0.17 * np.sin(phase * 3) * np.exp(-t / 0.07)
        signal *= np.exp(-t / 1.4) * envelope(t, duration, 0.007, release) * 0.47
    else:
        raise ValueError(f"Unsupported MIDI program {program}")
    return (signal * strength).astype(np.float32)


def room(signal):
    # Quiet shared room, rather than different reverbs on every note.
    rng = np.random.default_rng(9914)
    impulse = np.zeros((round(SR * 1.9), 2), dtype=np.float32)
    for channel in range(2):
        for position, gain in ((.031, .13), (.057, .10), (.083, .07), (.127, .055)):
            impulse[round((position + channel * .003) * SR), channel] = gain
        for index in range(180):
            position = rng.uniform(.12, 1.85)
            impulse[round(position * SR), channel] += rng.choice([-1, 1]) * .017 * math.exp(-position / .47)
        impulse[:, channel] = sosfilt(butter(1, 5800, fs=SR, output="sos"), impulse[:, channel])
    result = np.zeros_like(signal)
    for channel in range(2):
        result[:, channel] = fftconvolve(signal[:, channel], impulse[:, channel], mode="full")[:len(signal)]
    return result


def parse_loudnorm(stderr):
    return json.loads(stderr[stderr.rfind("{"):stderr.rfind("}") + 1])


def render(midi_path, output):
    began = time.perf_counter()
    notes, midi_duration = read_notes(midi_path)
    end = max(onset + duration for onset, duration, *_ in notes) + 3.8
    frames = round(end * SR)
    mix = np.zeros((frames, 2), dtype=np.float32)
    send = np.zeros_like(mix)
    rng = np.random.default_rng(SEED)
    gains = {0:1.0, 1:.80, 2:.84, 3:.60, 4:.92, 5:.78, 6:1.0, 7:.70, 9:.65}
    sends = {0:.22, 1:.22, 2:.16, 3:.28, 4:.33, 5:.30, 6:.035, 7:.23, 9:.10}
    for index, (onset, duration, key, velocity, channel, program, level, position) in enumerate(notes):
        mono = percussion(key, velocity, rng) if channel == 9 else voice(key, duration, velocity, program, rng)
        mono *= gains[channel] * level / 100
        angle = position / 127 * np.pi / 2
        stereo = mono[:, None] * np.array([np.cos(angle), np.sin(angle)], dtype=np.float32)
        if channel == 4:
            delay = round(.008 * SR)
            stereo[delay:, 1] = stereo[:-delay, 1]
            stereo[:delay, 1] = 0
        first = round(onset * SR)
        length = min(len(stereo), frames - first)
        mix[first:first + length] += stereo[:length]
        send[first:first + length] += stereo[:length] * sends[channel]
        if index % 800 == 0:
            print(f"Synthesized {index}/{len(notes)} notes", flush=True)
    mix += room(send)
    for channel in range(2):
        mix[:, channel] = sosfilt(butter(2, 28, "highpass", fs=SR, output="sos"), mix[:, channel])
    mix *= .82 / max(float(np.abs(mix).max()), 1e-9)
    fade = round(2.5 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)[:, None] ** 1.6
    mix[:round(.018 * SR)] *= np.linspace(0, 1, round(.018 * SR), dtype=np.float32)[:, None]
    pcm = np.round(np.clip(mix, -1, 1) * 32767).astype("<i2")
    binary = ffmpeg()
    with tempfile.TemporaryDirectory(prefix="variora-sea-breeze-") as temp:
        wav_path = Path(temp) / "render.wav"
        with wave.open(str(wav_path), "wb") as wav:
            wav.setparams((2, 2, SR, 0, "NONE", "not compressed"))
            wav.writeframes(pcm.tobytes())
        target = "loudnorm=I=-16:TP=-1.5:LRA=11"
        first_pass = subprocess.run([binary, "-hide_banner", "-i", str(wav_path), "-af", target + ":print_format=json", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", check=True)
        measurement = parse_loudnorm(first_pass.stderr)
        filters = target + f":measured_I={measurement['input_i']}:measured_TP={measurement['input_tp']}:measured_LRA={measurement['input_lra']}:measured_thresh={measurement['input_thresh']}:offset={measurement['target_offset']}:linear=true:print_format=json"
        encoding = subprocess.run([binary, "-hide_banner", "-y", "-i", str(wav_path), "-af", filters, "-ar", str(SR), "-codec:a", "libmp3lame", "-b:a", "256k", "-id3v2_version", "3", "-metadata", "title=海风里的明信片 / Postcards on the Sea Breeze", "-metadata", "artist=GPT-6.1 Sol (high)", "-metadata", "album=Variora — Seaside Stroll", str(output)], capture_output=True, text=True, encoding="utf-8", check=True)
        mastered = parse_loudnorm(encoding.stderr)
    report = {"sample_rate": SR, "channels": 2, "bitrate": 256000, "seed": SEED,
              "rendered_from": midi_path.name, "midi_sha256": hashlib.sha256(midi_path.read_bytes()).hexdigest(),
              "note_count": len(notes), "midi_duration_seconds": round(midi_duration, 6),
              "pcm_duration_seconds": frames / SR, "loudnorm_input": measurement,
              "loudnorm_output_before_mp3": mastered,
              "render_wall_seconds": round(time.perf_counter() - began, 3),
              "ffmpeg_version": subprocess.run([binary, "-version"], capture_output=True, text=True, check=True).stdout.splitlines()[0],
              "mp3_sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
    (HERE / "render-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--midi", type=Path, default=HERE / "sea_breeze.mid")
    parser.add_argument("--output", type=Path, default=HERE / "sea_breeze.mp3")
    args = parser.parse_args()
    render(args.midi, args.output)
