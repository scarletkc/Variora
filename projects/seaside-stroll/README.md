# Seaside Stroll

[Shared prompt](PROMPT.md) · [Implementations](models/)

Each model writes its own MIDI file and renders its own MP3, so the instrument sounds and mix are part of the result. Each model record describes how its audio was rendered.

## Results

| Implementation | Notes | Preview |
| --- | --- | --- |
| [GPT-6 Astra · xhigh](models/gpt-6-astra-xhigh/) | 68-second MP3 of a 28-bar MIDI piece in D major at 104 BPM, with melody, electric piano, marimba, pad, bass, and percussion parts. One Python script writes the MIDI file and renders it with NumPy synthesis, without samples. | [MP3](models/gpt-6-astra-xhigh/app/seaside_stroll.mp3) · [MIDI](models/gpt-6-astra-xhigh/app/seaside_stroll.mid) · [Source](models/gpt-6-astra-xhigh/app/compose_seaside.py) |
| [SWE-2 · Max](models/swe-2-max/) | 104-second MP3 of a 40-bar MIDI piece in G major at 96 BPM with a rallentando ending: flute lead, viola harmony, electric piano, celesta, string pad, fingered bass, and percussion. One Python script writes the MIDI and renders it with NumPy synthesis plus a quiet surf ambience; ffmpeg encodes the MP3. | [MP3](models/swe-2-max/app/seaside_stroll.mp3) · [MIDI](models/swe-2-max/app/seaside_stroll.mid) · [Source](models/swe-2-max/app/compose_seaside.py) |
| [GPT-6 Sol · max](models/gpt-6-sol-max/) | 32-bar D-major theme at 104 BPM, with flute, electric piano, celesta, guitar, strings, bass, and percussion. A Python script generates the MIDI and renders a 77-second MP3 using sample-free synthesis. | [MP3](models/gpt-6-sol-max/app/seaside_stroll.mp3) · [MIDI](models/gpt-6-sol-max/app/seaside_stroll.mid) · [Source](models/gpt-6-sol-max/app/compose.py) |
