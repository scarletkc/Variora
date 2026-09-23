import { test } from "node:test";
import assert from "node:assert/strict";
import { pianoRoll, readMidi } from "../scripts/midi.mjs";
import { smf } from "./fixtures.mjs";

const song = smf([
  [
    [0, 0xff, 0x51, 3, 0x07, 0xa1, 0x20],
    [0, 0xff, 0x58, 4, 3, 2, 24, 8],
    [0, 0xff, 0x59, 2, 2, 0],
    [0, 0xff, 0x06, 5, ...Buffer.from("Intro")],
    [960, 0xff, 0x51, 3, 0x0f, 0x42, 0x40],
    [0, 0xff, 0x06, 6, ...Buffer.from("Chorus")],
  ],
  [
    [0, 0xc0, 73],
    [0, 0x90, 60, 100],
    [0, 64, 100],
    [480, 60, 0],
    [480, 0x80, 64, 0],
    [480, 0x90, 67, 90],
    [480, 0x80, 67, 0],
  ],
  [
    [0, 0x99, 36, 100],
    [240, 0x89, 36, 0],
  ],
]);

test("summarizes tempo changes, running status, and General MIDI programs", () => {
  const { summary, notes } = readMidi(song);
  assert.deepEqual(summary, {
    format: 1,
    tracks: 3,
    ticksPerQuarter: 480,
    duration: 3,
    tempo: { min: 60, max: 120 },
    timeSignature: "3/4",
    key: { tonic: "D", mode: "major" },
    notes: 4,
    instruments: ["Flute", "Percussion"],
    markers: [
      { time: 0, text: "Intro" },
      { time: 1, text: "Chorus" },
    ],
  });
  assert.deepEqual(
    notes.find((note) => note.pitch === 67),
    { start: 2, end: 3, pitch: 67, channel: 0 },
  );
  assert.deepEqual(
    notes.find((note) => note.pitch === 60),
    { start: 0, end: 0.5, pitch: 60, channel: 0 },
  );
});

test("draws only pitched notes in the piano roll", () => {
  const { summary, notes } = readMidi(song);
  const svg = pianoRoll(notes, summary.duration);
  assert.match(svg, /^<svg [^>]*viewBox="0 0 1000 10"/);
  assert.equal(svg.match(/M/g).length, 3);
  assert.equal(
    pianoRoll(
      notes.filter((note) => note.channel === 9),
      1,
    ),
    null,
  );
});

test("rejects files that are not complete Standard MIDI Files", () => {
  assert.throws(() => readMidi(Buffer.from("RIFF0000WAVE")), /Standard MIDI/);
  assert.throws(() => readMidi(song.subarray(0, song.length - 3)), /Truncated/);
  assert.throws(
    () => readMidi(smf([[[0, 0x40, 100]]])),
    /running status without a status byte/,
  );
});
