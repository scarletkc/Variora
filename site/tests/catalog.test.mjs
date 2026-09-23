import { test } from "node:test";
import assert from "node:assert/strict";
import {
  access,
  mkdir,
  mkdtemp,
  readFile,
  symlink,
  rm,
  writeFile,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { buildCatalog } from "../scripts/catalog.mjs";
import { melody } from "./fixtures.mjs";

async function fixture(t, files) {
  const root = await mkdtemp(path.join(tmpdir(), "variora-catalog-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  for (const [name, content] of Object.entries(files)) {
    await mkdir(path.dirname(path.join(root, name)), { recursive: true });
    await writeFile(path.join(root, name), content);
  }
  return {
    root,
    projects: path.join(root, "projects"),
    public: path.join(root, "public"),
  };
}
const base = {
  "projects/example/PROMPT.md": "# Example\n\nMake a scene.",
  "projects/example/README.md": "# Example project",
};
test("discovers projects without implementations and uses the prompt as fallback", async (t) => {
  const f = await fixture(t, base);
  const [project] = await buildCatalog(f.projects, f.public);
  assert.equal(project.title, "Example project");
  assert.equal(project.description, "Make a scene.");
  assert.deepEqual(project.models, []);
});

test("chooses representative screenshots deterministically and copies original bytes", async (t) => {
  const f = await fixture(t, {
    ...base,
    "projects/example/models/demo/screenshots/desktop.png": "desktop",
    "projects/example/models/demo/screenshots/illustration.png":
      "original capture",
    "projects/example/models/demo/screenshots/scene.png": "scene",
  });
  const [project] = await buildCatalog(f.projects, f.public);
  assert.equal(
    project.models[0].screenshot,
    "/previews/_comparisons/example/demo/screenshot.png",
  );
  assert.equal(
    await readFile(path.join(f.public, project.models[0].screenshot), "utf8"),
    "original capture",
  );
});

test("supports explicit screenshot choices and disabling automatic selection", async (t) => {
  const f = await fixture(t, {
    ...base,
    "projects/example/models/demo/comparison.json":
      '{"screenshot":"captures/a b.webp"}',
    "projects/example/models/demo/captures/a b.webp": "chosen",
    "projects/example/models/disabled/comparison.json": '{"screenshot":null}',
    "projects/example/models/disabled/screenshots/preview.png": "disabled",
  });
  const [project] = await buildCatalog(f.projects, f.public);
  assert.equal(
    project.models[0].screenshot,
    "/previews/_comparisons/example/demo/screenshot.webp",
  );
  assert.equal(project.models[1].screenshot, null);
});

for (const screenshot of [
  "../../PROMPT.md",
  "screenshots/active.svg",
  "screenshots/missing.png",
  "screenshots",
  42,
  undefined,
]) {
  test(`rejects invalid comparison image: ${screenshot}`, async (t) => {
    const f = await fixture(t, {
      ...base,
      "projects/example/models/demo/comparison.json": JSON.stringify({
        screenshot,
      }),
      "projects/example/models/demo/screenshots/active.svg": "<svg/>",
    });
    await assert.rejects(buildCatalog(f.projects, f.public));
  });
}

test("rejects screenshot symlinks outside the submitting model", async (t) => {
  const f = await fixture(t, {
    ...base,
    "projects/example/models/demo/README.md": "# Demo",
    "outside/scene.png": "outside",
  });
  await symlink(
    path.join(f.root, "outside"),
    path.join(f.projects, "example/models/demo/screenshots"),
    "junction",
  );
  await assert.rejects(buildCatalog(f.projects, f.public), /symlink escapes/);
});
test("copies relative assets, parses model records, and excludes local config", async (t) => {
  const f = await fixture(t, {
    ...base,
    "projects/example/models/demo/README.md":
      "# Demo\n| Model | **model-1** |\n| Provider | [Vendor](https://example.com) |\n| Reasoning effort | `Max` |\n| Harness | CLI |",
    "projects/example/models/demo/app/index.html":
      '<script src="assets/main.js"></script>',
    "projects/example/models/demo/app/assets/main.js": "console.log('works')",
    "projects/example/models/demo/app/.env": "SECRET=private",
    "projects/example/models/demo/app/node_modules/package/index.js":
      "not shipped",
  });
  const [project] = await buildCatalog(f.projects, f.public);
  assert.deepEqual(project.models[0], {
    id: "demo",
    name: "model-1",
    provider: "Vendor",
    reasoning: "Max",
    harness: "CLI",
    firstCommittedAt: null,
    author: null,
    commit: null,
    preview: "/previews/example/demo/index.html",
    screenshot: null,
    output: null,
  });
  assert.match(
    await readFile(
      path.join(f.public, "previews/example/demo/assets/main.js"),
      "utf8",
    ),
    /works/,
  );
  await assert.rejects(
    access(path.join(f.public, "previews/example/demo/.env")),
  );
  await assert.rejects(
    access(path.join(f.public, "previews/example/demo/node_modules")),
  );
});
test("keeps source-only models visible when no static entry exists", async (t) => {
  const f = await fixture(t, {
    ...base,
    "projects/example/models/demo/README.md": "# Source model",
  });
  const [project] = await buildCatalog(f.projects, f.public);
  assert.equal(project.models[0].name, "Source model");
  assert.equal(project.models[0].preview, null);
  assert.equal(project.models[0].reasoning, "");
});
test("supports an explicit prebuilt directory and nested entry", async (t) => {
  const f = await fixture(t, {
    ...base,
    "projects/example/models/demo/preview.json":
      '{"directory":"app/dist","entry":"nested/start.html"}',
    "projects/example/models/demo/app/dist/nested/start.html": "<h1>Ready</h1>",
  });
  const [project] = await buildCatalog(f.projects, f.public);
  assert.equal(
    project.models[0].preview,
    "/previews/example/demo/nested/start.html",
  );
});
for (const config of [
  { directory: "../../..", entry: "index.html" },
  { directory: "app", entry: "../../README.md" },
]) {
  test(`rejects escaped preview paths: ${JSON.stringify(config)}`, async (t) => {
    const f = await fixture(t, {
      ...base,
      "projects/example/models/demo/preview.json": JSON.stringify(config),
      "projects/example/models/demo/app/index.html": "ok",
    });
    await assert.rejects(buildCatalog(f.projects, f.public), /escapes/);
  });
}
test("explicit invalid entries fail the build and stale assets are removed", async (t) => {
  const f = await fixture(t, {
    ...base,
    "projects/example/models/demo/preview.json":
      '{"directory":"app","entry":"missing.html"}',
    "projects/example/models/demo/app/index.html": "ok",
    "public/previews/old/index.html": "stale",
  });
  await assert.rejects(buildCatalog(f.projects, f.public), /ENOENT/);
  await assert.rejects(access(path.join(f.public, "previews/old/index.html")));
});
test("publishes music outputs with origins, MIDI details, and source links", async (t) => {
  const f = await fixture(t, {
    ...base,
    "projects/example/models/demo/output.json": JSON.stringify({
      type: "music",
      audio: { path: "renders/walk mix.mp3", origin: "contributor" },
      midi: "app/walk.mid",
      source: ["app/compose.py", "app/lib/"],
      rendering: "  FluidSynth 2.4, GeneralUser GS 2.0.  ",
    }),
    "projects/example/models/demo/renders/walk mix.mp3": "mp3 bytes",
    "projects/example/models/demo/app/walk.mid": melody([60, 64, 67], 73),
    "projects/example/models/demo/app/compose.py": "print('compose')",
    "projects/example/models/demo/app/lib/notes.py": "C = 60",
  });
  const [project] = await buildCatalog(f.projects, f.public);
  const { output } = project.models[0];
  assert.deepEqual(output.audio, {
    path: "renders/walk mix.mp3",
    name: "walk mix.mp3",
    url: "/previews/_outputs/example/demo/renders/walk%20mix.mp3",
    origin: "contributor",
    format: "MP3",
    type: "audio/mpeg",
  });
  assert.equal(output.midi.url, "/previews/_outputs/example/demo/app/walk.mid");
  assert.equal(output.midi.origin, "model");
  assert.equal(output.midi.summary.notes, 3);
  assert.equal(output.midi.summary.duration, 1.5);
  assert.deepEqual(output.midi.summary.instruments, ["Flute"]);
  assert.equal(output.midi.roll, "/previews/_outputs/example/demo/roll.svg");
  assert.deepEqual(output.source, [
    { path: "app/compose.py", directory: false, origin: "model" },
    { path: "app/lib", directory: true, origin: "model" },
  ]);
  assert.equal(output.rendering, "FluidSynth 2.4, GeneralUser GS 2.0.");
  assert.equal(
    await readFile(
      path.join(
        f.public,
        "previews/_outputs/example/demo/renders/walk mix.mp3",
      ),
      "utf8",
    ),
    "mp3 bytes",
  );
  assert.match(
    await readFile(
      path.join(f.public, "previews/_outputs/example/demo/roll.svg"),
      "utf8",
    ),
    /^<svg /,
  );
  await assert.rejects(
    access(
      path.join(f.public, "previews/_outputs/example/demo/app/compose.py"),
    ),
  );
});

test("keeps unreadable MIDI downloadable without derived details", async (t) => {
  const f = await fixture(t, {
    ...base,
    "projects/example/models/demo/output.json":
      '{"type":"music","midi":"song.midi"}',
    "projects/example/models/demo/song.midi": "not midi",
  });
  const [project] = await buildCatalog(f.projects, f.public);
  const { midi, audio } = project.models[0].output;
  assert.equal(audio, null);
  assert.equal(midi.summary, null);
  assert.equal(midi.roll, null);
  assert.equal(
    await readFile(
      path.join(f.public, "previews/_outputs/example/demo/song.midi"),
      "utf8",
    ),
    "not midi",
  );
});

test("publishes MIDI files used by browser previews", async (t) => {
  const f = await fixture(t, {
    ...base,
    "projects/example/models/demo/app/index.html": "<h1>Player</h1>",
    "projects/example/models/demo/app/theme.mid": melody([60]),
  });
  await buildCatalog(f.projects, f.public);
  await access(path.join(f.public, "previews/example/demo/theme.mid"));
});

for (const [name, config, files, error] of [
  ["invalid JSON", "{", {}, /output\.json: invalid JSON/],
  ["unknown type", { type: "text" }, {}, /unsupported output type "text"/],
  [
    "unknown field",
    { type: "music", audios: "a.mp3" },
    {},
    /unknown field "audios"/,
  ],
  ["no files", { type: "music" }, {}, /at least one/],
  [
    "missing audio",
    { type: "music", audio: "missing.mp3" },
    {},
    /audio not found: missing\.mp3/,
  ],
  [
    "unsupported audio",
    { type: "music", audio: "song.aiff" },
    { "song.aiff": "x" },
    /audio must be a/,
  ],
  [
    "audio directory",
    { type: "music", audio: "app" },
    { "app/a.txt": "x" },
    /audio must be a/,
  ],
  [
    "wrong MIDI extension",
    { type: "music", midi: "song.txt" },
    { "song.txt": "x" },
    /midi must be a \.mid or \.midi file/,
  ],
  [
    "escaping source",
    { type: "music", source: "../../PROMPT.md" },
    {},
    /source: Path escapes/,
  ],
  [
    "absolute source",
    { type: "music", source: "/etc/passwd" },
    {},
    /source: Path must be relative/,
  ],
  [
    "unknown origin",
    { type: "music", midi: { path: "a.mid", origin: "human" } },
    { "a.mid": "x" },
    /midi origin must be/,
  ],
  [
    "non-string rendering",
    { type: "music", midi: "a.mid", rendering: 3 },
    { "a.mid": "x" },
    /rendering must be a string/,
  ],
]) {
  test(`rejects invalid music output: ${name}`, async (t) => {
    const f = await fixture(t, {
      ...base,
      "projects/example/models/demo/output.json":
        typeof config === "string" ? config : JSON.stringify(config),
      ...Object.fromEntries(
        Object.entries(files).map(([file, content]) => [
          `projects/example/models/demo/${file}`,
          content,
        ]),
      ),
    });
    await assert.rejects(buildCatalog(f.projects, f.public), error);
  });
}

test("rejects entries that the publishing allowlist would exclude", async (t) => {
  const f = await fixture(t, {
    ...base,
    "projects/example/models/demo/preview.json":
      '{"directory":"app","entry":".private/index.html"}',
    "projects/example/models/demo/app/.private/index.html": "private",
  });
  await assert.rejects(
    buildCatalog(f.projects, f.public),
    /excluded by the asset rules/,
  );
});
