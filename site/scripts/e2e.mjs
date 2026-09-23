import { cp, mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { melody, wav } from "../tests/fixtures.mjs";

const site = fileURLToPath(new URL("..", import.meta.url));
const temp = await mkdtemp(path.join(tmpdir(), "variora-e2e-"));
function run(module, args, env = process.env) {
  const result = spawnSync(
    process.execPath,
    [fileURLToPath(import.meta.resolve(module)), ...args],
    { cwd: site, stdio: "inherit", env },
  );
  if (result.status !== 0)
    throw new Error(`${module} exited with ${result.status}`);
}
try {
  await cp(path.resolve(site, "../projects"), path.join(temp, "projects"), {
    recursive: true,
  });
  const model = path.join(temp, "projects/rainy-ramen/models/e2e-fixture");
  await mkdir(path.join(model, "app"), { recursive: true });
  await writeFile(
    path.join(model, "README.md"),
    "# Preview fixture\n\n| Field | Value |\n| --- | --- |\n| Model | E2E fixture |\n| Provider | Test |\n| Harness | Playwright |\n",
  );
  await writeFile(
    path.join(model, "app/index.html"),
    '<!doctype html><html lang="en"><title>Preview fixture</title><body><button id="counter">Count: 0</button><p id="isolation"></p><script type="module" src="./main.js"></script></body></html>',
  );
  await writeFile(
    path.join(model, "app/main.js"),
    'import {bindCounter} from "./counter.mjs";bindCounter();try{parent.document.body;document.querySelector("#isolation").textContent="Parent accessible"}catch{document.querySelector("#isolation").textContent="Parent isolated"}',
  );
  await writeFile(
    path.join(model, "app/counter.mjs"),
    'export function bindCounter(){let count=0;document.querySelector("#counter").onclick=e=>e.target.textContent="Count: "+(++count)}',
  );
  await writeFile(
    path.join(model, "app/classic.html"),
    '<!doctype html><html lang="en"><title>Classic fixture</title><body><p id="ready"></p><script src="./classic.js"></script></body></html>',
  );
  await writeFile(
    path.join(model, "app/classic.js"),
    'document.querySelector("#ready").textContent="Ready"',
  );
  await cp(model, path.join(temp, "projects/neon-serpent/models/e2e-fixture"), {
    recursive: true,
  });
  await cp(
    model,
    path.join(temp, "projects/neon-serpent/models/e2e-fixture-2"),
    {
      recursive: true,
    },
  );
  const music = path.join(temp, "projects/e2e-music");
  const files = {
    "PROMPT.md": "# Music fixture\n\nCompose a short tune.\n",
    "README.md": "# Music fixture\n",
    "site.json": '{ "category": "music" }\n',
  };
  for (const [id, name, output, assets] of [
    [
      "tone-a",
      "Tone A",
      {
        audio: "app/tone-a.wav",
        midi: "app/tone-a.mid",
        source: ["app/compose.py"],
        rendering: "Rendered by a test sine generator.",
      },
      {
        "app/tone-a.wav": wav(12, 440),
        "app/tone-a.mid": melody([60, 64, 67, 72]),
        "app/compose.py": "print('tone a')\n",
      },
    ],
    [
      "tone-b",
      "Tone B",
      {
        audio: { path: "render/tone-b.wav", origin: "contributor" },
        midi: "app/tone-b.mid",
      },
      {
        "render/tone-b.wav": wav(12, 660),
        "app/tone-b.mid": melody([67, 64, 60], 73),
      },
    ],
    [
      "midi-only",
      "MIDI only",
      { midi: "app/theme.mid" },
      { "app/theme.mid": melody([72, 71, 69]) },
    ],
    [
      "broken-audio",
      "Broken audio",
      { audio: "app/broken.wav" },
      { "app/broken.wav": "not audio" },
    ],
  ]) {
    Object.assign(files, {
      [`models/${id}/README.md`]: `# ${name}\n\n| Field | Value |\n| --- | --- |\n| Model | ${name} |\n| Provider | Test |\n| Harness | Playwright |\n`,
      [`models/${id}/output.json`]: JSON.stringify({
        type: "music",
        ...output,
      }),
      ...Object.fromEntries(
        Object.entries(assets).map(([file, content]) => [
          `models/${id}/${file}`,
          content,
        ]),
      ),
    });
  }
  for (const [file, content] of Object.entries(files)) {
    await mkdir(path.dirname(path.join(music, file)), { recursive: true });
    await writeFile(path.join(music, file), content);
  }
  const env = {
    ...process.env,
    VARIORA_PROJECTS_DIR: path.join(temp, "projects"),
  };
  run("./catalog.mjs", [], env);
  run(
    "@playwright/test/cli",
    ["test", "tests/browser/preview.spec.ts", "tests/browser/listen.spec.ts"],
    { ...env, VARIORA_E2E_SERVER: "dev" },
  );
  run("next/dist/bin/next", ["build"], env);
  run("@playwright/test/cli", ["test"], {
    ...env,
    VARIORA_E2E_SERVER: "static",
  });
} finally {
  // A fixture build must never be the artifact subsequently deployed.
  try {
    if (process.env.VARIORA_E2E_RESTORE_CATALOG !== "false") {
      run("./catalog.mjs", []);
    }
  } finally {
    await rm(path.join(site, "out"), { recursive: true, force: true });
    await rm(temp, { recursive: true, force: true });
  }
}
