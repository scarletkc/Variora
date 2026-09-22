// All audio is synthesized with the Web Audio API — no assets.
import { store } from "./store.js";

export class AudioEngine {
  constructor() {
    this.ctx = null;
    this.muted = store.get("neon-serpent-muted") === "1";
    this._pluckTimer = null;
  }

  /** Create the context on a user gesture. Safe to call repeatedly. */
  ensure() {
    if (this.ctx) {
      if (this.ctx.state === "suspended") this.ctx.resume();
      return;
    }
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    this.ctx = ctx;
    this.master = ctx.createGain();
    this.master.gain.value = this.muted ? 0 : 0.65;
    const comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -18;
    comp.ratio.value = 6;
    this.master.connect(comp);
    comp.connect(ctx.destination);

    // Shared delay for pluck echoes.
    this.echo = ctx.createDelay(1);
    this.echo.delayTime.value = 0.31;
    const fb = ctx.createGain();
    fb.gain.value = 0.34;
    this.echo.connect(fb).connect(this.echo);
    this.echo.connect(this.master);

    this._startAmbient();
    this._startEngine();
    this._schedulePlucks();
  }

  _startAmbient() {
    const ctx = this.ctx;
    const pad = ctx.createGain();
    pad.gain.value = 0.05;
    const lp = ctx.createBiquadFilter();
    lp.type = "lowpass";
    lp.frequency.value = 340;
    pad.connect(lp).connect(this.master);
    for (const [f, det] of [[55, 0], [55, 8], [110, -6], [164.8, 4]]) {
      const o = ctx.createOscillator();
      o.type = "sawtooth";
      o.frequency.value = f;
      o.detune.value = det;
      o.connect(pad);
      o.start();
    }
    const lfo = ctx.createOscillator();
    lfo.frequency.value = 0.07;
    const lg = ctx.createGain();
    lg.gain.value = 0.02;
    lfo.connect(lg).connect(pad.gain);
    lfo.start();
  }

  _startEngine() {
    const ctx = this.ctx;
    this.engineOsc = ctx.createOscillator();
    this.engineOsc.type = "triangle";
    this.engineOsc.frequency.value = 70;
    this.engineGain = ctx.createGain();
    this.engineGain.gain.value = 0;
    this.engineOsc.connect(this.engineGain).connect(this.master);
    this.engineOsc.start();

    // Wind: filtered noise whose gain follows speed.
    const len = ctx.sampleRate * 2;
    const buf = ctx.createBuffer(1, len, ctx.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
    this.noiseBuf = buf;
    const noise = ctx.createBufferSource();
    noise.buffer = buf;
    noise.loop = true;
    this.windFilter = ctx.createBiquadFilter();
    this.windFilter.type = "bandpass";
    this.windFilter.frequency.value = 600;
    this.windFilter.Q.value = 0.6;
    this.windGain = ctx.createGain();
    this.windGain.gain.value = 0;
    noise.connect(this.windFilter).connect(this.windGain).connect(this.master);
    noise.start();
  }

  _schedulePlucks() {
    const notes = [220, 261.6, 293.7, 329.6, 392, 440, 523.3];
    const tick = () => {
      if (this.ctx && !this.muted && Math.random() < 0.75) {
        const f = notes[(Math.random() * notes.length) | 0];
        this._tone(f, 0.5 + Math.random() * 0.5, 0.035, "sine", this.echo);
      }
      this._pluckTimer = setTimeout(tick, 1400 + Math.random() * 2600);
    };
    tick();
  }

  _tone(freq, dur, vol, type = "sine", dest = null, slideTo = null) {
    if (!this.ctx) return;
    const ctx = this.ctx;
    const o = ctx.createOscillator();
    o.type = type;
    o.frequency.value = freq;
    if (slideTo) o.frequency.exponentialRampToValueAtTime(slideTo, ctx.currentTime + dur);
    const g = ctx.createGain();
    g.gain.setValueAtTime(vol, ctx.currentTime);
    g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + dur);
    o.connect(g).connect(dest || this.master);
    o.start();
    o.stop(ctx.currentTime + dur + 0.05);
  }

  _noise(dur, vol, filterFreq, slideTo) {
    if (!this.ctx) return;
    const ctx = this.ctx;
    const s = ctx.createBufferSource();
    s.buffer = this.noiseBuf;
    const f = ctx.createBiquadFilter();
    f.type = "lowpass";
    f.frequency.setValueAtTime(filterFreq, ctx.currentTime);
    if (slideTo) f.frequency.exponentialRampToValueAtTime(slideTo, ctx.currentTime + dur);
    const g = ctx.createGain();
    g.gain.setValueAtTime(vol, ctx.currentTime);
    g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + dur);
    s.connect(f).connect(g).connect(this.master);
    s.start();
    s.stop(ctx.currentTime + dur + 0.05);
  }

  /** Per-frame: engine hum and wind follow speed. */
  update(speed, boost, playing) {
    if (!this.ctx) return;
    const t = this.ctx.currentTime;
    const target = playing ? 0.05 + speed * 0.002 : 0;
    this.engineGain.gain.setTargetAtTime(target, t, 0.12);
    this.engineOsc.frequency.setTargetAtTime(52 + speed * 2.4, t, 0.1);
    this.windGain.gain.setTargetAtTime(
      playing ? (speed / 40) * (boost ? 0.16 : 0.08) : 0, t, 0.2);
    this.windFilter.frequency.setTargetAtTime(400 + speed * 30, t, 0.2);
  }

  pickup(bonus) {
    if (!bonus) {
      this._tone(880, 0.16, 0.12);
      this._tone(1318, 0.22, 0.09);
    } else {
      this._tone(659, 0.14, 0.11);
      this._tone(988, 0.16, 0.11);
      this._tone(1318, 0.3, 0.12);
      this._tone(1976, 0.4, 0.06);
    }
  }

  count(final) {
    this._tone(final ? 1046 : 659, final ? 0.4 : 0.16, 0.12, "square");
  }

  crash() {
    this._noise(0.7, 0.5, 2400, 120);
    this._tone(120, 0.9, 0.4, "sine", null, 32);
    this._tone(66, 1.1, 0.3, "sawtooth", null, 28);
  }

  gameover() {
    this._tone(392, 0.3, 0.12, "triangle");
    setTimeout(() => this._tone(311, 0.3, 0.12, "triangle"), 220);
    setTimeout(() => this._tone(233, 0.7, 0.14, "triangle"), 440);
  }

  ui() {
    this._tone(1244, 0.07, 0.06, "square");
  }

  toggleMute() {
    this.muted = !this.muted;
    store.set("neon-serpent-muted", this.muted ? "1" : "0");
    if (this.master) {
      this.master.gain.setTargetAtTime(this.muted ? 0 : 0.65, this.ctx.currentTime, 0.05);
    }
    return this.muted;
  }
}
