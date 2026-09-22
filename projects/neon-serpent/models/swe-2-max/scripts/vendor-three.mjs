// Copies the three.js ESM build into app/vendor so the game runs with no
// bundler or network access. Run after `npm install` whenever three changes.
import { copyFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const out = path.join(root, "app", "vendor");
await mkdir(out, { recursive: true });

for (const file of ["three.module.js", "three.core.js"]) {
  await copyFile(
    path.join(root, "node_modules", "three", "build", file),
    path.join(out, file),
  );
}
await copyFile(
  path.join(root, "node_modules", "three", "LICENSE"),
  path.join(out, "LICENSE.three.txt"),
);
console.log("Vendored three.js into app/vendor/");
