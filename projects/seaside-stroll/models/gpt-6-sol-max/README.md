# GPT-6 Sol · max

| Field | Value |
| --- | --- |
| Model | `gpt-6-sol` |
| Reasoning effort | `max` |
| Provider | OpenAI |
| Harness | Codex desktop app 26.917.9434.0 (Windows) |

## Assistance used

- Skills: `ux-writing` (local skill from [scarletkc/agents](https://github.com/scarletkc/agents), version unknown) for the model record and project listing.
- Tools and plugins: Codex desktop shell and patch tool to write and check the source; Python 3.13.14 and NumPy 2.4.0 to generate the MIDI and synthesize audio; ffmpeg 8.1.2 with libmp3lame to encode the MP3. No external samples, sound banks, or music generation plugins.
- Subagents: none.

## Run

From this directory, with Python 3.13 and `ffmpeg` on `PATH`:

```sh
python -m pip install -r app/requirements.txt
python app/compose.py
```

The script writes `app/seaside_stroll.mid` and `app/seaside_stroll.mp3`. The committed files are the original outputs of this run. The MIDI uses General MIDI program numbers for its tracks; the MP3 uses the script's own synthesized timbres. See [output.json](output.json) for the exact rendering settings.

## Notes

- Prompt revision: [`96e5c1ad9d53d1e42904ce00cadcecc59e172547`](https://github.com/scarletkc/variora/commit/96e5c1ad9d53d1e42904ce00cadcecc59e172547), `projects/seaside-stroll/PROMPT.md`.
- Original result: 32 bars in D major, 4/4 at 104 BPM. A short keyboard and celesta intro leads to a flute theme, a higher middle passage, a return, and a quiet coda. The MP3 includes a three-second reverb tail. The synthesis seed is `61042026`.
- One composition and render run produced the submitted MIDI and MP3. No continuation prompt, manual audio edit, sample, or sound bank was used.
- Checks: Python syntax compilation succeeded. `ffprobe` identified the MP3 as 44.1 kHz stereo, 76.846 seconds. The site catalog parsed the MIDI as 8 tracks, 1,111 notes, D major, 4/4, and 104 BPM; `npm run build` succeeded. The generated MIDI and MP3 were not assessed by a human listening test.
- Isolation disclosure: before reading `projects/AGENTS.md`, this run searched the persistent memory registry for Variora workflow notes. That conflicts with the repository's no-memory rule. No other model's source code, MIDI, MP3, or other generated artifact was opened or used to compose this piece.
- Limitation: the synthetic instrument timbres are approximations rather than recordings of their General MIDI names.
