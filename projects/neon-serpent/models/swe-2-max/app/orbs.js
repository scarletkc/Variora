// Energy orbs: glowing pickups scattered on streets and plazas.
import * as THREE from "./vendor/three.module.js";
import { glow } from "./world.js";

const COUNT = 14;
const COLLECT_R = 2.4;
const NORMAL = 0x00ffc8;
const BONUS = 0xff2d95;

export class Orbs {
  constructor(scene, world) {
    this.world = world;
    this.group = new THREE.Group();
    scene.add(this.group);
    this.items = [];
    const geo = new THREE.IcosahedronGeometry(0.62, 0);
    const beamGeo = new THREE.CylinderGeometry(0.45, 0.9, 22, 8, 1, true);
    for (let i = 0; i < COUNT; i++) {
      const core = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: NORMAL }));
      const halo = new THREE.Sprite(new THREE.SpriteMaterial({
        map: glow(NORMAL), color: NORMAL, transparent: true,
        opacity: 0.85, blending: THREE.AdditiveBlending, depthWrite: false,
      }));
      halo.scale.setScalar(4.6);
      // Light column so orbs are visible down a long street.
      const beam = new THREE.Mesh(beamGeo, new THREE.MeshBasicMaterial({
        color: NORMAL, transparent: true, opacity: 0.26,
        blending: THREE.AdditiveBlending, side: THREE.DoubleSide, depthWrite: false,
      }));
      beam.position.y = 10;
      const item = {
        core, halo, beam, phase: Math.random() * Math.PI * 2,
        bonus: false, life: 0, alive: true, pos: new THREE.Vector3(),
      };
      core.add(halo, beam);
      this.group.add(core);
      this.items.push(item);
    }
  }

  reset(away) {
    for (const it of this.items) this._spawn(it, away);
  }

  _spawn(it, away) {
    const p = this.world.freePoint(Math.random, 1.2, away, 26);
    if (!p) {
      it.alive = false;
      it.core.visible = false;
      return;
    }
    it.alive = true;
    it.core.visible = true;
    it.pos.set(p.x, 1.5, p.z);
    it.core.position.copy(it.pos);
    it.bonus = Math.random() < 0.16;
    it.life = it.bonus ? 15 : Infinity;
    const color = it.bonus ? BONUS : NORMAL;
    it.core.material.color.setHex(color);
    it.halo.material.color.setHex(color);
    it.halo.material.map = glow(color);
    it.beam.material.color.setHex(color);
  }

  /** Animates every orb; only collects when `canCollect` is true. */
  update(t, dt, snake, onCollect, canCollect) {
    for (const it of this.items) {
      if (!it.alive) continue;
      it.core.position.set(
        it.pos.x,
        it.pos.y + Math.sin(t * 2.1 + it.phase) * 0.35,
        it.pos.z,
      );
      it.core.rotation.y = t * 1.4 + it.phase;
      it.core.rotation.x = t * 0.9;
      if (it.bonus) {
        it.life -= dt;
        const blink = it.life < 4 ? (Math.sin(t * 14) > 0 ? 1 : 0.25) : 1;
        it.core.material.opacity = blink;
        it.core.material.transparent = blink < 1;
        if (it.life <= 0) {
          this._spawn(it, snake.pos);
          continue;
        }
      }
      if (!canCollect) continue;
      const dx = snake.pos.x - it.pos.x, dz = snake.pos.z - it.pos.z;
      if (dx * dx + dz * dz < COLLECT_R * COLLECT_R) {
        onCollect(it.bonus, it.pos);
        this._spawn(it, snake.pos);
      }
    }
  }
}
