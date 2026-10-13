"""Check the delivered MIDI and decoded MP3, not just file existence."""
from pathlib import Path
import hashlib
import json
import subprocess

import mido
import numpy as np

from render import ffmpeg, parse_loudnorm

HERE = Path(__file__).resolve().parent
score = json.loads((HERE / "score.json").read_text(encoding="utf-8"))
mid = mido.MidiFile(HERE / "sea_breeze.mid")
notes = 0
overlaps = []
for track in mid.tracks:
    active = {}
    tick = 0
    for event in track:
        tick += event.time
        if event.type == "note_on" and event.velocity:
            identity = (event.channel, event.note)
            if active.get(identity):
                overlaps.append({"track": track.name, "tick": tick, "note": event.note})
            active[identity] = active.get(identity, 0) + 1
            notes += 1
        elif event.type == "note_off" or (event.type == "note_on" and event.velocity == 0):
            identity = (event.channel, event.note)
            assert active.get(identity, 0) > 0, (track.name, identity)
            active[identity] -= 1
    assert not any(active.values()), track.name
assert notes == score["total_notes"]
assert len(mid.tracks) == 10
assert not overlaps, overlaps
markers = []
time = 0.0
for event in mid:
    time += event.time
    if event.type == "marker":
        markers.append({"name": event.text, "seconds": round(time, 3)})
assert len(markers) == 8
binary = ffmpeg()
mp3 = HERE / "sea_breeze.mp3"
decoded = subprocess.run([binary, "-v", "error", "-xerror", "-i", str(mp3), "-f", "f32le", "-ac", "2", "-ar", "44100", "-"], capture_output=True, check=True)
pcm = np.frombuffer(decoded.stdout, dtype="<f4").reshape(-1, 2)
assert np.isfinite(pcm).all()
peak = float(np.abs(pcm).max())
assert 0.1 < peak < .99, peak
duration = len(pcm) / 44100
assert mid.length < duration < mid.length + 5
seconds = len(pcm) // 44100
windows = pcm[:seconds * 44100].reshape(seconds, 44100, 2)
rms = np.sqrt(np.mean(windows ** 2, axis=(1, 2)))
assert float(rms[2:-4].min()) > .002, "Unexpected silence inside the piece"
tail_rms = float(np.sqrt(np.mean(pcm[-8820:] ** 2)))
assert tail_rms < .004, tail_rms
norm = subprocess.run([binary, "-hide_banner", "-i", str(mp3), "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", check=True)
measurement = parse_loudnorm(norm.stderr)
assert -17 < float(measurement["input_i"]) < -15
assert float(measurement["input_tp"]) < -1
report = {"checks": "passed", "midi_tracks": len(mid.tracks), "midi_notes": notes,
          "unclosed_notes": 0, "same_key_overlaps": overlaps, "markers": markers,
          "full_mp3_decode": "passed; FFmpeg -xerror", "duration_seconds": duration,
          "decoded_sample_peak_dbfs": round(20 * float(np.log10(peak)), 3),
          "minimum_interior_one_second_rms": float(rms[2:-4].min()),
          "last_200ms_rms": tail_rms,
          "stereo_correlation": float(np.corrcoef(pcm[::16].T)[0, 1]),
          "integrated_lufs": float(measurement["input_i"]),
          "true_peak_dbtp": float(measurement["input_tp"]),
          "loudness_range_lu": float(measurement["input_lra"]),
          "sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (mp3, HERE / "sea_breeze.mid")},
          "limitations": ["No human listening assessment; metrics do not establish subjective musical quality.",
                          "Custom synth timbres differ from a General MIDI player's instrument sounds."]}
(HERE / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
