// Neon Serpent — first-person snake in a procedural neon city.
import * as THREE from "./vendor/three.module.js";
import { buildCity, HALF, HEAD_Y } from "./world.js";
import { Snake } from "./snake.js";
import { Orbs } from "./orbs.js";
import { Input } from "./input.js";
import { AudioEngine } from "./audio.js";
import { HUD } from "./hud.js";
import { store } from "./store.js";

const STEP = 1 / 60;
const canvas = document.getElementById("gl");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x0a0616, 0.016);

const camera = new THREE.PerspectiveCamera(74, 1, 0.1, 3200);
scene.add(new THREE.AmbientLight(0x334466, 0.9));
scene.add(new THREE.HemisphereLight(0x3a2a5e, 0x0a0a14, 0.7));

// Headlamp: the snake carries a soft spotlight down the street.
const lamp = new THREE.SpotLight(0xbfe8ff, 400, 90, 0.62, 0.7, 1.4);
const lampTarget = new THREE.Object3D();
scene.add(lamp, lampTarget);
lamp.target = lampTarget;

const world = buildCity(scene);
const snake = new Snake(scene);
const orbs = new Orbs(scene, world);
const input = new Input(canvas);
const audio = new AudioEngine();
const hud = new HUD();

let state = "intro";        // intro | countdown | playing | paused | dying | dead
let score = 0;
let best = Number(store.get("neon-serpent-best") || 0);
let countdownT = 0, countStep = 0;
let deathT = 0, deathCause = null;
let camYaw = snake.heading;
let acc = 0, lastT = performance.now() / 1000, simT = 0;
let auto = false;           // debug/screenshot autopilot

orbs.reset(snake.pos);
hud.overlay("intro");
hud.update({ score: 0, len: snake.segments, speed: 0, muted: audio.muted });

function start() {
  audio.ensure();
  audio.ui();
  snake.reset();
  orbs.reset(snake.pos);
  score = 0;
  camYaw = snake.heading;
  acc = 0;
  state = "countdown";
  countStep = 3;
  countdownT = 0.01;
  hud.overlay(null);
  input.lock();
}

function resume() {
  if (state !== "paused") return;
  audio.ui();
  acc = 0;
  state = "playing";
  hud.overlay(null);
  input.lock();
}

function pause() {
  if (state !== "playing") return;
  state = "paused";
  hud.overlay("pause");
  input.unlock();
  audio.update(0, false, false);
}

function die(cause) {
  if (state !== "playing" || !snake.alive) return;
  snake.die();
  deathCause = cause;
  deathT = 0.9;
  state = "dying";
  audio.crash();
  hud.flash();
  input.unlock();
}

function collect(bonus) {
  score += bonus ? 3 : 1;
  snake.grow(bonus ? 2 : 1);
  audio.pickup(bonus);
  hud.notice(bonus ? "+3 BONUS ボーナス" : "+1 ENERGY", bonus ? 1600 : 700);
}

function stepSim(dt) {
  simT += dt;
  let turn = input.turnAxis();
  if (auto) {
    // Autopilot: steer toward the nearest orb (used by tests/screenshots).
    let bestIt = null, bestD = Infinity;
    for (const it of orbs.items) {
      if (!it.alive) continue;
      const d = (it.pos.x - snake.pos.x) ** 2 + (it.pos.z - snake.pos.z) ** 2;
      if (d < bestD) { bestD = d; bestIt = it; }
    }
    if (bestIt) {
      const want = Math.atan2(bestIt.pos.z - snake.pos.z, bestIt.pos.x - snake.pos.x);
      let diff = want - snake.heading;
      while (diff > Math.PI) diff -= Math.PI * 2;
      while (diff < -Math.PI) diff += Math.PI * 2;
      turn = THREE.MathUtils.clamp(diff * 1.6, -1, 1);
    }
  }
  snake.update(dt, turn, input.consumeLook(), input.boost);

  const hit = world.hitTest(snake.pos.x, snake.pos.z, 0.9);
  if (hit) return die(hit);
  if (snake.selfHit()) return die("self");

  orbs.update(simT, dt, snake, collect, true);
}

function updateCamera(dt, t) {
  // The head mesh is only visible in third-person moments (intro/death cam);
  // in first person the camera sits inside it.
  snake.head.visible = state === "intro" || state === "dead";
  if (state === "intro") {
    const a = t * 0.06;
    camera.position.set(Math.cos(a) * 110, 46 + Math.sin(t * 0.3) * 8, Math.sin(a) * 110);
    camera.lookAt(0, 10, 0);
    camera.fov += (66 - camera.fov) * Math.min(1, dt * 2);
    camera.updateProjectionMatrix();
    return;
  }
  if (state === "dead") {
    // Slow crane shot: rise above the fallen serpent.
    camera.position.y = Math.min(camera.position.y + dt * 7, snake.pos.y + 30);
    camera.lookAt(snake.pos.x, 0, snake.pos.z);
    return;
  }
  // Smooth follow of the head with a little yaw lag and bank.
  let diff = snake.heading - camYaw;
  while (diff > Math.PI) diff -= Math.PI * 2;
  while (diff < -Math.PI) diff += Math.PI * 2;
  camYaw += diff * Math.min(1, dt * 9);

  const shake = state === "dying" ? deathT * 0.5 : 0;
  camera.position.set(
    snake.pos.x + (Math.random() - 0.5) * shake,
    snake.pos.y + 0.62 + (Math.random() - 0.5) * shake,
    snake.pos.z + (Math.random() - 0.5) * shake,
  );
  const dir = new THREE.Vector3(Math.cos(camYaw), 0, Math.sin(camYaw));
  const look = camera.position.clone().addScaledVector(dir, 8);
  look.y -= 0.5;
  camera.lookAt(look);
  camera.rotateZ(-snake.turnSmooth * 0.1);
  const fovT = input.boost && state === "playing" ? 88 : 74;
  camera.fov += (fovT - camera.fov) * Math.min(1, dt * 6);
  camera.updateProjectionMatrix();

  lamp.position.copy(camera.position);
  lampTarget.position.copy(look).setY(0.5);
}

function frame() {
  requestAnimationFrame(frame);
  const now = performance.now() / 1000;
  const dt = Math.min(now - lastT, 0.1);
  lastT = now;
  const t = now;

  // Global actions.
  if (input.consume("mute")) {
    audio.ensure();
    hud.notice(audio.toggleMute() ? "AUDIO OFF" : "AUDIO ON");
  }
  if (input.consume("pause")) {
    if (state === "playing") pause();
    else if (state === "paused") resume();
  }
  if (input.consume("unlock") && state === "playing") pause();
  if (input.consume("restart") && (state === "playing" || state === "dead" || state === "paused")) {
    start();
  }

  if (state === "countdown") {
    countdownT -= dt;
    if (countdownT <= 0) {
      if (countStep > 0) {
        audio.count(false);
        hud.countdown(String(countStep));
        countStep--;
        countdownT = 0.7;
      } else {
        hud.countdown("GO 行け");
        audio.count(true);
        state = "playing";
        setTimeout(() => hud.countdown(""), 500);
      }
    }
  } else if (state === "playing") {
    acc += dt;
    let n = 0;
    while (acc >= STEP && n++ < 6) {
      stepSim(STEP);
      acc -= STEP;
      if (state !== "playing") { acc = 0; break; }
    }
  } else if (state === "dying") {
    deathT -= dt;
    if (deathT <= 0) {
      state = "dead";
      best = Math.max(best, score);
      store.set("neon-serpent-best", String(best));
      audio.gameover();
      hud.dead(score, best, deathCause);
    }
  }

  if (state !== "playing") orbs.update(t, dt, snake, collect, false);
  world.update(t, dt, snake.pos);
  updateCamera(dt, t);
  audio.update(snake.speed, input.boost, state === "playing");
  hud.update({
    score, len: snake.segments,
    speed: snake.speed * (input.boost ? 1.65 : 1),
    muted: audio.muted,
  });
  if ((hud._mapTimer -= dt) <= 0 && state !== "intro") {
    hud.drawMap(world, snake, orbs);
    hud._mapTimer = 0.12;
  }
  renderer.render(scene, camera);
}

function resize() {
  renderer.setSize(innerWidth, innerHeight);
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
}
addEventListener("resize", resize);
resize();

document.getElementById("start").addEventListener("click", start);
document.getElementById("retry").addEventListener("click", start);
document.getElementById("resume").addEventListener("click", resume);
document.addEventListener("visibilitychange", () => {
  if (document.hidden && state === "playing") pause();
});

// Touch boost button.
const boostBtn = document.getElementById("boost");
if (input.isTouch) boostBtn.classList.remove("hidden");
boostBtn.addEventListener("touchstart", (e) => { e.preventDefault(); input.touchBoost = true; });
boostBtn.addEventListener("touchend", (e) => { e.preventDefault(); input.touchBoost = false; });

// Debug/testing hooks.
window.__NEON = {
  get state() { return state; },
  get score() { return score; },
  get best() { return best; },
  snake, orbs, world,
  start, die,
  teleport(x, z) { snake.pos.set(x, HEAD_Y, z); },
  setAuto(v) { auto = v; },
};

frame();
