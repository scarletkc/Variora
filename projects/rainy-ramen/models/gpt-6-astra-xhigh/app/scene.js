"use strict";

(() => {
  const svgNS = "http://www.w3.org/2000/svg";
  const body = document.body;
  const rainInput = document.querySelector("#rain");
  const rainLabel = document.querySelector("#rain-label");
  const soundButton = document.querySelector("#sound");
  const soundLabel = document.querySelector("#sound-label");
  const pauseButton = document.querySelector("#pause");
  const pauseLabel = document.querySelector("#pause-label");
  const pauseIcon = document.querySelector("#pause-icon");
  const audioStatus = document.querySelector("#audio-status");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const rainNames = ["Drizzle", "Steady", "Downpour"];
  let paused = reducedMotion.matches;
  let audio = null;
  let soundEnabled = false;

  // A fixed seed keeps the hand-built scene's incidental details reproducible.
  let seed = 2308;
  const random = () => {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    return seed / 4294967296;
  };
  const addSVG = (parent, tag, attributes) => {
    const element = document.createElementNS(svgNS, tag);
    for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, String(value));
    parent.append(element);
    return element;
  };

  const windows = document.querySelector("#city-windows");
  for (const building of [{ x: 20, y: 77, cols: 3, rows: 12 }, { x: 832, y: 35, cols: 4, rows: 14 }, { x: 1025, y: 71, cols: 3, rows: 11 }, { x: 1228, y: 37, cols: 5, rows: 10 }]) {
    for (let row = 0; row < building.rows; row++) {
      for (let col = 0; col < building.cols; col++) {
        const lit = random() > .65;
        addSVG(windows, "rect", { x: building.x + col * 33, y: building.y + row * 37, width: 14, height: 21, rx: 1, fill: lit ? (random() > .4 ? "#95aaa0" : "#c6a77a") : "#29434d", opacity: lit ? .16 + random() * .2 : .45 });
      }
    }
  }

  const reflections = document.querySelector("#reflections");
  for (let i = 0; i < 112; i++) {
    const y = 657 + random() * 213;
    const warm = random() > .26;
    addSVG(reflections, "rect", { x: warm ? 160 + random() * 710 : 1080 + random() * 230, y, width: 4 + random() * 86, height: .7 + random() * 3, rx: 1, fill: warm ? "#daa078" : "#80c2b6", opacity: (.06 + random() * .22) * (1 - (y - 657) / 320) });
  }

  const umbrellaDrops = document.querySelector("#umbrella-drops");
  for (let i = 0; i < 65; i++) {
    const x = 820 + random() * 470;
    const y = 210 + random() * 169;
    addSVG(umbrellaDrops, "path", { d: `M${x.toFixed(1)} ${y.toFixed(1)}l-1.4 5`, stroke: "#d2e2d2", "stroke-width": .6 + random() * 1.1, "stroke-linecap": "round", opacity: .15 + random() * .42 });
  }

  for (const [layerId, count, foreground] of [["rain-back", 135, false], ["rain-front", 95, true]]) {
    const layer = document.getElementById(layerId);
    for (let i = 0; i < count; i++) {
      const x = random() * 1550 - 50;
      const y = random() * 1080 - 100;
      const length = foreground ? 14 + random() * 18 : 8 + random() * 12;
      const tier = i % 3;
      addSVG(layer, "path", {
        d: `M${x.toFixed(1)} ${y.toFixed(1)}l${(-length * .2).toFixed(1)} ${length.toFixed(1)}`,
        stroke: foreground ? "#b1d1cd" : "#7fa7b0",
        "stroke-width": foreground ? 1.15 : .8,
        "stroke-linecap": "round", opacity: .16 + random() * .36,
        class: `rain-drop${tier > 0 ? " rain-extra" : ""}${tier === 2 ? " rain-storm" : ""}`,
        style: `--duration:${(.75 + random() * .65).toFixed(2)}s;--delay:-${(random() * 3).toFixed(2)}s`,
      });
    }
  }

  function updateRain() {
    const level = Number(rainInput.value);
    body.dataset.rain = String(level);
    rainLabel.textContent = rainNames[level];
    rainInput.setAttribute("aria-valuetext", rainNames[level]);
    if (audio) {
      audio.texture.gain.setTargetAtTime([.19, .3, .43][level], audio.context.currentTime, .35);
      audio.filter.frequency.setTargetAtTime([2100, 3200, 4600][level], audio.context.currentTime, .35);
    }
  }

  function updatePause() {
    body.classList.toggle("is-paused", paused);
    pauseButton.setAttribute("aria-pressed", String(paused));
    pauseButton.disabled = reducedMotion.matches;
    pauseButton.setAttribute("aria-label", reducedMotion.matches ? "Animation off: reduced motion enabled" : paused ? "Resume animation" : "Pause animation");
    pauseLabel.textContent = reducedMotion.matches ? "Motion off" : paused ? "Resume" : "Pause";
    pauseIcon.setAttribute("d", paused ? "m6 4 9 6-9 6Z" : "M7 5v10M13 5v10");
  }

  // The whole soundscape is synthesized locally and starts only after a gesture.
  async function createAudio() {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) throw new Error("Web Audio is unavailable");
    const context = new AudioContext();
    try {
      await context.resume();
      const master = context.createGain();
      master.gain.value = 0;
      master.connect(context.destination);

      const texture = context.createGain();
      texture.gain.value = [.19, .3, .43][Number(rainInput.value)];
      texture.connect(master);
      const filter = context.createBiquadFilter();
      filter.type = "lowpass";
      filter.frequency.value = [2100, 3200, 4600][Number(rainInput.value)];
      filter.Q.value = .45;
      filter.connect(texture);

      const rainBuffer = context.createBuffer(2, context.sampleRate * 6, context.sampleRate);
      for (let channel = 0; channel < 2; channel++) {
        const samples = rainBuffer.getChannelData(channel);
        let brown = 0;
        for (let i = 0; i < samples.length; i++) {
          const white = Math.random() * 2 - 1;
          brown = (brown + .025 * white) / 1.025;
          samples[i] = white * .34 + brown * 2.4;
        }
      }
      const rain = context.createBufferSource();
      rain.buffer = rainBuffer;
      rain.loop = true;
      rain.connect(filter);
      rain.start();

      // A very quiet sine tone gives the rain a warm, distant electrical hum.
      const hum = context.createOscillator();
      const humGain = context.createGain();
      hum.type = "sine";
      hum.frequency.value = 110;
      humGain.gain.value = .007;
      hum.connect(humGain).connect(master);
      hum.start();
      return { context, master, texture, filter };
    } catch (error) {
      await context.close();
      throw error;
    }
  }

  async function syncAudio() {
    if (!audio) return;
    if (soundEnabled && !document.hidden) {
      await audio.context.resume();
      audio.master.gain.setTargetAtTime(.68, audio.context.currentTime, .2);
    } else {
      audio.master.gain.setTargetAtTime(0, audio.context.currentTime, .07);
      await audio.context.suspend();
    }
  }

  function audioFailed() {
    soundEnabled = false;
    soundButton.setAttribute("aria-pressed", "false");
    soundLabel.textContent = "Sound off";
    audioStatus.textContent = "Sound could not start. Try the sound button again in a browser with Web Audio support.";
  }

  soundButton.addEventListener("click", async () => {
    soundButton.disabled = true;
    audioStatus.textContent = "";
    try {
      if (!audio) audio = await createAudio();
      soundEnabled = !soundEnabled;
      await syncAudio();
      soundButton.setAttribute("aria-pressed", String(soundEnabled));
      soundLabel.textContent = soundEnabled ? "Sound on" : "Sound off";
    } catch {
      audioFailed();
    } finally {
      soundButton.disabled = false;
    }
  });
  rainInput.addEventListener("input", updateRain);
  pauseButton.addEventListener("click", () => {
    paused = !paused;
    updatePause();
  });
  reducedMotion.addEventListener("change", () => {
    paused = reducedMotion.matches;
    updatePause();
  });
  document.addEventListener("visibilitychange", () => {
    body.classList.toggle("is-hidden", document.hidden);
    syncAudio().catch(audioFailed);
  });
  window.addEventListener("pagehide", () => {
    if (audio) audio.context.suspend().catch(() => {});
  });
  window.addEventListener("pageshow", () => syncAudio().catch(audioFailed));
  updateRain();
  updatePause();
})();
