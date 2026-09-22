export const WORLD_LIMIT = 57;
export const ROAD_CENTERS = [-48, -24, 0, 24, 48];
export const HEAD_RADIUS = 0.55;
export const BODY_SPACING = 0.72;
export const TURN_RATE = 1.85;

export function seededRandom(seed = 7241) {
  return () => {
    seed = (Math.imul(1664525, seed) + 1013904223) >>> 0;
    return seed / 4294967296;
  };
}

export function cityBlocks() {
  const blocks = [];
  for (let x = -36; x <= 36; x += 24) {
    for (let z = -36; z <= 36; z += 24) {
      blocks.push({ x, z, half: 7.8 });
    }
  }
  return blocks;
}

export const BLOCKS = cityBlocks();

export function wallAt(x, z, padding = HEAD_RADIUS) {
  if (
    Math.abs(x) > WORLD_LIMIT - padding ||
    Math.abs(z) > WORLD_LIMIT - padding
  )
    return true;
  return BLOCKS.some(
    (b) =>
      Math.abs(x - b.x) < b.half + padding &&
      Math.abs(z - b.z) < b.half + padding,
  );
}

function wrapAngle(angle) {
  return Math.atan2(Math.sin(angle), Math.cos(angle));
}

export class Simulation {
  constructor(random = Math.random) {
    this.random = random;
    this.reset();
  }

  reset() {
    this.x = 0;
    this.z = 39;
    this.heading = 0;
    this.speed = 0;
    this.score = 0;
    this.collected = 0;
    this.distance = 0;
    this.elapsed = 0;
    this.charge = 100;
    this.boosting = false;
    this.alive = true;
    this.reason = "";
    this.segmentCount = 14;
    this.path = [];
    for (let d = 0; d < 16; d += 0.15) this.path.push({ x: 0, z: 39 + d });
    this.cores = [
      { x: 0, z: 27 },
      { x: 0, z: 13 },
      { x: 0, z: -3 },
      { x: 24, z: 0 },
      { x: -24, z: 24 },
      { x: 0, z: -26 },
    ];
  }

  bodyPoints() {
    const points = [];
    let traversed = 0;
    let target = BODY_SPACING;
    for (
      let i = 1;
      i < this.path.length && points.length < this.segmentCount;
      i++
    ) {
      const a = this.path[i - 1],
        b = this.path[i];
      const length = Math.hypot(b.x - a.x, b.z - a.z);
      if (length < 0.00001) continue;
      while (
        target <= traversed + length &&
        points.length < this.segmentCount
      ) {
        const t = (target - traversed) / length;
        points.push({ x: a.x + (b.x - a.x) * t, z: a.z + (b.z - a.z) * t });
        target += BODY_SPACING;
      }
      traversed += length;
    }
    return points;
  }

  spawnCore() {
    for (let attempt = 0; attempt < 200; attempt++) {
      const road =
        ROAD_CENTERS[Math.floor(this.random() * ROAD_CENTERS.length)];
      const offset = (this.random() - 0.5) * 94;
      const point =
        this.random() < 0.5 ? { x: road, z: offset } : { x: offset, z: road };
      if (Math.hypot(point.x - this.x, point.z - this.z) < 12) continue;
      if (this.cores.some((c) => Math.hypot(c.x - point.x, c.z - point.z) < 9))
        continue;
      if (this.path.some((p) => Math.hypot(p.x - point.x, p.z - point.z) < 2))
        continue;
      return point;
    }
    // A full route can temporarily have no free slot; retry on a later step.
    return null;
  }

  nearestCore() {
    let nearest = null,
      distance = Infinity;
    for (const core of this.cores) {
      const d = Math.hypot(core.x - this.x, core.z - this.z);
      if (d < distance) {
        nearest = core;
        distance = d;
      }
    }
    return nearest
      ? {
          ...nearest,
          distance,
          bearing: wrapAngle(
            Math.atan2(nearest.x - this.x, -(nearest.z - this.z)) -
              this.heading,
          ),
        }
      : null;
  }

  step(dt, steer = 0, boost = false) {
    if (!this.alive || dt <= 0) return [];
    // Bound each collision sweep even when callers submit a long frame.
    if (dt > 1 / 60 + 1e-8) {
      const events = [];
      const steps = Math.ceil(dt * 60);
      for (let i = 0; i < steps; i++)
        events.push(...this.step(dt / steps, steer, boost));
      return events;
    }
    const events = [];
    this.boosting = boost && this.charge > 1;
    this.charge = Math.max(
      0,
      Math.min(100, this.charge + (this.boosting ? -29 : 16) * dt),
    );
    this.speed =
      (8 + Math.min(this.collected, 30) * 0.1) * (this.boosting ? 1.7 : 1);
    this.heading = wrapAngle(
      this.heading + Math.max(-1, Math.min(1, steer)) * TURN_RATE * dt,
    );
    this.x += Math.sin(this.heading) * this.speed * dt;
    this.z -= Math.cos(this.heading) * this.speed * dt;
    this.distance += this.speed * dt;
    this.elapsed += dt;

    if (wallAt(this.x, this.z)) this.crash("CITY COLLISION");
    if (
      this.alive &&
      this.bodyPoints()
        .slice(8)
        .some((p) => Math.hypot(this.x - p.x, this.z - p.z) < 0.86)
    )
      this.crash("TAIL COLLISION");
    if (!this.alive) return [{ type: "crash", reason: this.reason }];

    this.path.unshift({ x: this.x, z: this.z });
    let trailLength = 0;
    for (let i = 1; i < this.path.length; i++) {
      trailLength += Math.hypot(
        this.path[i].x - this.path[i - 1].x,
        this.path[i].z - this.path[i - 1].z,
      );
      if (trailLength > (this.segmentCount + 3) * BODY_SPACING) {
        this.path.length = i + 1;
        break;
      }
    }
    for (let i = this.cores.length - 1; i >= 0; i--) {
      const core = this.cores[i];
      if (Math.hypot(this.x - core.x, this.z - core.z) < 1.7) {
        this.cores.splice(i, 1);
        this.collected++;
        this.score += this.boosting ? 150 : 100;
        this.segmentCount += 4;
        this.charge = Math.min(100, this.charge + 18);
        events.push({ type: "collect", ...core });
      }
    }
    while (this.cores.length < 6) {
      const core = this.spawnCore();
      if (!core) break;
      this.cores.push(core);
    }
    return events;
  }

  crash(reason) {
    this.alive = false;
    this.reason = reason;
    this.speed = 0;
    this.boosting = false;
  }
}
