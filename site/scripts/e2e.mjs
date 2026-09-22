import { cp, mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

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
  const env = {
    ...process.env,
    VARIORA_PROJECTS_DIR: path.join(temp, "projects"),
  };
  run("./catalog.mjs", [], env);
  run("@playwright/test/cli", ["test", "tests/browser/preview.spec.ts"], {
    ...env,
    VARIORA_E2E_SERVER: "dev",
  });
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
