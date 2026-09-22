import { Simulation, BLOCKS, WORLD_LIMIT } from "./simulation.mjs";
import { Synth } from "./audio.js";

const $ = (id) => document.getElementById(id);
const sim = new Simulation();
const synth = new Synth();
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const keys = new Set(),
  touch = new Set();
let view,
  state = "loading",
  best = 0,
  last = 0,
  accumulator = 0,
  toastTimer,
  frame = 0;
try {
  best = Number(localStorage.getItem("neon-serpent-best")) || 0;
} catch {
  /* Sandboxed previews can disable storage. */
}
const map = $("map").getContext("2d");
const pad = (value, length) => String(value).padStart(length, "0");

function setState(next) {
  state = next;
  document.body.dataset.state = next;
  $("intro").hidden = next !== "intro";
  $("district").hidden = next !== "intro";
  $("run-hud").hidden = !["playing", "paused", "over"].includes(next);
  $("modal").hidden = !["paused", "over"].includes(next);
  $("pause").hidden = next !== "playing";
  $("touch-controls").hidden = next !== "playing";
  $("link-status").textContent =
    {
      intro: "NEURAL LINK READY",
      playing: "NEURAL LINK ACTIVE",
      paused: "LINK SUSPENDED",
      over: "SIGNAL LOST",
      error: "CONNECTION FAILED",
    }[next] || "SYSTEM INITIALIZING";
  keys.clear();
  touch.clear();
  document
    .querySelectorAll("[data-control]")
    .forEach((button) => button.classList.remove("active"));
  accumulator = 0;
}

function start() {
  if (!view || state === "error") return;
  sim.reset();
  setState("playing");
  synth.start();
  $("route-tip").style.opacity = "1";
  $("route-tip").textContent = "FOLLOW THE AMBER LIGHT";
  $("start").blur();
  $("resume").blur();
  $("restart").blur();
  updateHud();
}

function pause() {
  if (state !== "playing") return;
  setState("paused");
  updateHud();
  $("modal-kicker").textContent = "NEURAL LINK SUSPENDED";
  $("modal-title").textContent = "STAY SHARP.";
  $("modal-copy").textContent = "The city will wait. Resume when you’re ready.";
  $("result-stats").hidden = true;
  $("resume").hidden = false;
  $("resume").querySelector("span").textContent = "RESUME RUN";
  $("restart").textContent = "NEW RUN";
  $("resume").focus();
}

function resume() {
  if (state === "paused") {
    setState("playing");
    $("resume").blur();
  }
}

function gameOver(reason) {
  best = Math.max(best, sim.score);
  try {
    localStorage.setItem("neon-serpent-best", String(best));
  } catch {
    /* A run remains playable without persistence. */
  }
  setState("over");
  synth.crash();
  $("modal-kicker").textContent = reason;
  $("modal-title").textContent = "SIGNAL LOST.";
  $("modal-copy").textContent =
    reason === "TAIL COLLISION"
      ? "Your past caught up with you. Give your tail more room."
      : "The streets have edges. Watch your route on the minimap.";
  $("result-stats").hidden = false;
  $("final-score").textContent = sim.score.toLocaleString();
  $("final-distance").textContent = `${Math.floor(sim.distance)} M`;
  $("best").textContent = best.toLocaleString();
  $("resume").hidden = true;
  $("restart").textContent = "↗  TRY AGAIN / ENTER";
  $("restart").focus();
  updateHud();
}

function toast(message) {
  clearTimeout(toastTimer);
  $("toast").textContent = message;
  $("toast").classList.add("visible");
  toastTimer = setTimeout(() => $("toast").classList.remove("visible"), 1400);
}

function updateHud() {
  $("score").textContent = pad(sim.score, 6);
  $("core-count").textContent = pad(sim.collected, 2);
  $("length").textContent = sim.segmentCount;
  $("speed").textContent = pad(Math.round(sim.speed * 3.6), 2);
  $("charge").style.transform = `scaleX(${sim.charge / 100})`;
  const target = sim.nearestCore();
  if (target) {
    $("target-distance").textContent = `${Math.round(target.distance)} M`;
    $("target-arrow").style.transform = `rotate(${target.bearing}rad)`;
  }
  if (sim.elapsed > 7) $("route-tip").style.opacity = "0";
  drawMap();
}

function drawMap() {
  const size = 240,
    scale = size / (WORLD_LIMIT * 2 + 8);
  const coordinate = (value) => size / 2 + value * scale;
  map.clearRect(0, 0, size, size);
  map.strokeStyle = "#a5d5ba30";
  map.lineWidth = 1;
  map.strokeRect(
    coordinate(-WORLD_LIMIT),
    coordinate(-WORLD_LIMIT),
    WORLD_LIMIT * 2 * scale,
    WORLD_LIMIT * 2 * scale,
  );
  map.fillStyle = "#66989b42";
  for (const block of BLOCKS)
    map.fillRect(
      coordinate(block.x - block.half),
      coordinate(block.z - block.half),
      block.half * 2 * scale,
      block.half * 2 * scale,
    );
  const body = sim.bodyPoints();
  map.strokeStyle = "#82e4ce";
  map.lineWidth = 2;
  map.beginPath();
  map.moveTo(coordinate(sim.x), coordinate(sim.z));
  body.forEach((point) => map.lineTo(coordinate(point.x), coordinate(point.z)));
  map.stroke();
  map.fillStyle = "#ffcd82";
  for (const core of sim.cores) {
    map.beginPath();
    map.arc(coordinate(core.x), coordinate(core.z), 2.7, 0, Math.PI * 2);
    map.fill();
  }
  map.save();
  map.translate(coordinate(sim.x), coordinate(sim.z));
  map.rotate(sim.heading);
  map.fillStyle = "#ff8856";
  map.strokeStyle = "#13292b";
  map.lineWidth = 1.5;
  map.beginPath();
  map.moveTo(0, -6);
  map.lineTo(4.5, 4.5);
  map.lineTo(0, 2.5);
  map.lineTo(-4.5, 4.5);
  map.closePath();
  map.fill();
  map.stroke();
  map.restore();
}

async function toggleSound() {
  if (synth.enabled) synth.disable();
  else if (!(await synth.enable())) {
    toast("AUDIO UNAVAILABLE IN THIS BROWSER");
    return;
  }
  $("sound").setAttribute("aria-pressed", String(synth.enabled));
  $("sound").setAttribute(
    "aria-label",
    synth.enabled ? "Turn sound off" : "Turn sound on",
  );
  $("sound-label").textContent = synth.enabled ? "SOUND ON" : "SOUND OFF";
}

$("start").addEventListener("click", start);
$("pause").addEventListener("click", pause);
$("resume").addEventListener("click", resume);
$("restart").addEventListener("click", start);
$("sound").addEventListener("click", toggleSound);

window.addEventListener("keydown", (event) => {
  if (event.code === "Tab" && (state === "paused" || state === "over")) {
    const buttons = [...$("modal").querySelectorAll("button")].filter(
      (button) => !button.hidden,
    );
    const index = buttons.indexOf(document.activeElement);
    const next = event.shiftKey
      ? index <= 0
        ? buttons.length - 1
        : index - 1
      : (index + 1) % buttons.length;
    event.preventDefault();
    buttons[next].focus();
    return;
  }
  if (
    event.code === "Enter" &&
    !event.repeat &&
    !document.activeElement?.matches("button,a")
  ) {
    if (state === "intro" || state === "over") start();
    else if (state === "paused") resume();
  }
  if (
    [
      "ArrowLeft",
      "ArrowRight",
      "ArrowUp",
      "Space",
      "ShiftLeft",
      "ShiftRight",
      "KeyW",
      "KeyA",
      "KeyD",
    ].includes(event.code) &&
    state === "playing"
  ) {
    event.preventDefault();
    keys.add(event.code);
  }
  if (event.repeat) return;
  if (["Escape", "KeyP"].includes(event.code)) {
    event.preventDefault();
    if (state === "playing") pause();
    else if (state === "paused") resume();
  }
  if (event.code === "KeyM") toggleSound();
  if (event.code === "KeyR" && state === "over") start();
});
window.addEventListener("keyup", (event) => keys.delete(event.code));
window.addEventListener("blur", pause);
document.addEventListener("visibilitychange", () => {
  if (document.hidden) pause();
});

for (const button of document.querySelectorAll("[data-control]")) {
  const control = button.dataset.control;
  button.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    button.setPointerCapture(event.pointerId);
    touch.add(control);
    button.classList.add("active");
  });
  const release = () => {
    touch.delete(control);
    button.classList.remove("active");
  };
  button.addEventListener("pointerup", release);
  button.addEventListener("pointercancel", release);
  button.addEventListener("lostpointercapture", release);
  button.addEventListener("contextmenu", (event) => event.preventDefault());
}

function fail(error) {
  console.error(error);
  setState("error");
  $("intro").hidden = false;
  $("start-label").textContent = "RELOAD CITY";
  $("start").disabled = false;
  $("start").removeEventListener("click", start);
  $("start").addEventListener("click", () => location.reload(), { once: true });
  $("start-hint").textContent =
    "Could not start the 3D renderer. Enable hardware acceleration and use a browser with WebGL 2, then reload.";
  $("intro").querySelector(".brief").textContent =
    "The neural link could not be established.";
}

function animate(timestamp) {
  if (state === "error") return;
  const dt = Math.min((timestamp - (last || timestamp)) / 1000, 0.1);
  last = timestamp;
  const steer =
    (keys.has("KeyD") || keys.has("ArrowRight") || touch.has("right") ? 1 : 0) -
    (keys.has("KeyA") || keys.has("ArrowLeft") || touch.has("left") ? 1 : 0);
  const boost =
    keys.has("ShiftLeft") ||
    keys.has("ShiftRight") ||
    keys.has("KeyW") ||
    keys.has("ArrowUp") ||
    keys.has("Space") ||
    touch.has("boost");
  if (state === "playing") {
    accumulator += dt;
    while (accumulator >= 1 / 120 && state === "playing") {
      accumulator -= 1 / 120;
      for (const event of sim.step(1 / 120, steer, boost)) {
        if (event.type === "crash") gameOver(event.reason);
        if (event.type === "collect") {
          view.collect(event.x, event.z);
          synth.collect();
          toast(`${sim.boosting ? "+150" : "+100"} ENERGY / TAIL +4`);
          if (!reducedMotion) {
            $("flash").style.opacity = "1";
            setTimeout(() => ($("flash").style.opacity = "0"), 180);
          }
        }
      }
    }
  }
  if (frame++ % 3 === 0) updateHud();
  synth.update(sim.speed, state === "playing");
  view.render(sim, state, timestamp / 1000, dt, steer);
  requestAnimationFrame(animate);
}

async function initialize() {
  try {
    const { CityView } = await import("./world.js");
    view = new CityView($("city"), reducedMotion);
    window.addEventListener("resize", () => view.resize());
    $("city").addEventListener("webglcontextlost", (event) => {
      event.preventDefault();
      fail(new Error("WebGL context lost"));
    });
    setState("intro");
    $("start").disabled = false;
    $("start-label").textContent = "ENTER THE CITY";
    $("start-hint").textContent = matchMedia("(pointer: coarse)").matches
      ? "TOUCH CONTROLS / HEADPHONES RECOMMENDED"
      : "PRESS ENTER / HEADPHONES RECOMMENDED";
    requestAnimationFrame(animate);
  } catch (error) {
    fail(error);
  }
}
initialize();
