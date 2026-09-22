// DOM HUD, overlays, and the minimap.
import { HALF } from "./world.js";

const $ = (id) => document.getElementById(id);

export class HUD {
  constructor() {
    this.score = $("score");
    this.len = $("len");
    this.speedFill = $("speedfill");
    this.noticeEl = $("notice");
    this.countEl = $("countdown");
    this.muteEl = $("mute");
    this.map = $("map").getContext("2d");
    this.deadScore = $("dead-score");
    this.deadBest = $("dead-best");
    this.deadCause = $("dead-cause");
    this.overlays = {
      intro: $("overlay-intro"),
      pause: $("overlay-pause"),
      dead: $("overlay-dead"),
    };
    this._noticeUntil = 0;
    this._mapTimer = 0;
  }

  overlay(name) {
    for (const [k, el] of Object.entries(this.overlays)) {
      el.classList.toggle("hidden", k !== name);
    }
    $("hud").classList.toggle("hidden", name === "intro");
  }

  update({ score, len, speed, muted }) {
    this.score.textContent = score;
    this.len.textContent = len;
    this.speedFill.style.width = `${Math.min(100, (speed / 38) * 100)}%`;
    this.muteEl.textContent = muted ? "M · OFF" : "M · SND";
    if (performance.now() > this._noticeUntil) this.noticeEl.textContent = "";
  }

  notice(text, ms = 1400) {
    this.noticeEl.textContent = text;
    this._noticeUntil = performance.now() + ms;
  }

  countdown(text) {
    this.countEl.textContent = text || "";
    this.countEl.classList.toggle("hidden", !text);
  }

  flash() {
    const f = $("flash");
    f.classList.remove("go");
    void f.offsetWidth; // restart the CSS animation
    f.classList.add("go");
  }

  dead(score, best, cause) {
    this.deadScore.textContent = score;
    this.deadBest.textContent = best;
    this.deadCause.textContent = {
      wall: "You hit the boundary field.",
      building: "You hit a building.",
      self: "You bit your own tail.",
    }[cause] || "Signal lost.";
    this.overlay("dead");
  }

  drawMap(world, snake, orbs) {
    const g = this.map, S = 150;
    const w2m = (x) => ((x + HALF) / (2 * HALF)) * S;
    g.clearRect(0, 0, S, S);
    g.fillStyle = "rgba(4,6,14,0.85)";
    g.fillRect(0, 0, S, S);
    g.strokeStyle = "rgba(255,45,149,0.8)";
    g.lineWidth = 1.5;
    g.strokeRect(1, 1, S - 2, S - 2);
    g.fillStyle = "rgba(80,90,140,0.8)";
    for (const c of world.colliders) {
      g.fillRect(w2m(c.minX), w2m(c.minZ), Math.max(1.5, (c.maxX - c.minX) * S / (2 * HALF)), Math.max(1.5, (c.maxZ - c.minZ) * S / (2 * HALF)));
    }
    for (const it of orbs.items) {
      if (!it.alive) continue;
      g.fillStyle = it.bonus ? "#ff2d95" : "#00ffc8";
      g.beginPath();
      g.arc(w2m(it.pos.x), w2m(it.pos.z), it.bonus ? 2.6 : 1.8, 0, Math.PI * 2);
      g.fill();
    }
    // Trail.
    g.strokeStyle = "rgba(0,240,255,0.85)";
    g.lineWidth = 1.6;
    g.beginPath();
    for (let i = 0; i < snake.tx.length; i += 3) {
      const x = w2m(snake.tx[i]), y = w2m(snake.tz[i]);
      if (i === 0) g.moveTo(x, y); else g.lineTo(x, y);
    }
    g.lineTo(w2m(snake.pos.x), w2m(snake.pos.z));
    g.stroke();
    // Head + facing tick.
    const hx = w2m(snake.pos.x), hy = w2m(snake.pos.z);
    g.strokeStyle = "#ffffff";
    g.beginPath();
    g.moveTo(hx, hy);
    g.lineTo(hx + Math.cos(snake.heading) * 7, hy + Math.sin(snake.heading) * 7);
    g.stroke();
    g.fillStyle = "#ffffff";
    g.beginPath();
    g.arc(hx, hy, 2.4, 0, Math.PI * 2);
    g.fill();
  }
}
