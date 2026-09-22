import test from "node:test";
import assert from "node:assert/strict";
import {
  Simulation,
  seededRandom,
  wallAt,
  HEAD_RADIUS,
  WORLD_LIMIT,
} from "../app/simulation.mjs";

test("collecting a core increases score and grows a continuous following tail", () => {
  const sim = new Simulation(seededRandom(41));
  const events = sim.step(1.5);
  assert.equal(sim.collected, 1);
  assert.equal(sim.score, 100);
  assert.equal(sim.segmentCount, 18);
  assert.equal(events.filter((event) => event.type === "collect").length, 1);
  const points = sim.bodyPoints();
  assert.ok(points.length >= 14);
  assert.ok(points.every((p) => Math.abs(p.x) < 0.001 && p.z > sim.z));
  assert.equal(sim.cores.length, 6);
  assert.ok(sim.cores.every((core) => !wallAt(core.x, core.z)));
});

test("long frames cannot tunnel through a building or boundary", () => {
  const building = new Simulation();
  building.x = 0;
  building.z = 36;
  building.heading = Math.PI / 2;
  assert.equal(building.step(2).at(-1).reason, "CITY COLLISION");
  assert.ok(building.x < 5);
  const edge = new Simulation();
  edge.z = -55;
  assert.equal(edge.step(1).at(-1).reason, "CITY COLLISION");
  assert.ok(edge.z >= -WORLD_LIMIT + HEAD_RADIUS - 0.15);
});

test("turning changes head direction and the body follows the traveled curve", () => {
  const sim = new Simulation();
  sim.x = 0;
  sim.z = 0;
  sim.path = [{ x: 0, z: 0 }];
  sim.step(0.6, 1);
  assert.ok(sim.x > 1 && sim.heading > 1);
  const points = sim.bodyPoints();
  assert.ok(points.length > 3);
  assert.ok(points[0].x < sim.x);
  assert.ok(points.at(-1).x < points[0].x);
});

test("old tail collisions end the run, while nearby neck segments are allowed", () => {
  const sim = new Simulation();
  sim.x = 0;
  sim.z = 0;
  sim.path = [
    { x: 0, z: 0 },
    { x: 0, z: 3 },
    { x: 3, z: 3 },
    { x: 3, z: -1 },
    { x: 0, z: -1 },
    { x: 0, z: -4 },
  ];
  sim.segmentCount = 30;
  const events = sim.step(0.1);
  assert.equal(events.at(-1).reason, "TAIL COLLISION");
  const stopped = [sim.x, sim.z, sim.score];
  assert.deepEqual(sim.step(1), []);
  assert.deepEqual([sim.x, sim.z, sim.score], stopped);
  const straight = new Simulation();
  straight.step(0.5);
  assert.equal(straight.alive, true);
});

test("boost uses charge, earns a bonus, and recharges when released", () => {
  const sim = new Simulation(seededRandom(5));
  sim.step(1, 0, true);
  assert.equal(sim.collected, 1);
  assert.equal(sim.score, 150);
  assert.ok(sim.charge < 100);
  assert.ok(sim.speed > 13);
  const charge = sim.charge;
  sim.step(0.2, 0, false);
  assert.ok(sim.charge > charge);
  assert.ok(sim.speed < 9);
  sim.charge = 0;
  sim.step(1 / 120, 0, true);
  assert.equal(sim.boosting, false);
  assert.ok(sim.charge > 0);
});

test("seeded runs reproduce pickup locations and reset clears the previous run", () => {
  const a = new Simulation(seededRandom(7)),
    b = new Simulation(seededRandom(7));
  a.step(3);
  b.step(3);
  assert.deepEqual(a.cores, b.cores);
  a.crash("CITY COLLISION");
  a.reset();
  assert.equal(a.alive, true);
  assert.equal(a.score, 0);
  assert.equal(a.charge, 100);
  assert.equal(a.segmentCount, 14);
  assert.equal(a.x, 0);
  assert.equal(a.z, 39);
});

test("spawn failure on a crowded route is bounded", () => {
  const sim = new Simulation(() => 0.5);
  sim.cores = [{ x: 0, z: 0 }];
  assert.equal(sim.spawnCore(), null);
});
