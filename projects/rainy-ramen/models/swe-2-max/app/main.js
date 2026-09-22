"use strict";

const SVG_NS = "http://www.w3.org/2000/svg";
const reducedMotion =
  window.matchMedia("(prefers-reduced-motion: reduce)").matches &&
  !new URLSearchParams(location.search).has("animate");

if (reducedMotion) {
  const style = document.createElement("style");
  style.textContent = "* { animation: none !important; }";
  document.head.appendChild(style);
}

const rand = (min, max) => min + Math.random() * (max - min);

/* ---------- distant city windows ---------- */
(function cityWindows() {
  const layer = document.getElementById("city-windows");
  const palette = ["#ffd98a", "#9fd8ff", "#ff9ad5"];
  const blocks = [
    { x: 12, y: 316, w: 160, h: 220 },
    { x: 962, y: 280, w: 106, h: 270 },
    { x: 1090, y: 220, w: 100, h: 330 },
  ];
  for (const b of blocks) {
    for (let y = b.y; y < b.y + b.h; y += 26) {
      for (let x = b.x; x < b.x + b.w; x += 24) {
        if (Math.random() < 0.55) continue;
        const r = document.createElementNS(SVG_NS, "rect");
        r.setAttribute("x", x.toFixed(0));
        r.setAttribute("y", y.toFixed(0));
        r.setAttribute("width", "7");
        r.setAttribute("height", "10");
        r.setAttribute("fill", palette[(Math.random() * palette.length) | 0]);
        r.setAttribute("opacity", rand(0.15, 0.6).toFixed(2));
        layer.appendChild(r);
      }
    }
  }
})();

/* ---------- procedural rain ---------- */
function makeRain(layerId, count, { len, width, opacity, dur, slant, color }) {
  const layer = document.getElementById(layerId);
  for (let i = 0; i < count; i++) {
    const l = rand(len[0], len[1]);
    const x = rand(-40, 1240);
    const drop = document.createElementNS(SVG_NS, "line");
    drop.setAttribute("x1", x.toFixed(1));
    drop.setAttribute("y1", "0");
    drop.setAttribute("x2", (x - l * slant).toFixed(1));
    drop.setAttribute("y2", l.toFixed(1));
    drop.setAttribute("stroke", color);
    drop.setAttribute("stroke-width", rand(width[0], width[1]).toFixed(2));
    drop.setAttribute("opacity", rand(opacity[0], opacity[1]).toFixed(2));
    drop.classList.add("drop");
    const d = rand(dur[0], dur[1]);
    drop.style.animationDuration = d.toFixed(2) + "s";
    drop.style.animationDelay = (-rand(0, d)).toFixed(2) + "s";
    layer.appendChild(drop);
  }
}

if (!reducedMotion) {
  makeRain("rain-back", 90, {
    len: [10, 18], width: [0.8, 1.4], opacity: [0.14, 0.32],
    dur: [1.1, 1.7], slant: 0.22, color: "#9db8e8",
  });
  makeRain("rain-front", 70, {
    len: [18, 34], width: [1.4, 2.1], opacity: [0.25, 0.5],
    dur: [0.65, 1.05], slant: 0.22, color: "#b9d2ff",
  });
}

/* ---------- ground splashes ---------- */
(function splashes() {
  if (reducedMotion) return;
  const layer = document.getElementById("splashes");
  for (let i = 0; i < 26; i++) {
    const e = document.createElementNS(SVG_NS, "ellipse");
    e.setAttribute("cx", rand(20, 1180).toFixed(0));
    e.setAttribute("cy", rand(562, 606).toFixed(0));
    e.setAttribute("rx", rand(5, 11).toFixed(1));
    e.setAttribute("ry", rand(1.6, 3).toFixed(1));
    e.setAttribute("stroke-width", rand(0.8, 1.6).toFixed(1));
    e.classList.add("splash");
    const d = rand(0.55, 1.05);
    e.style.animationDuration = d.toFixed(2) + "s";
    e.style.animationDelay = (-rand(0, d)).toFixed(2) + "s";
    layer.appendChild(e);
  }
})();

/* ---------- subtle parallax on background layers ---------- */
if (!reducedMotion) {
  const far = document.getElementById("px-far");
  const mid = document.getElementById("px-mid");
  const front = document.getElementById("rain-front");
  window.addEventListener("pointermove", (ev) => {
    const dx = ev.clientX / window.innerWidth - 0.5;
    const dy = ev.clientY / window.innerHeight - 0.5;
    far.style.transform = `translate(${dx * -6}px, ${dy * -3}px)`;
    mid.style.transform = `translate(${dx * -11}px, ${dy * -5}px)`;
    front.style.transform = `translate(${dx * -20}px, ${dy * -8}px)`;
  });
  window.addEventListener("pointerleave", () => {
    far.style.transform = mid.style.transform = front.style.transform = "";
  });
}

/* ---------- generative rain audio (WebAudio, no assets) ---------- */
const btn = document.getElementById("soundToggle");
let audio = null;
let rainOn = false;

function buildAudio() {
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  const master = ctx.createGain();
  master.gain.value = 0;
  master.connect(ctx.destination);

  // looping brown-ish noise built from a random buffer
  const len = ctx.sampleRate * 2;
  const buf = ctx.createBuffer(1, len, ctx.sampleRate);
  const data = buf.getChannelData(0);
  let last = 0;
  for (let i = 0; i < len; i++) {
    const white = Math.random() * 2 - 1;
    last = (last + 0.02 * white) / 1.02;
    data[i] = last * 3.2;
  }
  const src = ctx.createBufferSource();
  src.buffer = buf;
  src.loop = true;

  const low = ctx.createBiquadFilter();
  low.type = "lowpass";
  low.frequency.value = 1200;
  low.Q.value = 0.4;
  const rainGain = ctx.createGain();
  rainGain.gain.value = 0.5;
  src.connect(low).connect(rainGain).connect(master);
  src.start();

  // high patter hiss
  const src2 = ctx.createBufferSource();
  const buf2 = ctx.createBuffer(1, len, ctx.sampleRate);
  const d2 = buf2.getChannelData(0);
  for (let i = 0; i < len; i++) d2[i] = Math.random() * 2 - 1;
  src2.buffer = buf2;
  src2.loop = true;
  const band = ctx.createBiquadFilter();
  band.type = "bandpass";
  band.frequency.value = 4200;
  band.Q.value = 0.6;
  const hissGain = ctx.createGain();
  hissGain.gain.value = 0.05;
  src2.connect(band).connect(hissGain).connect(master);
  src2.start();

  // occasional synthesized droplet "plink" into a puddle
  const plinkTimer = setInterval(() => {
    if (Math.random() < 0.55) return;
    const t = ctx.currentTime;
    const osc = ctx.createOscillator();
    const g = ctx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(rand(1400, 2400), t);
    osc.frequency.exponentialRampToValueAtTime(rand(500, 800), t + 0.09);
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(0.05, t + 0.008);
    g.gain.exponentialRampToValueAtTime(0.0004, t + 0.16);
    osc.connect(g).connect(master);
    osc.start(t);
    osc.stop(t + 0.2);
  }, 1400);

  return { ctx, master, plinkTimer };
}

btn.addEventListener("click", () => {
  if (!audio) audio = buildAudio();
  const { ctx, master } = audio;
  if (ctx.state === "suspended") ctx.resume();
  rainOn = !rainOn;
  const t = ctx.currentTime;
  master.gain.cancelScheduledValues(t);
  master.gain.setValueAtTime(master.gain.value, t);
  master.gain.linearRampToValueAtTime(rainOn ? 0.12 : 0, t + 0.8);
  btn.textContent = "rain sound: " + (rainOn ? "on" : "off");
  btn.setAttribute("aria-pressed", String(rainOn));
});
