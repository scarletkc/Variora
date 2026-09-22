// City generation: buildings, neon signs, torii gates, ground, sky, walls.
// Everything is procedural — all textures are drawn into canvases at runtime.
import * as THREE from "./vendor/three.module.js";

export const WORLD = { blocks: 13, lot: 26, street: 14 };
export const PITCH = WORLD.lot + WORLD.street;
export const HALF =
  (WORLD.blocks * WORLD.lot + (WORLD.blocks + 1) * WORLD.street) / 2;
export const HEAD_Y = 1.55;
export const WALL_HEIGHT = 14;

const NEON = [0x00f0ff, 0xff2d95, 0x9b5cff, 0x00ffc8, 0xffb000, 0xff5544];
const SIGN_WORDS = [
  "ネオン", "ラーメン", "寿司", "酒場", "未来", "東京", "カラオケ", "ホテル",
  "夜市", "電脳", "龍", "蛇", "光", "夢", "パチンコ", "焼鳥", "ビール",
  "入口", "天国", "無限", "都市", "遊", "祭",
];

export function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function canvas(w, h) {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  return [c, c.getContext("2d")];
}

// Merge transformed geometries into one non-indexed BufferGeometry.
// uvs are rescaled by `uvForVertex(part, vertex, normal)` when provided.
function mergeParts(parts) {
  const pos = [], nrm = [], uv = [];
  const v = new THREE.Vector3(), n = new THREE.Vector3();
  const nm = new THREE.Matrix3();
  for (const part of parts) {
    const g = part.geometry.toNonIndexed();
    nm.getNormalMatrix(part.matrix);
    const p = g.attributes.position, u = g.attributes.uv;
    const nn = g.attributes.normal;
    for (let i = 0; i < p.count; i++) {
      v.fromBufferAttribute(p, i).applyMatrix4(part.matrix);
      n.fromBufferAttribute(nn, i).applyMatrix3(nm).normalize();
      pos.push(v.x, v.y, v.z);
      nrm.push(n.x, n.y, n.z);
      let ux = u.getX(i), uy = u.getY(i);
      if (part.uvScale) {
        // BoxGeometry: pick the horizontal face extent from the normal axis.
        const s = Math.abs(n.x) > 0.5 ? part.uvScale[1] : part.uvScale[0];
        ux *= s;
        uy *= part.uvScale[2];
      }
      uv.push(ux, uy);
    }
    g.dispose();
    part.geometry.dispose();
  }
  const out = new THREE.BufferGeometry();
  out.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  out.setAttribute("normal", new THREE.Float32BufferAttribute(nrm, 3));
  out.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2));
  return out;
}

// Concatenate EdgeGeometry line segments into a single vertex-colored geometry.
function mergeEdges(edges) {
  const pos = [], col = [];
  const v = new THREE.Vector3(), c = new THREE.Color();
  for (const e of edges) {
    const g = e.geometry;
    const p = g.attributes.position;
    c.set(e.color);
    for (let i = 0; i < p.count; i++) {
      v.fromBufferAttribute(p, i).applyMatrix4(e.matrix);
      pos.push(v.x, v.y, v.z);
      col.push(c.r, c.g, c.b);
    }
    g.dispose();
  }
  const out = new THREE.BufferGeometry();
  out.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  out.setAttribute("color", new THREE.Float32BufferAttribute(col, 3));
  return out;
}

function windowTexture(rand) {
  const [c, g] = canvas(256, 256);
  g.fillStyle = "#05070f";
  g.fillRect(0, 0, 256, 256);
  const tints = ["#67f6ff", "#ffb35c", "#ff5cb8", "#8f7bff", "#b7ff5c"];
  // One texture tile covers ~9u of facade; windows are ~1.4u wide.
  for (let y = 10; y < 236; y += 26) {
    const floorLit = rand() > 0.18; // occasional dark floor band
    for (let x = 10; x < 236; x += 21) {
      const r = rand();
      if (floorLit && r < 0.36) {
        g.fillStyle = tints[(rand() * tints.length) | 0];
        g.globalAlpha = 0.4 + rand() * 0.6;
        g.fillRect(x, y, 13, 16);
      } else if (r < 0.5) {
        g.fillStyle = "#141b2b";
        g.globalAlpha = 1;
        g.fillRect(x, y, 13, 16);
      }
    }
  }
  g.globalAlpha = 1;
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

function groundTexture() {
  const S = 2048;
  const [c, g] = canvas(S, S);
  const w2p = (x) => ((x + HALF) / (2 * HALF)) * S;
  const scale = S / (2 * HALF);
  g.fillStyle = "#06070f";
  g.fillRect(0, 0, S, S);

  // Block lots: slightly raised pavement + neon curb.
  for (let i = 0; i < WORLD.blocks; i++) {
    for (let j = 0; j < WORLD.blocks; j++) {
      const cx = (i - (WORLD.blocks - 1) / 2) * PITCH;
      const cz = (j - (WORLD.blocks - 1) / 2) * PITCH;
      const x = w2p(cx - WORLD.lot / 2), y = w2p(cz - WORLD.lot / 2);
      const s = WORLD.lot * scale;
      g.fillStyle = "#0a0e1c";
      g.fillRect(x, y, s, s);
      g.strokeStyle = "rgba(0,240,255,0.5)";
      g.lineWidth = 3;
      g.strokeRect(x + 1.5, y + 1.5, s - 3, s - 3);
      g.strokeStyle = "rgba(255,45,149,0.16)";
      g.lineWidth = 9;
      g.strokeRect(x + 4.5, y + 4.5, s - 9, s - 9);
    }
  }

  // Street centerlines: dashed cyan.
  g.strokeStyle = "rgba(0,240,255,0.55)";
  g.lineWidth = 2.5;
  g.setLineDash([18, 22]);
  for (let k = 0; k <= WORLD.blocks; k++) {
    const p = w2p(-HALF + WORLD.street / 2 + k * PITCH);
    g.beginPath(); g.moveTo(p, 0); g.lineTo(p, S); g.stroke();
    g.beginPath(); g.moveTo(0, p); g.lineTo(S, p); g.stroke();
  }
  g.setLineDash([]);

  // Intersection nodes: magenta glow dots.
  g.fillStyle = "rgba(255,45,149,0.7)";
  for (let a = 0; a <= WORLD.blocks; a++) {
    for (let b = 0; b <= WORLD.blocks; b++) {
      const x = w2p(-HALF + WORLD.street / 2 + a * PITCH);
      const y = w2p(-HALF + WORLD.street / 2 + b * PITCH);
      g.beginPath(); g.arc(x, y, 5, 0, Math.PI * 2); g.fill();
    }
  }

  // Boundary.
  g.strokeStyle = "rgba(255,45,149,0.9)";
  g.lineWidth = 10;
  g.strokeRect(6, 6, S - 12, S - 12);

  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  return tex;
}

function wallTexture() {
  const [c, g] = canvas(512, 128);
  const grad = g.createLinearGradient(0, 128, 0, 0);
  grad.addColorStop(0, "rgba(255,45,149,0.0)");
  grad.addColorStop(0.55, "rgba(255,45,149,0.28)");
  grad.addColorStop(1, "rgba(255,120,200,0.9)");
  g.fillStyle = grad;
  g.fillRect(0, 0, 512, 128);
  g.strokeStyle = "rgba(255,255,255,0.25)";
  for (let x = 0; x < 512; x += 16) {
    g.beginPath(); g.moveTo(x, 0); g.lineTo(x, 128); g.stroke();
  }
  const tex = new THREE.CanvasTexture(c);
  tex.wrapS = THREE.RepeatWrapping;
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

function signTexture(word, color, vertical) {
  const [c, g] = vertical ? canvas(64, 256) : canvas(256, 80);
  const css = `#${color.toString(16).padStart(6, "0")}`;
  g.fillStyle = "rgba(6,6,16,0.92)";
  g.fillRect(0, 0, c.width, c.height);
  g.strokeStyle = css;
  g.lineWidth = 4;
  g.strokeRect(4, 4, c.width - 8, c.height - 8);
  g.fillStyle = css;
  g.shadowColor = css;
  g.shadowBlur = 14;
  g.textAlign = "center";
  g.textBaseline = "middle";
  if (vertical) {
    g.font = "bold 40px monospace";
    const step = (c.height - 30) / word.length;
    for (let i = 0; i < word.length; i++) {
      g.fillText(word[i], c.width / 2, 22 + step * (i + 0.5));
    }
  } else {
    g.font = `bold ${word.length > 3 ? 34 : 44}px monospace`;
    g.fillText(word, c.width / 2, c.height / 2 + 2);
  }
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

function glowSprite(color, size = 64) {
  const [c, g] = canvas(size, size);
  const grad = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  const css = `#${color.toString(16).padStart(6, "0")}`;
  grad.addColorStop(0, css);
  grad.addColorStop(0.35, css + "88");
  grad.addColorStop(1, "rgba(0,0,0,0)");
  g.fillStyle = grad;
  g.fillRect(0, 0, size, size);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

export const glowTextures = {};
export function glow(color) {
  if (!glowTextures[color]) glowTextures[color] = glowSprite(color);
  return glowTextures[color];
}

export function buildCity(scene, seed = 20260922) {
  const rand = mulberry32(seed);
  const colliders = [];   // {minX, maxX, minZ, maxZ}
  const group = new THREE.Group();
  const dynamic = [];     // objects with an update(t, dt)

  // --- Sky dome + stars -----------------------------------------------
  const domeGeo = new THREE.SphereGeometry(1500, 32, 16);
  const dc = [];
  const top = new THREE.Color(0x030209), mid = new THREE.Color(0x140a26),
    hor = new THREE.Color(0x3d1040);
  {
    const p = domeGeo.attributes.position;
    const tmp = new THREE.Color();
    for (let i = 0; i < p.count; i++) {
      const y = p.getY(i) / 1500;
      if (y > 0.25) tmp.lerpColors(mid, top, Math.min(1, (y - 0.25) / 0.7));
      else tmp.lerpColors(hor, mid, Math.max(0, Math.min(1, (y + 0.12) / 0.4)));
      dc.push(tmp.r, tmp.g, tmp.b);
    }
  }
  domeGeo.setAttribute("color", new THREE.Float32BufferAttribute(dc, 3));
  const dome = new THREE.Mesh(
    domeGeo,
    new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide, fog: false }),
  );
  group.add(dome);

  {
    const n = 700, sp = [];
    for (let i = 0; i < n; i++) {
      const t = rand() * Math.PI * 2, u = 0.08 + rand() * 0.85;
      const r = 1350;
      sp.push(r * Math.sqrt(1 - u * u) * Math.cos(t), r * u, r * Math.sqrt(1 - u * u) * Math.sin(t));
    }
    const sg = new THREE.BufferGeometry();
    sg.setAttribute("position", new THREE.Float32BufferAttribute(sp, 3));
    const stars = new THREE.Points(sg, new THREE.PointsMaterial({
      color: 0x9fc4ff, size: 2.2, sizeAttenuation: false,
      transparent: true, opacity: 0.75, fog: false,
    }));
    group.add(stars);
  }

  // Moon.
  {
    const m = new THREE.Sprite(new THREE.SpriteMaterial({
      map: glow(0xffe8f0), color: 0xffcfe4, transparent: true,
      opacity: 0.95, fog: false, depthWrite: false,
    }));
    m.position.set(-700, 780, -900);
    m.scale.setScalar(220);
    group.add(m);
  }

  // --- Ground ----------------------------------------------------------
  const groundTex = groundTexture();
  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(2 * HALF + 40, 2 * HALF + 40),
    new THREE.MeshStandardMaterial({
      map: groundTex, emissiveMap: groundTex, emissive: 0xffffff,
      emissiveIntensity: 0.85, roughness: 0.9, metalness: 0.1,
    }),
  );
  ground.rotation.x = -Math.PI / 2;
  group.add(ground);

  // --- Buildings --------------------------------------------------------
  const winTex = [windowTexture(rand), windowTexture(rand), windowTexture(rand)];
  const buckets = [[], [], []];
  const edgeParts = [];
  const signSpots = [];   // faces available for signs

  const box = new THREE.BoxGeometry(1, 1, 1);
  const boxEdges = new THREE.EdgesGeometry(box);
  const half = (WORLD.blocks - 1) / 2;
  for (let bi = 0; bi < WORLD.blocks; bi++) {
    for (let bj = 0; bj < WORLD.blocks; bj++) {
      const cx = (bi - half) * PITCH, cz = (bj - half) * PITCH;
      if (rand() < 0.16) continue; // open plaza
      // Subdivide the lot into 1, 2 or 4 lots.
      const layout = rand();
      const lots = [];
      if (layout < 0.42) lots.push([cx, cz, WORLD.lot, WORLD.lot]);
      else if (layout < 0.62) {
        lots.push([cx - WORLD.lot / 4, cz, WORLD.lot / 2, WORLD.lot]);
        lots.push([cx + WORLD.lot / 4, cz, WORLD.lot / 2, WORLD.lot]);
      } else if (layout < 0.82) {
        lots.push([cx, cz - WORLD.lot / 4, WORLD.lot, WORLD.lot / 2]);
        lots.push([cx, cz + WORLD.lot / 4, WORLD.lot, WORLD.lot / 2]);
      } else {
        for (const sx of [-1, 1]) for (const sz of [-1, 1])
          lots.push([cx + sx * WORLD.lot / 4, cz + sz * WORLD.lot / 4, WORLD.lot / 2, WORLD.lot / 2]);
      }
      for (const [lx, lz, lw, ld] of lots) {
        if (rand() < 0.24) continue;
        const margin = 2.4 + rand() * 1.4;
        const w = lw - margin * 2 - rand() * 2;
        const d = ld - margin * 2 - rand() * 2;
        if (w < 6 || d < 6) continue;
        const h = 9 + Math.pow(rand(), 1.7) * 58;
        const x = lx + (rand() - 0.5) * (lw - w - margin * 2);
        const z = lz + (rand() - 0.5) * (ld - d - margin * 2);
        const mtx = new THREE.Matrix4()
          .makeScale(w, h, d)
          .setPosition(x, h / 2, z);
        buckets[(rand() * 3) | 0].push({
          geometry: box.clone(), matrix: mtx,
          uvScale: [w / 9, d / 9, h / 9],
        });
        edgeParts.push({
          geometry: boxEdges,
          matrix: mtx.clone(),
          color: NEON[(rand() * NEON.length) | 0],
        });
        colliders.push({ minX: x - w / 2, maxX: x + w / 2, minZ: z - d / 2, maxZ: z + d / 2 });
        if (rand() < 0.55) signSpots.push({ x, z, w, d, h });
      }
    }
  }

  const wallMat = (tex) => new THREE.MeshStandardMaterial({
    color: 0x8f9ab5, map: tex, emissiveMap: tex, emissive: 0xffffff,
    emissiveIntensity: 0.9, roughness: 0.55, metalness: 0.35,
  });
  for (let i = 0; i < 3; i++) {
    if (!buckets[i].length) continue;
    const mesh = new THREE.Mesh(mergeParts(buckets[i]), wallMat(winTex[i]));
    group.add(mesh);
  }
  group.add(new THREE.LineSegments(
    mergeEdges(edgeParts),
    new THREE.LineBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.85 }),
  ));

  // --- Neon signs --------------------------------------------------------
  const signs = [];
  const signCount = Math.min(signSpots.length, 64);
  for (let i = 0; i < signCount; i++) {
    const s = signSpots[(rand() * signSpots.length) | 0];
    const color = NEON[(rand() * NEON.length) | 0];
    const vertical = rand() < 0.45;
    const word = SIGN_WORDS[(rand() * SIGN_WORDS.length) | 0];
    const tex = signTexture(word, color, vertical);
    const pw = vertical ? 3.2 : 8 + rand() * 3;
    const ph = vertical ? 11 + rand() * 4 : 2.8;
    const mat = new THREE.MeshBasicMaterial({
      map: tex, transparent: true, side: THREE.DoubleSide,
      depthWrite: false, fog: true,
    });
    const plane = new THREE.Mesh(new THREE.PlaneGeometry(pw, ph), mat);
    const side = (rand() * 4) | 0;
    const y = Math.min(4 + rand() * 12, s.h - ph / 2 - 1);
    if (y < 3) continue;
    if (side === 0) { plane.position.set(s.x + (rand() - 0.5) * s.w * 0.7, y, s.z + s.d / 2 + 0.25); }
    else if (side === 1) { plane.position.set(s.x + (rand() - 0.5) * s.w * 0.7, y, s.z - s.d / 2 - 0.25); plane.rotation.y = Math.PI; }
    else if (side === 2) { plane.position.set(s.x + s.w / 2 + 0.25, y, s.z + (rand() - 0.5) * s.d * 0.7); plane.rotation.y = Math.PI / 2; }
    else { plane.position.set(s.x - s.w / 2 - 0.25, y, s.z + (rand() - 0.5) * s.d * 0.7); plane.rotation.y = -Math.PI / 2; }
    signs.push({ mat, seed: rand() * 10, speed: 6 + rand() * 10 });
    group.add(plane);
  }
  dynamic.push({
    update(t) {
      for (const s of signs) {
        const f = Math.sin(t * s.speed + s.seed) > -0.92 ? 1 : 0.25;
        s.mat.opacity = 0.92 * f;
      }
    },
  });

  // --- Torii gates over streets -----------------------------------------
  {
    const parts = [];
    const pillar = new THREE.CylinderGeometry(0.55, 0.7, 7.4, 10);
    const beam = new THREE.BoxGeometry(1, 1, 1);
    const inner = [2, 4, 7, 9, 11];
    for (const k of inner) {
      if (rand() < 0.25) continue;
      const sx = -HALF + WORLD.street / 2 + k * PITCH;
      const sz = (rand() - 0.5) * (HALF * 1.3);
      const off = WORLD.street / 2 - 1.1;
      for (const s of [-1, 1]) {
        parts.push({
          geometry: pillar.clone(),
          matrix: new THREE.Matrix4().setPosition(sx + s * off, 3.7, sz),
        });
        colliders.push({ minX: sx + s * off - 0.85, maxX: sx + s * off + 0.85, minZ: sz - 0.85, maxZ: sz + 0.85 });
      }
      const span = off * 2 + 3;
      parts.push({ geometry: beam.clone(), matrix: new THREE.Matrix4().makeScale(span, 0.7, 1.1).setPosition(sx, 7.5, sz) });
      parts.push({ geometry: beam.clone(), matrix: new THREE.Matrix4().makeScale(span * 0.82, 0.5, 0.9).setPosition(sx, 6.3, sz) });
    }
    const mat = new THREE.MeshStandardMaterial({
      color: 0xff2233, emissive: 0xff2233, emissiveIntensity: 0.75,
      roughness: 0.5, metalness: 0.2,
    });
    group.add(new THREE.Mesh(mergeParts(parts), mat));
  }

  // --- Plaza holo poles ---------------------------------------------------
  {
    const parts = [];
    const pole = new THREE.CylinderGeometry(0.22, 0.22, 9, 8, 1, true);
    for (let i = 0; i < 26; i++) {
      const p = freePoint(rand, 0, null, 0);
      if (!p) continue;
      parts.push({
        geometry: pole.clone(),
        matrix: new THREE.Matrix4().setPosition(p.x, 4.5, p.z),
      });
    }
    if (parts.length) {
      group.add(new THREE.Mesh(mergeParts(parts), new THREE.MeshBasicMaterial({
        color: 0x00ffc8, transparent: true, opacity: 0.3,
        blending: THREE.AdditiveBlending, side: THREE.DoubleSide, depthWrite: false,
      })));
    }
  }

  // --- Boundary walls -----------------------------------------------------
  {
    const tex = wallTexture();
    tex.repeat.set(30, 1);
    const mat = new THREE.MeshBasicMaterial({
      map: tex, transparent: true, opacity: 0.85, side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending, depthWrite: false,
    });
    const geo = new THREE.PlaneGeometry(2 * HALF + 2, WALL_HEIGHT);
    for (let i = 0; i < 4; i++) {
      const w = new THREE.Mesh(geo, mat);
      const a = (i * Math.PI) / 2;
      w.position.set(Math.sin(a) * HALF, WALL_HEIGHT / 2, Math.cos(a) * HALF);
      w.rotation.y = a + Math.PI;
      group.add(w);
    }
    const rim = new THREE.BufferGeometry();
    // Glowing rim: a line loop at the top of the walls.
    const rimPts = [
      [-HALF, -HALF], [HALF, -HALF], [HALF, HALF], [-HALF, HALF], [-HALF, -HALF],
    ].map(([x, z]) => new THREE.Vector3(x, WALL_HEIGHT, z));
    rim.setFromPoints(rimPts);
    group.add(new THREE.Line(rim, new THREE.LineBasicMaterial({ color: 0xff2d95 })));
  }

  // --- Rain ---------------------------------------------------------------
  {
    const n = 500, sp = [], vel = [];
    for (let i = 0; i < n; i++) {
      sp.push((rand() - 0.5) * 160, rand() * 60, (rand() - 0.5) * 160);
      vel.push(46 + rand() * 22);
    }
    const rg = new THREE.BufferGeometry();
    rg.setAttribute("position", new THREE.Float32BufferAttribute(sp, 3));
    const rain = new THREE.Points(rg, new THREE.PointsMaterial({
      color: 0x66bbff, size: 0.22, transparent: true, opacity: 0.55,
      blending: THREE.AdditiveBlending, depthWrite: false,
    }));
    group.add(rain);
    dynamic.push({
      update(t, dt, head) {
        rain.position.set(head.x, 0, head.z);
        const p = rg.attributes.position;
        for (let i = 0; i < n; i++) {
          let y = p.getY(i) - vel[i] * dt;
          if (y < 0) y += 60;
          p.setY(i, y);
        }
        p.needsUpdate = true;
      },
    });
  }

  scene.add(group);

  function isBlocked(x, z, r) {
    for (const c of colliders) {
      if (x > c.minX - r && x < c.maxX + r && z > c.minZ - r && z < c.maxZ + r)
        return true;
    }
    return false;
  }

  function freePoint(randFn, r, away, minDist) {
    const rf = randFn || Math.random;
    for (let tries = 0; tries < 80; tries++) {
      const x = (rf() * 2 - 1) * (HALF - 6);
      const z = (rf() * 2 - 1) * (HALF - 6);
      if (isBlocked(x, z, r + 2)) continue;
      if (away && Math.hypot(x - away.x, z - away.z) < minDist) continue;
      return { x, z };
    }
    return null;
  }

  return {
    group,
    colliders,
    /** Returns 'wall' | 'building' | null for a circle at (x, z, r). */
    hitTest(x, z, r) {
      if (Math.abs(x) > HALF - 1.4 - r || Math.abs(z) > HALF - 1.4 - r) return "wall";
      if (isBlocked(x, z, r)) return "building";
      return null;
    },
    isBlocked,
    freePoint,
    update(t, dt, headPos) {
      for (const d of dynamic) d.update(t, dt, headPos);
    },
  };
}
