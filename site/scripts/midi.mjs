const instruments = [
  "Acoustic Grand Piano",
  "Bright Acoustic Piano",
  "Electric Grand Piano",
  "Honky-tonk Piano",
  "Electric Piano 1",
  "Electric Piano 2",
  "Harpsichord",
  "Clavinet",
  "Celesta",
  "Glockenspiel",
  "Music Box",
  "Vibraphone",
  "Marimba",
  "Xylophone",
  "Tubular Bells",
  "Dulcimer",
  "Drawbar Organ",
  "Percussive Organ",
  "Rock Organ",
  "Church Organ",
  "Reed Organ",
  "Accordion",
  "Harmonica",
  "Tango Accordion",
  "Acoustic Guitar (nylon)",
  "Acoustic Guitar (steel)",
  "Electric Guitar (jazz)",
  "Electric Guitar (clean)",
  "Electric Guitar (muted)",
  "Overdriven Guitar",
  "Distortion Guitar",
  "Guitar Harmonics",
  "Acoustic Bass",
  "Electric Bass (finger)",
  "Electric Bass (pick)",
  "Fretless Bass",
  "Slap Bass 1",
  "Slap Bass 2",
  "Synth Bass 1",
  "Synth Bass 2",
  "Violin",
  "Viola",
  "Cello",
  "Contrabass",
  "Tremolo Strings",
  "Pizzicato Strings",
  "Orchestral Harp",
  "Timpani",
  "String Ensemble 1",
  "String Ensemble 2",
  "Synth Strings 1",
  "Synth Strings 2",
  "Choir Aahs",
  "Voice Oohs",
  "Synth Voice",
  "Orchestra Hit",
  "Trumpet",
  "Trombone",
  "Tuba",
  "Muted Trumpet",
  "French Horn",
  "Brass Section",
  "Synth Brass 1",
  "Synth Brass 2",
  "Soprano Sax",
  "Alto Sax",
  "Tenor Sax",
  "Baritone Sax",
  "Oboe",
  "English Horn",
  "Bassoon",
  "Clarinet",
  "Piccolo",
  "Flute",
  "Recorder",
  "Pan Flute",
  "Blown Bottle",
  "Shakuhachi",
  "Whistle",
  "Ocarina",
  "Lead 1 (square)",
  "Lead 2 (sawtooth)",
  "Lead 3 (calliope)",
  "Lead 4 (chiff)",
  "Lead 5 (charang)",
  "Lead 6 (voice)",
  "Lead 7 (fifths)",
  "Lead 8 (bass + lead)",
  "Pad 1 (new age)",
  "Pad 2 (warm)",
  "Pad 3 (polysynth)",
  "Pad 4 (choir)",
  "Pad 5 (bowed)",
  "Pad 6 (metallic)",
  "Pad 7 (halo)",
  "Pad 8 (sweep)",
  "FX 1 (rain)",
  "FX 2 (soundtrack)",
  "FX 3 (crystal)",
  "FX 4 (atmosphere)",
  "FX 5 (brightness)",
  "FX 6 (goblins)",
  "FX 7 (echoes)",
  "FX 8 (sci-fi)",
  "Sitar",
  "Banjo",
  "Shamisen",
  "Koto",
  "Kalimba",
  "Bagpipe",
  "Fiddle",
  "Shanai",
  "Tinkle Bell",
  "Agogo",
  "Steel Drums",
  "Woodblock",
  "Taiko Drum",
  "Melodic Tom",
  "Synth Drum",
  "Reverse Cymbal",
  "Guitar Fret Noise",
  "Breath Noise",
  "Seashore",
  "Bird Tweet",
  "Telephone Ring",
  "Helicopter",
  "Applause",
  "Gunshot",
];
const tonics = {
  major: "Cb Gb Db Ab Eb Bb F C G D A E B F# C#".split(" "),
  minor: "Ab Eb Bb F C G D A E B F# C# G# D# A#".split(" "),
};
const drums = 9;

export function readMidi(bytes) {
  const data = new Uint8Array(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const view = new DataView(data.buffer, data.byteOffset, data.byteLength);
  let offset = 0;
  function chunk() {
    if (offset + 8 > data.length) throw new Error("Truncated MIDI chunk");
    const id = String.fromCharCode(...data.subarray(offset, offset + 4));
    const start = offset + 8;
    const end = start + view.getUint32(offset + 4);
    if (end > data.length) throw new Error(`Truncated ${id} chunk`);
    offset = end;
    return { id, start, end };
  }
  if (String.fromCharCode(...data.subarray(0, 4)) !== "MThd")
    throw new Error("Not a Standard MIDI File");
  const header = chunk();
  if (header.end - header.start < 6) throw new Error("Truncated MThd chunk");
  const format = view.getUint16(header.start);
  const trackCount = view.getUint16(header.start + 2);
  const division = view.getUint16(header.start + 4);
  const tempos = [];
  const markers = [];
  const notes = [];
  const programs = new Map();
  let timeSignature = null;
  let key = null;
  let tracks = 0;
  let lastTick = 0;
  while (offset < data.length && tracks < trackCount) {
    const { id, start, end } = chunk();
    if (id !== "MTrk") continue;
    tracks++;
    let position = start;
    let tick = 0;
    let status = 0;
    const open = new Map();
    const byte = () => {
      if (position >= end) throw new Error("Truncated MIDI event");
      return data[position++];
    };
    const quantity = () => {
      let value = 0;
      for (let index = 0; index < 4; index++) {
        const next = byte();
        value = value * 128 + (next & 0x7f);
        if (!(next & 0x80)) return value;
      }
      throw new Error("Invalid MIDI variable-length quantity");
    };
    const close = (channel, pitch) => {
      const started = open.get(channel * 128 + pitch);
      if (!started?.length) return;
      notes.push({ start: started.shift(), end: tick, pitch, channel });
    };
    while (position < end) {
      tick += quantity();
      let type = data[position];
      if (type & 0x80) position++;
      else if (status) type = status;
      else throw new Error("MIDI running status without a status byte");
      if (type === 0xff) {
        const meta = byte();
        const length = quantity();
        if (position + length > end) throw new Error("Truncated MIDI event");
        const payload = data.subarray(position, (position += length));
        if (meta === 0x51 && length === 3)
          tempos.push({
            tick,
            micros: (payload[0] << 16) | (payload[1] << 8) | payload[2],
          });
        else if (meta === 0x58 && length >= 2 && !timeSignature)
          timeSignature = `${payload[0]}/${2 ** payload[1]}`;
        else if (meta === 0x59 && length === 2 && !key) {
          const sharps = (payload[0] << 24) >> 24;
          const mode = payload[1] ? "minor" : "major";
          const tonic = tonics[mode][sharps + 7];
          if (tonic) key = { tonic, mode };
        } else if (meta === 0x06) {
          const text = new TextDecoder().decode(payload).trim();
          if (text) markers.push({ tick, text: text.slice(0, 80) });
        } else if (meta === 0x2f) break;
        status = 0;
      } else if (type === 0xf0 || type === 0xf7) {
        position += quantity();
        status = 0;
      } else if (type >= 0xf0) {
        throw new Error("Unexpected MIDI system message");
      } else {
        status = type;
        const kind = type & 0xf0;
        const channel = type & 0x0f;
        const first = byte();
        const second = kind === 0xc0 || kind === 0xd0 ? 0 : byte();
        if (kind === 0x90 && second > 0) {
          const index = channel * 128 + first;
          open.set(index, [...(open.get(index) ?? []), tick]);
        } else if (kind === 0x80 || kind === 0x90) close(channel, first);
        else if (kind === 0xc0) {
          if (!programs.has(channel)) programs.set(channel, new Set());
          programs.get(channel).add(first);
        }
      }
    }
    for (const [index, starts] of open)
      for (const started of starts)
        notes.push({
          start: started,
          end: tick,
          pitch: index % 128,
          channel: Math.floor(index / 128),
        });
    lastTick = Math.max(lastTick, tick);
  }
  if (!tracks) throw new Error("MIDI file has no tracks");

  const smpte = division & 0x8000;
  const ticksPerQuarter = smpte ? null : division;
  const map = tempos
    .sort((a, b) => a.tick - b.tick)
    .reduce(
      (segments, { tick, micros }) => {
        const previous = segments.at(-1);
        const seconds =
          previous.seconds +
          ((tick - previous.tick) * previous.micros) / 1e6 / ticksPerQuarter;
        if (tick === previous.tick) segments.pop();
        segments.push({ tick, micros, seconds });
        return segments;
      },
      [{ tick: 0, micros: 500000, seconds: 0 }],
    );
  const seconds = (tick) => {
    if (smpte)
      return tick / (-(((division >> 8) << 24) >> 24) * (division & 0xff));
    const segment = map.findLast((item) => item.tick <= tick);
    return (
      segment.seconds +
      ((tick - segment.tick) * segment.micros) / 1e6 / ticksPerQuarter
    );
  };
  const end = notes.length
    ? notes.reduce((last, note) => Math.max(last, note.end), 0)
    : lastTick;
  const used = [...new Set(notes.map((note) => note.channel))].sort(
    (a, b) => a - b,
  );
  const names = used.flatMap((channel) =>
    channel === drums
      ? ["Percussion"]
      : [...(programs.get(channel) ?? [0])].map(
          (program) => instruments[program],
        ),
  );
  const bpm = smpte
    ? []
    : (tempos.length ? tempos : [{ micros: 500000 }]).map(
        ({ micros }) => Math.round((6e7 / micros) * 10) / 10,
      );
  return {
    summary: {
      format,
      tracks,
      ticksPerQuarter,
      duration: Math.round(seconds(end) * 100) / 100,
      tempo: bpm.length
        ? { min: Math.min(...bpm), max: Math.max(...bpm) }
        : null,
      timeSignature,
      key,
      notes: notes.length,
      instruments: [...new Set(names)],
      markers: markers
        .sort((a, b) => a.tick - b.tick)
        .slice(0, 32)
        .map(({ tick, text }) => ({
          time: Math.round(seconds(tick) * 100) / 100,
          text,
        })),
    },
    notes: notes.map((note) => ({
      start: seconds(note.start),
      end: seconds(note.end),
      pitch: note.pitch,
      channel: note.channel,
    })),
  };
}

export function pianoRoll(notes, duration) {
  const pitched = notes.filter((note) => note.channel !== drums);
  if (!pitched.length || !(duration > 0)) return null;
  const high = pitched.reduce((top, note) => Math.max(top, note.pitch), 0) + 1;
  const low = pitched.reduce(
    (bottom, note) => Math.min(bottom, note.pitch),
    127,
  );
  const rows = high - low + 2;
  const scale = 1000 / duration;
  const round = (value) => Math.round(value * 10) / 10;
  const path = pitched
    .map((note) => {
      const width = round(Math.max((note.end - note.start) * scale, 1.5));
      return `M${round(note.start * scale)} ${high - note.pitch + 0.1}h${width}v0.8h-${width}z`;
    })
    .join("");
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 ${rows}" preserveAspectRatio="none"><path d="${path}"/></svg>\n`;
}
