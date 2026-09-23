# Seaside Stroll

[Shared prompt](PROMPT.md) · [Implementations](models/)

Each model writes its own MIDI file and renders its own MP3, so the instrument sounds and mix are part of the result. Each model record describes how its audio was rendered.

## Results

| Implementation | Notes | Preview |
| --- | --- | --- |
| [GPT-6 Astra · xhigh](models/gpt-6-astra-xhigh/) | 68-second MP3 of a 28-bar MIDI piece in D major at 104 BPM, with melody, electric piano, marimba, pad, bass, and percussion parts. One Python script writes the MIDI file and renders it with NumPy synthesis, without samples. | [MP3](models/gpt-6-astra-xhigh/app/seaside_stroll.mp3) · [MIDI](models/gpt-6-astra-xhigh/app/seaside_stroll.mid) · [Source](models/gpt-6-astra-xhigh/app/compose_seaside.py) |
