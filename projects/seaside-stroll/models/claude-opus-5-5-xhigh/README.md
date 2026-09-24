# Claude Opus 5.5 · xhigh

| Field | Value |
| --- | --- |
| Model | claude-opus-5-5 |
| Reasoning effort | xhigh |
| Provider | Anthropic |
| Harness | Claude Code 2.1.281 |

## Assistance used

- Skills: none.
- Tools and plugins: the harnesses' built-in shell, file read/write/edit, search, to-do, and ask-user tools. Python 3.13.14 with NumPy 2.4.0 and SciPy 1.16.3 for composition and synthesis; ffmpeg 8.1.2 (gyan.dev full build, libmp3lame) to encode the MP3 and, during checks, to measure loudness and draw spectrograms; Node.js 24.1.0 to read the MIDI back with the site's `site/scripts/midi.mjs`. Temporary analysis scripts used for the checks below ran outside the repository and are not included.
- Subagents: none.

## Run

```sh
cd projects/seaside-stroll/models/claude-opus-5-5-xhigh/app
python -m pip install -r requirements.txt
python compose.py   # writes seaside_stroll.mid (standard library only)
python render.py    # reads seaside_stroll.mid, writes seaside_stroll.mp3
```

`render.py` needs `ffmpeg` with libmp3lame on `PATH`. It took about 17 seconds on the Windows 11 machine used for the run. Both scripts use the fixed random seed `20260924` (`SEED` in each file); two complete runs with the versions above produced byte-identical files (MD5 `fcb0e5f869ad03d183bbc1d6f9ac882e` for the MIDI, `1ab11c9ba24b2f6877e7e89ba674ce16` for the MP3). Other library versions may change the audio slightly.

## Notes

### Result

- A 151-second MP3 of a 58-bar piece in F major at 100 BPM with a light sixteenth-note swing. The final chorus modulates up a whole step to G major, and the outro slows to 68 BPM. Form: waves (1 bar), intro (4), verse A (8), verse A′ (8), pre-chorus (8), chorus (8), bridge (8), final chorus in G (8), outro (5).
- `compose.py` writes a format-1 MIDI file with a conductor track (tempo map, key change, section markers) and ten parts: ocarina lead, glockenspiel, nylon guitar, electric piano, string pad, legato strings, finger bass, percussion, and General MIDI Seashore and Bird Tweet channels for waves and distant gulls. Accompaniment voicings drop colour tones that sit a semitone from the tune, and timing and velocity are humanized with a fixed seed. `smf.py` is a small Standard MIDI File writer and reader shared by both scripts.
- `render.py` reads only the MIDI file and synthesizes each part without samples or sound banks: Karplus-Strong strings tuned with an allpass for the guitar, two-operator FM for the electric piano, inharmonic partials for the glockenspiel, detuned wavetable sawtooths for the strings, additive partials for the bass, one continuous tone per legato phrase for the ocarina, filtered noise for waves and most percussion, and swept harmonics for the gulls. Volume, expression, pan, and reverb send come from the MIDI controllers; per-voice calibration gains in `render.py` set the balance. A synthetic stereo impulse response supplies the reverb, and the master is normalized to −16 LUFS with a lookahead limiter.

### Run history

The run began in Devin CLI 3000.11.3 with the same model and effort, where `smf.py` and `compose.py` were written; that session was interrupted once and resumed. After it stopped, the user asked Claude Code to continue it; the agent resumed from the earlier session's messages, regenerated the MIDI, wrote `render.py`, adjusted the mix, and wrote this record. No other model's code, MIDI, audio, or record was opened.

There was one attempt; no result was selected from several, and no manual edits were made.

### Checks performed

- **MIDI**: the site's `readMidi` reports format 1, 11 tracks, 147.78 s, tempo 68–100 BPM, 4/4, F major, 3,454 notes, 10 instruments, and the 9 section markers.
- **Harmony**: a scan for lead notes of an eighth or longer that sit a semitone from a sounding accompaniment note flagged 62 of 216 lead notes before the voicing revision and 30 after it. The remaining ones are passing tones and major sevenths such as A over B♭maj7 and were left as written.
- **Tuning**: single-note FFTs of guitar, electric piano, bass, and glockenspiel voices land within 0.4 cents of the target pitch. The string pad reads +5 to +8 cents because of its detuned voices and vibrato.
- **Balance**: K-weighted loudness of each part per section. The first render had the guitar and kick drum nearly level with the lead, and the limiter reduced gain by up to 2.1 dB. The calibration was changed in two passes: guitar −2.5 dB with a softer pluck, kick −6 dB, snare −3 dB, crash −6 dB, tambourine and toms −2 dB, glockenspiel +3 dB, strings +2 to +3 dB, bass −2.5 dB, waves +4 dB, gulls +12 dB. From the verses through the final chorus, the lead now sits 4–12 LU above each accompanying part, and the limiter reduces gain by at most 0.6 dB.
- **Spectrum**: third-octave levels peak around 630–1,000 Hz, where the melody sits, and fall gradually above 1 kHz. A bright band near 175–300 Hz in the spectrogram was checked and matches the accompaniment's chord tones, not a rendering artifact.
- **Loudness**: ffmpeg `ebur128` on the MP3 measures −16.0 LUFS integrated, −1.2 dBTP true peak, and 8.3 LU loudness range.
- **Determinism**: two complete `compose.py` and `render.py` runs produced identical MD5 hashes.

### Known issues

- Nobody listened to the audio during the run. The checks above are measurements and spectrogram images; musical quality and the realism of the synthesized instruments, especially the waves and gulls, were not judged by ear.
- The instruments are simple synthesis models and will sound synthetic next to sampled instruments.
- The MIDI uses General MIDI programs, so other players render it with their own sounds. The Seashore and Bird Tweet channels in particular vary widely between synthesizers.
- The MP3 is 3 seconds longer than the MIDI because the renderer keeps a reverb tail.
- `render.py` handles what this piece uses: it reads pan and reverb send once per channel, skips drum notes outside its kit, and plays unknown programs with a plain organ-like tone.
