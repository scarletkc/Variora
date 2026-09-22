export class Synth {
  constructor() {
    this.enabled = false;
    this.context = null;
  }

  async enable() {
    try {
      if (!this.context) this.setup();
      await this.context.resume();
      this.enabled = true;
      this.master.gain.setTargetAtTime(0.23, this.context.currentTime, 0.12);
      return true;
    } catch {
      return false;
    }
  }

  setup() {
    this.context = new AudioContext();
    const ctx = this.context;
    this.master = ctx.createGain();
    this.master.gain.value = 0;
    this.master.connect(ctx.destination);
    this.engine = ctx.createOscillator();
    this.engine.type = "sawtooth";
    this.engine.frequency.value = 42;
    this.engineFilter = ctx.createBiquadFilter();
    this.engineFilter.type = "lowpass";
    this.engineFilter.frequency.value = 180;
    this.engineGain = ctx.createGain();
    this.engineGain.gain.value = 0;
    this.engine
      .connect(this.engineFilter)
      .connect(this.engineGain)
      .connect(this.master);
    this.engine.start();
    const noise = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
    const samples = noise.getChannelData(0);
    for (let i = 0; i < samples.length; i++) samples[i] = Math.random() * 2 - 1;
    this.rain = ctx.createBufferSource();
    this.rain.buffer = noise;
    this.rain.loop = true;
    const filter = ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.value = 1600;
    const rainGain = ctx.createGain();
    rainGain.gain.value = 0.045;
    this.rain.connect(filter).connect(rainGain).connect(this.master);
    this.rain.start();
  }

  disable() {
    this.enabled = false;
    if (this.context)
      this.master.gain.setTargetAtTime(0, this.context.currentTime, 0.06);
  }

  update(speed, playing) {
    if (!this.context) return;
    const now = this.context.currentTime;
    this.engine.frequency.setTargetAtTime(38 + speed * 3.5, now, 0.15);
    this.engineFilter.frequency.setTargetAtTime(140 + speed * 24, now, 0.15);
    this.engineGain.gain.setTargetAtTime(playing ? 0.1 : 0, now, 0.1);
  }

  tone(frequency, delay, duration, type = "sine", volume = 0.28) {
    if (!this.context || !this.enabled) return;
    const start = this.context.currentTime + delay;
    const oscillator = this.context.createOscillator(),
      gain = this.context.createGain();
    oscillator.type = type;
    oscillator.frequency.setValueAtTime(frequency, start);
    gain.gain.setValueAtTime(0, start);
    gain.gain.linearRampToValueAtTime(volume, start + 0.012);
    gain.gain.exponentialRampToValueAtTime(0.001, start + duration);
    oscillator.connect(gain).connect(this.master);
    oscillator.start(start);
    oscillator.stop(start + duration + 0.05);
    oscillator.onended = () => {
      oscillator.disconnect();
      gain.disconnect();
    };
  }

  collect() {
    [440, 660, 880].forEach((note, i) =>
      this.tone(note, i * 0.065, 0.26, "sine"),
    );
  }
  start() {
    [164.81, 246.94, 329.63].forEach((note, i) =>
      this.tone(note, i * 0.1, 0.4, "triangle"),
    );
  }
  crash() {
    this.tone(54, 0, 0.75, "sawtooth", 0.3);
    this.tone(43, 0.12, 0.65, "triangle", 0.4);
  }
}
