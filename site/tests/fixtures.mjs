function quantity(value) {
  const bytes = [value & 0x7f];
  while ((value >>= 7)) bytes.unshift((value & 0x7f) | 0x80);
  return bytes;
}

function chunk(id, data) {
  const head = Buffer.alloc(8);
  head.write(id, 0, "ascii");
  head.writeUInt32BE(data.length, 4);
  return Buffer.concat([head, Buffer.from(data)]);
}

export function smf(tracks, division = 480) {
  return Buffer.concat([
    chunk("MThd", [0, 1, 0, tracks.length, division >> 8, division & 0xff]),
    ...tracks.map((events) =>
      chunk(
        "MTrk",
        [...events, [0, 0xff, 0x2f, 0]].flatMap(([delta, ...bytes]) => [
          ...quantity(delta),
          ...bytes,
        ]),
      ),
    ),
  ]);
}

export function melody(pitches, program = 0) {
  return smf([
    [[0, 0xff, 0x51, 3, 0x07, 0xa1, 0x20]],
    [
      [0, 0xc0, program],
      ...pitches.flatMap((pitch) => [
        [0, 0x90, pitch, 90],
        [480, 0x80, pitch, 0],
      ]),
    ],
  ]);
}

export function wav(seconds, frequency, rate = 8000) {
  const samples = Math.round(seconds * rate);
  const data = Buffer.alloc(44 + samples * 2);
  data.write("RIFF", 0, "ascii");
  data.writeUInt32LE(36 + samples * 2, 4);
  data.write("WAVEfmt ", 8, "ascii");
  data.writeUInt32LE(16, 16);
  data.writeUInt16LE(1, 20);
  data.writeUInt16LE(1, 22);
  data.writeUInt32LE(rate, 24);
  data.writeUInt32LE(rate * 2, 28);
  data.writeUInt16LE(2, 32);
  data.writeUInt16LE(16, 34);
  data.write("data", 36, "ascii");
  data.writeUInt32LE(samples * 2, 40);
  for (let index = 0; index < samples; index++)
    data.writeInt16LE(
      Math.round(Math.sin((2 * Math.PI * frequency * index) / rate) * 6000),
      44 + index * 2,
    );
  return data;
}
