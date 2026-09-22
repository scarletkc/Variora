import * as THREE from "./vendor/three.module.js";
import {
  BLOCKS,
  ROAD_CENTERS,
  WORLD_LIMIT,
  seededRandom,
} from "./simulation.mjs";

const AMBER = 0xff8044;
const CYAN = 0x67dfd0;

class Architecture {
  constructor(scene) {
    this.scene = scene;
    this.groups = new Map();
    this.cube = new THREE.BoxGeometry(1, 1, 1);
    this.dummy = new THREE.Object3D();
  }
  box(material, x, y, z, w, h, d, rotation = 0) {
    if (!this.groups.has(material)) this.groups.set(material, []);
    this.dummy.position.set(x, y, z);
    this.dummy.rotation.set(0, rotation, 0);
    this.dummy.scale.set(w, h, d);
    this.dummy.updateMatrix();
    this.groups.get(material).push(this.dummy.matrix.clone());
  }
  finish() {
    for (const [material, matrices] of this.groups) {
      const mesh = new THREE.InstancedMesh(
        this.cube,
        material,
        matrices.length,
      );
      matrices.forEach((matrix, i) => mesh.setMatrixAt(i, matrix));
      mesh.computeBoundingSphere();
      this.scene.add(mesh);
    }
  }
}

function textureCanvas(width, height, paint) {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  paint(canvas.getContext("2d"), width, height);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

function signTexture(text, color, vertical) {
  return textureCanvas(vertical ? 128 : 512, 256, (ctx, w, h) => {
    ctx.fillStyle = "#071517";
    ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = color;
    ctx.lineWidth = 3;
    ctx.strokeRect(7, 7, w - 14, h - 14);
    ctx.fillStyle = color;
    ctx.shadowColor = color;
    ctx.shadowBlur = 9;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    if (vertical) {
      const chars = [...text];
      ctx.font = `bold ${Math.min(62, 206 / chars.length)}px sans-serif`;
      chars.forEach((char, i) =>
        ctx.fillText(char, w / 2, 27 + ((i + 0.5) * 204) / chars.length),
      );
    } else {
      ctx.font = "bold 76px sans-serif";
      ctx.fillText(text, w / 2, 113, w - 35);
      ctx.shadowBlur = 0;
      ctx.font = "17px monospace";
      ctx.fillText("OPEN ALL NIGHT / 営業中", w / 2, 206);
      ctx.fillRect(35, 171, w - 70, 2);
    }
  });
}

export class CityView {
  constructor(canvas, reducedMotion) {
    this.reducedMotion = reducedMotion;
    this.renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: false,
      powerPreference: "high-performance",
    });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x101e28);
    this.scene.fog = new THREE.FogExp2(0x142b31, 0.014);
    this.camera = new THREE.PerspectiveCamera(77, 1, 0.08, 240);
    this.camera.rotation.order = "YXZ";
    this.camera.position.set(0, 1.6, 39);
    this.scene.add(new THREE.HemisphereLight(0xa5d5da, 0x21343c, 1.9));
    const moon = new THREE.DirectionalLight(0x92adce, 1.6);
    moon.position.set(-30, 70, -60);
    this.scene.add(moon);
    this.random = seededRandom(87453);
    this.makeCity();
    this.makeRain();
    this.makeSerpent();
    this.coreMeshes = [];
    this.makeCoreGeometry();
    this.sparks = [];
    this.makePost();
    this.resize();
  }

  makeCity() {
    const random = this.random;
    const lit = (color, intensity = 2.5) =>
      new THREE.MeshStandardMaterial({
        color,
        emissive: color,
        emissiveIntensity: intensity,
        roughness: 0.65,
      });
    const metal = new THREE.MeshStandardMaterial({
      color: 0x243339,
      roughness: 0.55,
      metalness: 0.65,
    });
    const dark = new THREE.MeshStandardMaterial({
      color: 0x14252d,
      roughness: 0.8,
    });
    const concrete = [0x2b3d46, 0x263740, 0x334149, 0x28333e].map(
      (color) => new THREE.MeshStandardMaterial({ color, roughness: 0.9 }),
    );
    const glass = new THREE.MeshStandardMaterial({
      color: 0x152d31,
      metalness: 0.75,
      roughness: 0.24,
    });
    const amber = lit(AMBER, 3.3),
      cyan = lit(CYAN, 2.4),
      red = lit(0xf05669, 2),
      white = lit(0xbdcfc2, 1.3);
    const windows = [
      lit(0x95c9bf, 0.65),
      lit(0x38757e, 0.35),
      lit(0xdda273, 0.75),
      glass,
    ];
    const arch = new Architecture(this.scene);
    const roadTexture = textureCanvas(512, 512, (ctx, w, h) => {
      ctx.fillStyle = "#39444a";
      ctx.fillRect(0, 0, w, h);
      for (let i = 0; i < 14000; i++) {
        const c = Math.floor(35 + random() * 55);
        ctx.fillStyle = `rgba(${c},${c + 7},${c + 10},${random() * 0.5})`;
        ctx.fillRect(random() * w, random() * h, 1 + random() * 7, 1);
      }
      for (let i = 0; i < 40; i++) {
        ctx.fillStyle = "#738e9133";
        ctx.beginPath();
        ctx.ellipse(
          random() * w,
          random() * h,
          random() * 80,
          random() * 12,
          random() * 3,
          0,
          Math.PI * 2,
        );
        ctx.fill();
      }
    });
    roadTexture.wrapS = roadTexture.wrapT = THREE.RepeatWrapping;
    roadTexture.repeat.set(22, 22);
    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(360, 360),
      new THREE.MeshStandardMaterial({
        map: roadTexture,
        color: 0x4b6065,
        roughness: 0.27,
        metalness: 0.65,
      }),
    );
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.04;
    this.scene.add(ground);

    this.glow = textureCanvas(128, 128, (ctx, w, h) => {
      const gradient = ctx.createRadialGradient(
        w / 2,
        h / 2,
        0,
        w / 2,
        h / 2,
        w / 2,
      );
      gradient.addColorStop(0, "#ffffffc0");
      gradient.addColorStop(0.16, "#ffffff80");
      gradient.addColorStop(0.5, "#ffffff20");
      gradient.addColorStop(1, "#ffffff00");
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, w, h);
    });
    const reflectionGeometry = new THREE.PlaneGeometry(1, 1);
    const reflectionMats = [AMBER, CYAN, 0xf05669].map(
      (color) =>
        new THREE.MeshBasicMaterial({
          map: this.glow,
          color,
          transparent: true,
          opacity: 0.48,
          blending: THREE.AdditiveBlending,
          depthWrite: false,
        }),
    );
    const reflection = (x, z, colorIndex, w = 5, h = 12) => {
      const mesh = new THREE.Mesh(
        reflectionGeometry,
        reflectionMats[colorIndex],
      );
      mesh.rotation.x = -Math.PI / 2;
      mesh.position.set(x, 0.018, z);
      mesh.scale.set(w, h, 1);
      this.scene.add(mesh);
    };

    const signCache = new Map();
    const sign = (
      text,
      color,
      x,
      y,
      z,
      width,
      height,
      rotation = 0,
      vertical = false,
    ) => {
      const key = `${text}${color}${vertical}`;
      if (!signCache.has(key))
        signCache.set(
          key,
          new THREE.MeshBasicMaterial({
            map: signTexture(text, color, vertical),
            color: 0xffffff,
          }),
        );
      const mesh = new THREE.Mesh(
        new THREE.PlaneGeometry(width, height),
        signCache.get(key),
      );
      mesh.position.set(x, y, z);
      mesh.rotation.y = rotation;
      this.scene.add(mesh);
    };
    const signs = [
      ["電脳", "#63e9d7"],
      ["ラーメン", "#ff8b56"],
      ["夜市", "#ff6885"],
      ["新宿", "#92f3df"],
      ["カラオケ", "#ffa077"],
      ["不夜城", "#61cddb"],
      ["ネオン", "#e5b975"],
      ["地下鉄", "#c1e7dd"],
    ];
    BLOCKS.forEach((block, bi) => {
      const { x, z, half } = block;
      const height = 15 + random() * 30;
      arch.box(concrete[bi % 4], x, height / 2, z, half * 2, height, half * 2);
      arch.box(metal, x, 0.14, z, 16.1, 0.28, 16.1);
      arch.box(dark, x, height + 0.3, z, 16.2, 0.6, 16.2);
      arch.box(metal, x + 3, height + 1.7, z - 2, 5, 2.8, 4);
      arch.box(metal, x - 4, height + 4, z + 2, 0.15, 8, 0.15);
      arch.box(red, x - 4, height + 8.1, z + 2, 0.24, 0.24, 0.24);
      for (let face = 0; face < 4; face++) {
        const rotation = (face * Math.PI) / 2;
        const local = (u, y, outward = half + 0.04) => ({
          x: x + Math.cos(rotation) * u + Math.sin(rotation) * outward,
          y,
          z: z - Math.sin(rotation) * u + Math.cos(rotation) * outward,
        });
        const faceBox = (
          mat,
          u,
          y,
          w,
          h,
          depth = 0.1,
          offset = half + 0.05,
        ) => {
          const p = local(u, y, offset);
          arch.box(mat, p.x, p.y, p.z, w, h, depth, rotation);
        };
        faceBox(dark, 0, 2.2, 15.4, 4.1);
        for (let u = -5.8; u < 7; u += 3.85) {
          faceBox(glass, u, 1.7, 3.3, 2.9, 0.12, half + 0.09);
          faceBox(metal, u, 1.7, 0.09, 3, 0.18, half + 0.19);
          faceBox(metal, u, 0.3, 3.4, 0.12, 0.18, half + 0.19);
        }
        faceBox(bi % 3 ? cyan : amber, 0, 3.8, 15.2, 0.07, 0.17, half + 0.2);
        for (let y = 6.2; y < height - 1; y += 3.3) {
          faceBox(metal, 0, y + 1.4, 15.5, 0.14);
          for (let u = -6.4; u < 7; u += 2.6) {
            faceBox(
              windows[Math.floor(random() * windows.length)],
              u,
              y,
              1.32,
              1.95,
            );
            if (random() > 0.78)
              faceBox(metal, u, y - 1.1, 1.5, 0.55, 0.8, half + 0.4);
          }
        }
        for (const u of [-7.3, 7.3])
          faceBox(metal, u, height / 2, 0.16, height, 0.3, half + 0.15);
        const entry = signs[(bi * 3 + face) % signs.length];
        let p = local(-1.2, 4.9, half + 0.13);
        sign(entry[0], entry[1], p.x, p.y, p.z, 6.4, 1.75, rotation);
        p = local(5.1, 8.6, half + 0.6);
        faceBox(dark, 5.1, 8.6, 1.8, 5.4, 0.4, half + 0.35);
        sign(
          signs[(bi + face + 3) % signs.length][0],
          entry[1],
          p.x,
          p.y,
          p.z,
          1.7,
          5.2,
          rotation,
          true,
        );
        const road = local(0, 0, half + 2.2);
        reflection(
          road.x,
          road.z,
          (bi + face) % 3,
          face % 2 ? 8 : 5,
          face % 2 ? 5 : 10,
        );
      }
    });

    for (const road of ROAD_CENTERS) {
      for (let d = -54; d <= 54; d += 6) {
        if (ROAD_CENTERS.every((c) => Math.abs(c - d) > 4.6)) {
          arch.box(white, road, 0.003, d, 0.08, 0.007, 1.8);
          arch.box(white, d, 0.003, road, 1.8, 0.007, 0.08);
        }
      }
      for (const intersection of ROAD_CENTERS) {
        for (let stripe = -3; stripe <= 3; stripe++) {
          arch.box(
            white,
            road + stripe * 0.85,
            0.005,
            intersection + 5.3,
            0.38,
            0.008,
            1.5,
          );
          arch.box(
            white,
            intersection - 5.3,
            0.005,
            road + stripe * 0.85,
            1.5,
            0.008,
            0.38,
          );
        }
      }
    }

    // The perimeter is a continuous visible barrier matching the collision plane.
    for (const rotation of [0, Math.PI / 2]) {
      for (const side of [-1, 1]) {
        if (rotation === 0) {
          arch.box(dark, 0, 1.2, side * (WORLD_LIMIT + 0.3), 116, 2.4, 0.6);
          arch.box(amber, 0, 2.5, side * WORLD_LIMIT, 116, 0.09, 0.09);
        } else {
          arch.box(dark, side * (WORLD_LIMIT + 0.3), 1.2, 0, 0.6, 2.4, 116);
          arch.box(amber, side * WORLD_LIMIT, 2.5, 0, 0.09, 0.09, 116);
        }
      }
    }
    for (let i = 0; i < 64; i++) {
      const angle = (i / 64) * Math.PI * 2;
      const radius = 85 + random() * 60;
      const x = Math.sin(angle) * radius,
        z = Math.cos(angle) * radius;
      const height = 20 + random() * 75;
      arch.box(
        concrete[i % 4],
        x,
        height / 2,
        z,
        9 + random() * 12,
        height,
        9 + random() * 12,
      );
      arch.box(i % 4 ? cyan : amber, x, height, z, 0.16, 1.5, 0.16);
      if (i % 3 === 0)
        arch.box(cyan, x, height * 0.65, z + 7, 0.16, height * 0.5, 0.16);
    }

    // Suspended infrastructure leaves the street-level collision map unobstructed.
    for (const z of [-24, 24]) {
      arch.box(metal, 0, 12, z, 114, 0.5, 1.4);
      arch.box(cyan, 0, 11.7, z + 0.7, 112, 0.04, 0.04);
      for (let x = -52; x <= 52; x += 8)
        arch.box(metal, x, 12.8, z, 0.15, 1.5, 0.12);
      arch.box(metal, 0, 13.5, z, 114, 0.15, 0.15);
    }
    sign("新宿区", "#ffa26a", 0, 8.4, -5.8, 7.6, 2.4);
    arch.box(metal, 0, 9.9, -6, 9, 0.2, 0.25);
    arch.box(metal, -4.3, 11, -6, 0.15, 2.3, 0.15);
    arch.box(metal, 4.3, 11, -6, 0.15, 2.3, 0.15);

    const wirePoints = [];
    for (let zi = -40; zi <= 40; zi += 18) {
      for (let wire = 0; wire < 3; wire++) {
        for (let j = 0; j < 20; j++) {
          for (const t of [j / 20, (j + 1) / 20])
            wirePoints.push(
              -9 + 18 * t,
              10 - Math.sin(t * Math.PI) * 1.8 + wire * 0.24,
              zi + wire * 0.4,
            );
        }
      }
    }
    const wireGeometry = new THREE.BufferGeometry();
    wireGeometry.setAttribute(
      "position",
      new THREE.Float32BufferAttribute(wirePoints, 3),
    );
    this.scene.add(
      new THREE.LineSegments(
        wireGeometry,
        new THREE.LineBasicMaterial({ color: 0x152025 }),
      ),
    );
    const lanternGeometry = new THREE.SphereGeometry(0.24, 10, 8);
    for (let i = -3; i <= 3; i++) {
      const lantern = new THREE.Mesh(lanternGeometry, amber);
      lantern.scale.y = 1.4;
      lantern.position.set(i, 6.4 - Math.cos(i * 0.4) * 0.6, 16);
      this.scene.add(lantern);
      arch.box(metal, i, lantern.position.y + 1.2, 16, 0.025, 1.8, 0.025);
    }
    for (const [x, z, color] of [
      [-3, 30, AMBER],
      [3, 7, CYAN],
      [0, -19, AMBER],
      [-23, 0, CYAN],
    ]) {
      const light = new THREE.PointLight(color, 30, 18, 2);
      light.position.set(x, 3, z);
      this.scene.add(light);
    }
    arch.finish();
  }

  makeRain() {
    const count = 1800;
    const positions = new Float32Array(count * 6);
    this.rainSeeds = new Float32Array(count * 4);
    for (let i = 0; i < count; i++) {
      this.rainSeeds.set(
        [
          (this.random() - 0.5) * 85,
          this.random() * 35,
          (this.random() - 0.5) * 85,
          0.25 + this.random() * 0.35,
        ],
        i * 4,
      );
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute(
      "position",
      new THREE.BufferAttribute(positions, 3).setUsage(THREE.DynamicDrawUsage),
    );
    this.rain = new THREE.LineSegments(
      geometry,
      new THREE.LineBasicMaterial({
        color: 0xa4c4c9,
        transparent: true,
        opacity: 0.18,
        depthWrite: false,
      }),
    );
    this.rain.frustumCulled = false;
    this.scene.add(this.rain);
  }

  makeSerpent() {
    this.body = new THREE.InstancedMesh(
      new THREE.IcosahedronGeometry(0.43, 1),
      new THREE.MeshStandardMaterial({
        color: 0x164c52,
        emissive: CYAN,
        emissiveIntensity: 0.45,
        metalness: 0.7,
        roughness: 0.3,
      }),
      2048,
    );
    this.spine = new THREE.InstancedMesh(
      new THREE.BoxGeometry(0.1, 0.06, 0.44),
      new THREE.MeshBasicMaterial({ color: 0x8dffe3 }),
      2048,
    );
    this.body.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    this.spine.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    this.body.frustumCulled = this.spine.frustumCulled = false;
    this.scene.add(this.body, this.spine);
    this.dummy = new THREE.Object3D();
    this.headLight = new THREE.PointLight(CYAN, 12, 8, 2);
    this.scene.add(this.headLight);
    this.cockpit = new THREE.Group();
    const hull = new THREE.MeshStandardMaterial({
      color: 0x193d40,
      emissive: 0x102d31,
      metalness: 0.85,
      roughness: 0.24,
    });
    const strip = new THREE.MeshBasicMaterial({ color: CYAN });
    for (const side of [-1, 1]) {
      const fin = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.12, 1.8), hull);
      fin.position.set(side * 0.56, -0.78, -1.16);
      fin.rotation.z = side * -0.22;
      fin.rotation.y = side * -0.17;
      this.cockpit.add(fin);
      const line = new THREE.Mesh(
        new THREE.BoxGeometry(0.035, 0.016, 1.5),
        strip,
      );
      line.position.set(side * 0.53, -0.704, -1.13);
      line.rotation.y = side * -0.17;
      this.cockpit.add(line);
    }
    this.camera.add(this.cockpit);
    this.scene.add(this.camera);
    this.cockpit.visible = false;
  }

  makeCoreGeometry() {
    this.coreGeo = new THREE.OctahedronGeometry(0.45);
    this.coreMat = new THREE.MeshStandardMaterial({
      color: 0xffd7a2,
      emissive: AMBER,
      emissiveIntensity: 4,
      metalness: 0.4,
      roughness: 0.2,
    });
    this.ringGeo = new THREE.TorusGeometry(0.86, 0.024, 6, 40);
    this.ringMat = new THREE.MeshBasicMaterial({ color: 0xffb56d });
    this.coreGroundMat = new THREE.MeshBasicMaterial({
      map: this.glow,
      color: AMBER,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      opacity: 0.7,
    });
  }

  makePost() {
    this.target = new THREE.WebGLRenderTarget(1, 1, {
      type: THREE.HalfFloatType,
    });
    this.target.samples = 4;
    this.bloomTarget = new THREE.WebGLRenderTarget(1, 1, {
      type: THREE.HalfFloatType,
      depthBuffer: false,
    });
    this.postScene = new THREE.Scene();
    this.postCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    this.bloomMaterial = new THREE.ShaderMaterial({
      uniforms: {
        sceneMap: { value: this.target.texture },
        resolution: { value: new THREE.Vector2(1, 1) },
      },
      vertexShader:
        "varying vec2 vUv; void main(){vUv=uv;gl_Position=vec4(position.xy,0.,1.);}",
      fragmentShader: `
        uniform sampler2D sceneMap;
        uniform vec2 resolution;
        varying vec2 vUv;
        void main() {
          vec3 color = vec3(0.);
          float total = 0.;
          for (int i = -5; i <= 5; i++) {
            float weight = exp(-float(i*i) / 10.);
            vec3 sampleColor = texture2D(sceneMap, vUv + vec2(float(i) * 2.5 / resolution.x, 0.)).rgb;
            color += max(sampleColor - .85, 0.) * weight;
            total += weight;
          }
          gl_FragColor = vec4(color / total, 1.);
        }
      `,
      depthTest: false,
      depthWrite: false,
    });
    this.postMaterial = new THREE.ShaderMaterial({
      uniforms: {
        sceneMap: { value: this.target.texture },
        bloomMap: { value: this.bloomTarget.texture },
        resolution: { value: new THREE.Vector2(1, 1) },
        boost: { value: 0 },
      },
      vertexShader:
        "varying vec2 vUv; void main(){vUv=uv;gl_Position=vec4(position.xy,0.,1.);}",
      fragmentShader: `
        uniform sampler2D sceneMap;
        uniform sampler2D bloomMap;
        uniform vec2 resolution;
        uniform float boost;
        varying vec2 vUv;
        void main() {
          vec3 color = texture2D(sceneMap, vUv).rgb;
          vec3 bloom = vec3(0.);
          float total = 0.;
          for (int i = -5; i <= 5; i++) {
            float weight = exp(-float(i*i) / 10.);
            bloom += texture2D(bloomMap, vUv + vec2(0., float(i) * 2.5 / resolution.y)).rgb * weight;
            total += weight;
          }
          color += bloom / total * .8;
          vec2 p = vUv * 2. - 1.;
          color *= 1. - dot(p,p) * .14;
          color += vec3(.015, .045, .039) * boost * pow(length(p) * .65, 3.);
          color = (color * (2.51 * color + .03)) / (color * (2.43 * color + .59) + .14);
          color = pow(clamp(color, 0., 1.), vec3(1. / 2.2));
          gl_FragColor = vec4(color, 1.);
        }
      `,
      depthTest: false,
      depthWrite: false,
    });
    this.postQuad = new THREE.Mesh(
      new THREE.PlaneGeometry(2, 2),
      this.postMaterial,
    );
    this.postScene.add(this.postQuad);
  }

  resize() {
    const width = this.renderer.domElement.clientWidth,
      height = this.renderer.domElement.clientHeight;
    this.renderer.setSize(width, height, false);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    const resolution = new THREE.Vector2();
    this.renderer.getDrawingBufferSize(resolution);
    this.target.setSize(resolution.x, resolution.y);
    resolution.multiplyScalar(0.5).floor();
    this.bloomTarget.setSize(resolution.x, resolution.y);
    this.postMaterial.uniforms.resolution.value.copy(resolution);
    this.bloomMaterial.uniforms.resolution.value.copy(resolution);
  }

  collect(x, z) {
    const vertices = new Float32Array(54);
    const velocities = [];
    for (let i = 0; i < 18; i++) {
      vertices.set([x, 1.1, z], i * 3);
      velocities.push(
        new THREE.Vector3(
          (this.random() - 0.5) * 7,
          this.random() * 4,
          (this.random() - 0.5) * 7,
        ),
      );
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(vertices, 3));
    const material = new THREE.PointsMaterial({
      map: this.glow,
      color: AMBER,
      size: 0.09,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const points = new THREE.Points(geometry, material);
    this.scene.add(points);
    this.sparks.push({ points, velocities, life: 1 });
  }

  render(sim, state, time, dt, steer) {
    const playing = state === "playing";
    const intro = state === "intro";
    const sway = this.reducedMotion ? 0 : Math.sin(time * 0.22) * 0.055;
    this.camera.position.set(
      sim.x,
      1.48 +
        (playing && !this.reducedMotion
          ? Math.sin(sim.distance * 1.1) * 0.018
          : 0),
      sim.z,
    );
    this.camera.rotation.set(
      intro ? 0.065 : -0.025,
      -sim.heading + (intro ? sway - 0.08 : 0),
      playing && !this.reducedMotion ? -steer * 0.026 : 0,
    );
    const fov = sim.boosting && playing && !this.reducedMotion ? 85 : 77;
    if (Math.abs(this.camera.fov - fov) > 0.01) {
      this.camera.fov += (fov - this.camera.fov) * Math.min(dt * 5, 1);
      this.camera.updateProjectionMatrix();
    }
    this.cockpit.visible = !intro;
    this.headLight.position.set(sim.x, 1.4, sim.z);
    const body = sim.bodyPoints();
    this.body.count = this.spine.count = Math.min(body.length, 2048);
    body.slice(0, 2048).forEach((point, i) => {
      const next = i ? body[i - 1] : sim;
      this.dummy.position.set(point.x, 0.47, point.z);
      this.dummy.rotation.set(
        0,
        Math.atan2(next.x - point.x, next.z - point.z),
        0,
      );
      this.dummy.scale.setScalar(1 - Math.max(0, i / body.length - 0.75) * 2.2);
      this.dummy.updateMatrix();
      this.body.setMatrixAt(i, this.dummy.matrix);
      this.dummy.position.y = 0.86;
      this.dummy.updateMatrix();
      this.spine.setMatrixAt(i, this.dummy.matrix);
    });
    this.body.instanceMatrix.needsUpdate =
      this.spine.instanceMatrix.needsUpdate = true;
    while (this.coreMeshes.length < sim.cores.length) {
      const group = new THREE.Group();
      group.add(new THREE.Mesh(this.coreGeo, this.coreMat));
      const ring = new THREE.Mesh(this.ringGeo, this.ringMat);
      group.add(ring);
      const foot = new THREE.Mesh(
        new THREE.PlaneGeometry(4, 4),
        this.coreGroundMat,
      );
      foot.rotation.x = -Math.PI / 2;
      group.add(foot);
      const halo = new THREE.Sprite(
        new THREE.SpriteMaterial({
          map: this.glow,
          color: AMBER,
          transparent: true,
          blending: THREE.AdditiveBlending,
          opacity: 0.65,
          depthWrite: false,
        }),
      );
      halo.scale.setScalar(3);
      group.add(halo);
      this.coreMeshes.push(group);
      this.scene.add(group);
    }
    this.coreMeshes.forEach((group, i) => {
      group.visible = i < sim.cores.length;
      if (!group.visible) return;
      const core = sim.cores[i];
      group.position.set(core.x, 0, core.z);
      const y = 1.1 + (this.reducedMotion ? 0 : Math.sin(time * 2 + i) * 0.12);
      group.children[0].position.y = y;
      group.children[0].rotation.set(time * 0.4, time * 0.8, 0.2);
      group.children[1].position.y = y;
      group.children[1].rotation.set(0, time * 0.6 + i, 0.4);
      group.children[2].position.y = 0.025;
      group.children[3].position.y = y;
    });
    const positions = this.rain.geometry.attributes.position;
    for (let i = 0; i < this.rainSeeds.length / 4; i++) {
      const base = i * 4,
        out = i * 6;
      const x = sim.x + this.rainSeeds[base],
        z = sim.z + this.rainSeeds[base + 2];
      const y =
        (this.rainSeeds[base + 1] -
          ((this.reducedMotion ? 0 : time * 12) % 35) +
          35) %
        35;
      positions.array.set(
        [x, y, z, x - 0.05, y + this.rainSeeds[base + 3], z + 0.04],
        out,
      );
    }
    positions.needsUpdate = true;
    for (let i = this.sparks.length - 1; i >= 0; i--) {
      const spark = this.sparks[i];
      spark.life -= dt;
      if (spark.life <= 0) {
        this.scene.remove(spark.points);
        spark.points.geometry.dispose();
        spark.points.material.dispose();
        this.sparks.splice(i, 1);
        continue;
      }
      const points = spark.points.geometry.attributes.position;
      spark.velocities.forEach((v, j) => {
        v.y -= dt * 6;
        points.array[j * 3] += v.x * dt;
        points.array[j * 3 + 1] += v.y * dt;
        points.array[j * 3 + 2] += v.z * dt;
      });
      points.needsUpdate = true;
      spark.points.material.opacity = spark.life;
    }
    this.postMaterial.uniforms.boost.value = playing && sim.boosting ? 1 : 0;
    this.renderer.setRenderTarget(this.target);
    this.renderer.render(this.scene, this.camera);
    this.postQuad.material = this.bloomMaterial;
    this.renderer.setRenderTarget(this.bloomTarget);
    this.renderer.render(this.postScene, this.postCamera);
    this.postQuad.material = this.postMaterial;
    this.renderer.setRenderTarget(null);
    this.renderer.render(this.postScene, this.postCamera);
  }
}
