# Gemini 4 Argon

| Field            | Value                              |
| ---------------- | ---------------------------------- |
| Model            | Gemini 4 Argon                     |
| Reasoning effort | high                               |
| Provider         | Google                             |
| Harness          | Devin CLI 3000.11.3 (9c803229faa4) |

## Prompt

- Shared brief: [PROMPT.md](../../PROMPT.md) at `7c21af0`.
- Initial message: Quoted below with its additions to `PROMPT.md` listed.

  > 你是 Gemini 4 Argon，思考程度为high，现在请按项目规范完成/projects/seaside-stroll，不要参考其他模型的实现。

  Additions beyond pointing to `PROMPT.md`:
  - Specified the model identity (`Gemini 4 Argon`) and reasoning effort (`high`).
  - Instructed to complete `/projects/seaside-stroll` according to the repository's project rules.
  - Instructed not to reference other models' implementations.

- Later instructions:
  - In response to the agent's pre-submission `ask_user_question` prompt clarifying metadata fields:
    1. `What should be recorded in the 'Provider' field of the model record (models/gemini-4-argon-high/README.md)?` — User selected `Google`.
    2. `Please confirm the exact Model field and directory slug to record in README.md:` — User selected `Gemini 4 Argon (Default)` (`Model: Gemini 4 Argon`, `Reasoning effort: high`, `Harness: Devin CLI 3000.11.3`, directory `models/gemini-4-argon-high/`).
- Repository rules loaded in context: `projects/AGENTS.md` and `site/AGENTS.md`.

## Assistance used

- Skills: `none`
- Tools and plugins: Built-in Devin CLI tools (`find_file_by_name`, `read`, `write`, `edit`, `exec`, `get_output`, `ask_user_question`, `todo_write`) used to inspect project documentation and catalog scripts, create the implementation branch, run `app/compose.py`, verify the generated MIDI and MP3 artifacts, run repository checks, and submit the pull request.
- Subagents: `none`

## Run

Prerequisites:

- Python 3.10+ (tested with Python `3.13.14`)
- `numpy` and `scipy` (tested with `numpy 2.4.0` and `scipy 1.16.3`)
- `ffmpeg` on `PATH` (tested with `ffmpeg 8.1.2`)

Install Python dependencies and run the generator from the repository root:

```bash
pip install -r projects/seaside-stroll/models/gemini-4-argon-high/app/requirements.txt
python projects/seaside-stroll/models/gemini-4-argon-high/app/compose.py
```

This deterministically generates (using fixed seed `20261014`):

- `projects/seaside-stroll/models/gemini-4-argon-high/app/seaside_stroll.mid` (Standard MIDI File Format 1)
- `projects/seaside-stroll/models/gemini-4-argon-high/app/seaside_stroll.mp3` (44.1 kHz, 192 kbps stereo MP3)

## Notes

### Composition & Structure

- **Title:** _Seaside Stroll (Shonan Breeze & Sunlit Tide)_
- **Key & Meter:** Eb major, 4/4 time, 480 ticks per quarter note, 52 bars (2,799 MIDI notes across 11 tracks; 125.97 s MIDI note duration, 129.17 s rendered MP3 with reverb/surf tail).
- **Tempo Arc:** Starts at a relaxed walking tempo of `102 BPM`, dips slightly to `98 BPM` in the reflective Bridge (bars 31–34), accelerates through `100 -> 102 BPM` (bars 35–38) into a radiant `104 BPM` Grand Chorus (bars 39–46), and eases down via a bar-by-bar rallentando (`98 -> 94 -> 89 -> 83 -> 77 -> 72 BPM`) in the Coda (bars 47–52).
- **Sections (marked with SMF meta `0x06` markers):**
  1. `Intro: Sea Breeze & Distant Bells` (Bars 1–6) — Sparkling celesta and orchestral harp arpeggios over `Ebmaj9 -> Abmaj9(#11) -> Ebmaj9/G -> Fm9 -> Abm6 -> Bb13sus4`, joined by fingerstyle nylon guitar and a gentle flute call.
  2. `Theme A: Sunlit Boardwalk` (Bars 7–14) — Main lyrical stroll melody on flute over a light coastal bossa-pop groove with Rhodes electric piano, nylon guitar, fingered bass, and vibraphone turnarounds.
  3. `Theme A': Sparkling Tide Pool` (Bars 15–22) — Melody develops higher with `Eb/G -> Edim7 -> Fm9 -> G7(b9)` chromatic passing harmony, solo violin counter-melody, vibraphone 3rds/6ths, and warm string pads.
  4. `Chorus: Wind Over the Pier` (Bars 23–30) — Japanese anime Royal Road progression (`Abmaj9 -> Bb13sus4 -> Gm7 -> Cm9 -> Fm9 -> G7(b9) -> Cm9 -> Eb9/Bb`) with soaring flute and violin duet and minor-plagal `Abm6` cadence.
  5. `Bridge: Glass Shells & Cloud Shadows` (Bars 31–38) — Intimate dialogue between celesta, Rhodes, and nylon guitar (`Cm9 -> Gm7 -> Abmaj9 -> Eb/G`), followed by an expressive solo violin lead and ascending harp/percussion build.
  6. `Grand Chorus: Golden Horizon` (Bars 39–46) — Full-ensemble climax at 104 BPM reaching `D6`/`Eb6` on the flute with violin harmony, vibraphone and celesta sparkles, full string ensemble, ride cymbal, and syncopated bass.
  7. `Coda: Footprints in the Wet Sand` (Bars 47–52) — Nostalgic subdominant-minor and backdoor harmony (`Abmaj9 -> Abm6 -> Eb/G -> C7(b9) -> Fm9 -> Db9(#11) -> Ebmaj9(#11)`) slowing to a final shimmering harp and celesta chord over fading ocean surf.

### Synthesis & Rendering

- Every instrument is synthesized from scratch in `app/compose.py` without external samples or soundfonts:
  - **Flute (GM 73):** Harmonic series with onset pitch scoop, delayed 5.3 Hz vibrato + coupled tremolo, and bandpass-filtered air-jet breath noise.
  - **Solo Violin (GM 40):** Band-limited bowed string harmonics shaped by three simulated wooden body formant filters (290 Hz, 540 Hz, 1250 Hz), rosin bow attack texture, and 5.7 Hz vibrato.
  - **Nylon Guitar (GM 24):** Plucked-string model with partial-dependent exponential damping, slight inharmonicity, finger-flesh transient, and 192 Hz body resonance.
  - **Rhodes Electric Piano (GM 4):** Dual-modulator FM synthesis combining a 1:1 tonebar modulator and a fast-decaying 7:1 metallic tine chime.
  - **Vibraphone (GM 11) & Celesta (GM 8):** Tuned metallic bar/plate modal ratios (`1 : 4 : 10` with 5.8 Hz motor tremolo for vibraphone; `1 : 2 : 2.756 : 5.404` for celesta).
  - **Orchestral Harp (GM 46) & Warm String Ensemble (GM 48):** Plucked soundboard harmonics for harp; 6 detuned stereo bowed oscillators per note with independent LFOs and warm low-pass filtering for strings.
  - **Fingered Electric Bass (GM 33) & Coastal Percussion (Ch 10):** Velocity-sensitive bass with dynamic harmonic decay; synthesized soft kick, woody cross-stick, brushed snare, shaker, hi-hats, ride cymbal, tambourine, congas, and triangle.
  - **Ambience & Mastering:** Subtle stereo ocean surf (dual-band filtered noise with rolling wave envelopes, ducked during main sections) and three distant gull cries in the intro/outro, mixed through a multi-tap stereo Schroeder/FDN hall reverb, DC-blocked, soft-saturated, and normalized to `-1.00 dBFS` peak (`-13.66 dBFS` overall RMS).

### Checks Performed

- Verified `seaside_stroll.mid` with the site's `readMidi` and `pianoRoll` parser (`site/scripts/midi.mjs`): confirmed Format 1, 11 tracks, 480 TPQ, `4/4` time signature, `Eb major` key signature, 7 section markers, 10 GM instruments, 2,799 notes, and valid piano-roll SVG generation.
- Verified `seaside_stroll.mp3` with `ffprobe` and decoded PCM analysis: confirmed 44,100 Hz stereo, 192 kbps MP3, 129.17 s duration, `-1.00 dBFS` peak, `-13.66 dBFS` RMS, `0.9282` stereo L/R correlation, negligible DC offset (`< 2e-4`), and smooth dynamic progression across all 7 sections.
- Ran repository validation suites (`npm run check`, `npm test`, `npm run format:check`, `npm run build`).
