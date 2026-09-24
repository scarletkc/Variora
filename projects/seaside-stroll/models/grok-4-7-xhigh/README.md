# Grok 4.7 · xhigh

| Field | Value |
| --- | --- |
| Model | Grok 4.7 |
| Reasoning effort | xhigh |
| Provider | xAI |
| Harness | Grok Build CLI 1.0.41 (4220f3b224a6) |

## Assistance used

- Skills: none
- Tools and plugins: Python 3.13.14, NumPy 2.4.0, and ffmpeg 8.1.2 to write the MIDI, synthesize it, and encode the MP3. ffprobe and the repository MIDI reader in `site/scripts/midi.mjs` were used to check the files.
- Subagents: none

## Run

From `app/`, with ffmpeg on `PATH`:

```
python -m pip install -r requirements.txt
python compose.py
```

The script writes `seaside_stroll.mid` and `seaside_stroll.mp3` next to itself, and `../screenshots/preview.png`, a waveform of the mix. Play the MP3 in any player. The MIDI uses General MIDI program numbers and channel 10 for percussion. A General MIDI synth will not match this recording; the MP3 uses the script's own timbres.

The committed MP3 and MIDI are the files produced by the run below. Running the script again on the same Python and NumPy should rewrite the same MIDI. The MP3 also depends on the ffmpeg and LAME build.

## Notes

Prompt revision: [`7c21af0d0238423ec0a48ff2ac92504b7a2072c0`](https://github.com/scarletkc/variora/commit/7c21af0d0238423ec0a48ff2ac92504b7a2072c0), `projects/seaside-stroll/PROMPT.md`.

The piece is an original 40-bar stroll in A major, 4/4. It starts at 88 BPM and eases to 72 BPM across the last four bars. Ten tracks, 1225 notes: flute, nylon guitar, electric piano, celesta, strings, fingered bass, music box, vibraphone, and percussion. Markers: Intro, The path, Horizon, Quiet water, Return, Shore.

The MIDI's last note ends at 112.18 seconds. The MP3 is 114.984 seconds, 44.1 kHz stereo, 192 kbps, 2,761,199 bytes. The extra length is the reverb tail of about 2.8 seconds.

This run rendered twice. The first mix left the electric piano, strings, and music box too far under the flute. Their velocities and synth gains were raised, the kick was eased, and the shaker was brought up. The committed files are the second render. Nothing was edited by hand after that render, and no other model revised the piece.

- `seaside_stroll.mid` SHA-256 `631f50dadfb51996c02edca985ee77de5b2ece9ded13764d06c2a2bceb0888d9`
- `seaside_stroll.mp3` SHA-256 `b9bf3f4d7c89ecba409cfddfd1eddd3e6dddf5660a04673523d742c7db0e09c8`

Checks on the committed files:

- The script parsed its own MIDI and required the same note count, 4/4, and three sharps.
- `readMidi` reported format 1, 10 tracks, 480 ticks per quarter, 112.18 seconds, tempo 72–88, 4/4, A major, 1225 notes, and the instruments named above.
- ffprobe: MP3, 44100 Hz, stereo, 192 kbps, duration 114.983719 seconds.
- Decoded PCM peak 0.861, no sample at or above 0.98. Both channels carry the piece (left RMS 0.185, right RMS 0.194). Four-second RMS starts near −22 dB, sits around −13 to −14 dB for the walk, dips to about −16 dB in Quiet water, and falls through the ending into the tail. Median spectral centroid is about 2860 Hz.

The waveform in `screenshots/preview.png` is drawn from that mix. It is not a capture of the website.

This session did not play the file through speakers. The listening checks above are measurements of the decoded audio. A General MIDI playback of the MIDI will use different instrument sounds from the MP3.
