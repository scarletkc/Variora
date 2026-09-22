// The serpent: continuous first-person movement, arc-length trail sampling,
// instanced bead body, and self-collision.
import * as THREE from "./vendor/three.module.js";
import { HEAD_Y, glow } from "./world.js";

const MAX_SEGMENTS = 420;
const SPACING = 1.55;        // arc distance between body beads
const STEP = 0.4;            // trail point spacing
const HEAD_R = 0.95;
const BODY_R = 0.8;
const START_SEGMENTS = 12;

const BODY_TOP = new THREE.Color(0x35f6ff);
const BODY_MID = new THREE.Color(0x7a5cff);
const BODY_TAIL = new THREE.Color(0xff2d95);

export class Snake {
  constructor(scene) {
    this.scene = scene;
    this.group = new THREE.Group();

    const beadGeo = new THREE.SphereGeometry(BODY_R, 14, 10);
    this.beads = new THREE.InstancedMesh(
      beadGeo,
      new THREE.MeshBasicMaterial({ color: 0xffffff }),
      MAX_SEGMENTS,
    );
    this.beads.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    this.beads.frustumCulled = false;
    this.group.add(this.beads);

    // Head: sphere + visor + glow sprite.
    this.head = new THREE.Group();
    const skull = new THREE.Mesh(
      new THREE.SphereGeometry(HEAD_R, 20, 14),
      new THREE.MeshBasicMaterial({ color: 0x18e0ff }),
    );
    skull.scale.set(1.15, 0.9, 1.3);
    const visor = new THREE.Mesh(
      new THREE.SphereGeometry(HEAD_R * 0.72, 14, 10),
      new THREE.MeshBasicMaterial({ color: 0xff2d95 }),
    );
    visor.scale.set(0.9, 0.5, 0.6);
    visor.position.set(0, 0.16, HEAD_R * 0.78);
    const crest = new THREE.Mesh(
      new THREE.ConeGeometry(0.22, 1.4, 6),
      new THREE.MeshBasicMaterial({ color: 0x9b5cff }),
    );
    crest.position.set(0, HEAD_R * 0.9, -HEAD_R * 0.35);
    crest.rotation.x = -0.7;
    const halo = new THREE.Sprite(new THREE.SpriteMaterial({
      map: glow(0x00f0ff), color: 0x00f0ff,
      transparent: true, opacity: 0.55, blending: THREE.AdditiveBlending,
      depthWrite: false,
    }));
    halo.scale.setScalar(6.5);
    this.head.add(skull, visor, crest, halo);
    this.group.add(this.head);

    // Cyan glow the serpent casts on the street.
    this.lamp = new THREE.PointLight(0x22ddff, 60, 26, 1.8);
    this.group.add(this.lamp);

    scene.add(this.group);
    this._m = new THREE.Matrix4();
    this._c = new THREE.Color();
    this.reset();
  }

  reset(x = 20, z = 0, heading = -Math.PI / 2) {
    this.pos = new THREE.Vector3(x, HEAD_Y, z);
    this.heading = heading;
    this.energy = 0;
    this.segments = START_SEGMENTS;
    this.alive = true;
    this.grace = 1.6;
    this.turnSmooth = 0;
    this.dist = 0;
    // Trail of breadcrumb points: x, z and cumulative arc distance.
    this.tx = [x];
    this.tz = [z];
    this.td = [0];
    this.beads.count = this.segments;
    this._recolor();
    this._placeHead();
  }

  get speed() {
    return Math.min(13 + this.energy * 0.22, 23);
  }

  grow(n) {
    this.energy += n;
    this.segments = Math.min(this.segments + 2 + n, MAX_SEGMENTS);
    this.beads.count = this.segments;
    this._recolor();
  }

  _recolor() {
    for (let i = 0; i < this.segments; i++) {
      const t = i / Math.max(1, this.segments - 1);
      if (t < 0.5) this._c.lerpColors(BODY_TOP, BODY_MID, t * 2);
      else this._c.lerpColors(BODY_MID, BODY_TAIL, (t - 0.5) * 2);
      this.beads.setColorAt(i, this._c);
    }
    if (this.beads.instanceColor) this.beads.instanceColor.needsUpdate = true;
  }

  /**
   * @param {number} dt   fixed timestep
   * @param {number} turn analog steering, -1..1
   * @param {number} look instantaneous heading delta from the mouse (radians)
   * @param {boolean} boost
   */
  update(dt, turn, look, boost) {
    if (!this.alive) return;
    this.grace = Math.max(0, this.grace - dt);

    const target = THREE.MathUtils.clamp(turn, -1, 1);
    this.turnSmooth += (target - this.turnSmooth) * Math.min(1, dt * 10);
    const rate = boost ? 2.9 : 2.35; // rad/s at full lock
    this.heading += this.turnSmooth * rate * dt + look;

    const v = this.speed * (boost ? 1.65 : 1);
    this.pos.x += Math.cos(this.heading) * v * dt;
    this.pos.z += Math.sin(this.heading) * v * dt;
    this.dist += v * dt;

    const n = this.tx.length - 1;
    const dx = this.pos.x - this.tx[n], dz = this.pos.z - this.tz[n];
    if (dx * dx + dz * dz > STEP * STEP) {
      this.tx.push(this.pos.x);
      this.tz.push(this.pos.z);
      this.td.push(this.dist);
    }
    this._updateBody();
    this._placeHead();
  }

  _placeHead() {
    this.head.position.copy(this.pos);
    this.head.rotation.y = Math.PI / 2 - this.heading;
    this.lamp.position.set(this.pos.x, this.pos.y + 1.2, this.pos.z);
  }

  // Walk the trail backwards once, placing every bead by arc distance.
  _updateBody() {
    let pi = this.tx.length - 1;
    const s = new THREE.Vector3();
    for (let i = 0; i < this.segments; i++) {
      const target = this.dist - (i + 1) * SPACING;
      if (target <= 0) {
        // Not enough trail yet: stack beads behind the head.
        s.set(
          this.pos.x - Math.cos(this.heading) * (i + 1) * SPACING,
          HEAD_Y,
          this.pos.z - Math.sin(this.heading) * (i + 1) * SPACING,
        );
      } else {
        while (pi > 0 && this.td[pi - 1] > target) pi--;
        const i1 = Math.max(0, pi - 1);
        const span = this.td[pi] - this.td[i1] || 1;
        const f = THREE.MathUtils.clamp((target - this.td[i1]) / span, 0, 1);
        s.set(
          this.tx[i1] + (this.tx[pi] - this.tx[i1]) * f,
          HEAD_Y,
          this.tz[i1] + (this.tz[pi] - this.tz[i1]) * f,
        );
      }
      const taper = 1 - (i / this.segments) * 0.55;
      this._m.makeScale(taper, taper, taper).setPosition(s);
      this.beads.setMatrixAt(i, this._m);
    }
    this.beads.instanceMatrix.needsUpdate = true;

    // Trim trail points no bead can still reach.
    const need = this.dist - (this.segments + 4) * SPACING;
    let cut = 0;
    while (cut < this.td.length - 2 && this.td[cut + 1] < need) cut++;
    if (cut > 0) {
      this.tx.splice(0, cut);
      this.tz.splice(0, cut);
      this.td.splice(0, cut);
    }
  }

  /** Distance from the head to body bead i (used by self-collision + minimap). */
  selfHit() {
    if (this.grace > 0 || this.segments < 10) return false;
    const r = HEAD_R + BODY_R * 0.72;
    let pi = this.tx.length - 1;
    for (let i = 7; i < this.segments; i++) {
      const target = this.dist - (i + 1) * SPACING;
      if (target <= 0) break;
      while (pi > 0 && this.td[pi - 1] > target) pi--;
      const i1 = Math.max(0, pi - 1);
      const span = this.td[pi] - this.td[i1] || 1;
      const f = THREE.MathUtils.clamp((target - this.td[i1]) / span, 0, 1);
      const x = this.tx[i1] + (this.tx[pi] - this.tx[i1]) * f;
      const z = this.tz[i1] + (this.tz[pi] - this.tz[i1]) * f;
      const dx = this.pos.x - x, dz = this.pos.z - z;
      if (dx * dx + dz * dz < r * r) return true;
    }
    return false;
  }

  die() {
    this.alive = false;
  }
}
