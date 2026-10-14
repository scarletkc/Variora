# SWE-2 · max

| Field | Value |
| --- | --- |
| Model | `SWE-2` |
| Reasoning effort | `max` |
| Provider | Cognition |
| Harness | Devin CLI 3000.11.3 |

## Assistance used

- Skills: none
- Tools and plugins: Devin CLI built-in file and shell tools. ffmpeg 8.1.2 (gyan.dev build) is invoked by the generation script to encode MP3.
- Subagents: none

## Run

```sh
cd app
python compose_seaside.py
```

Requires Python 3.13+ with NumPy 2.x and ffmpeg on `PATH`. The script writes `seaside_stroll.mid` and `seaside_stroll.mp3` next to itself. Listen to the MP3 in any player, or load the MIDI into a General MIDI synth or DAW.

## Notes

- 40 bars in 4/4, G major, 96 BPM, with a written rallentando to ~58 BPM across the last two bars. About 101 s of music; the MP3 is ~104 s including the reverb tail.
- Form: 4-bar intro, two 8-bar A statements, an 8-bar bridge, an 8-bar final chorus with viola harmony a diatonic third below the flute, and a 4-bar outro. A-section harmony leans on the IV-V-iii-vi "royal road" progression.
- GM parts: Flute (73) melody, Viola (41) harmony, Electric Piano 2 (5), Celesta (8), String Ensemble 2 (49), Electric Bass fingered (33), and channel-10 percussion (kick, side stick/snare, closed hats, shaker, tambourine, crash).
- The MIDI is written by a small dependency-free Format 1 encoder inside the script (tempo, time-signature, key-signature, program/pan/volume events included).
- Rendering: the same script synthesizes audio with NumPy — per-part additive melodic instruments and filtered-noise percussion, constant-power panning, an FFT-convolution hall using a synthetic decaying-noise impulse response, and a quiet low-passed surf ambience swell. Encoded to MP3 with ffmpeg `libmp3lame -q:a 2`, 44.1 kHz stereo. Synthesis is deterministic (`numpy.random` seed 20260924); no samples or sound banks.
- Checks performed: the site's own MIDI reader (`site/scripts/midi.mjs`) parses the file and reports 1525 notes, 4/4, G major, tempo range 58-96; `ffprobe` validates a 104.4 s MP3; a 4-second-window RMS scan shows the intended dynamic arc (bridge loudest, outro fading out); output peak -1 dBFS.
- One attempt, no retries or follow-up edits. Known limitations: the instruments are deliberately simple synthesized voices rather than sampled GM timbres, so the rendering sounds synth-like by design.
