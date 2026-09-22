import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, cp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { buildCatalog } from "../../../../../site/scripts/catalog.mjs";

test("the catalog discovers this model and preserves its offline entry and license", async () => {
  const temporary = await mkdtemp(path.join(tmpdir(), "variora-neon-catalog-"));
  const project = path.join(temporary, "projects", "neon-serpent");
  const model = path.join(project, "models", "gpt-6-astra-xhigh");
  const source = fileURLToPath(new URL("../", import.meta.url));
  try {
    await mkdir(model, { recursive: true });
    for (const file of ["PROMPT.md", "README.md", "site.json"]) {
      await cp(
        new URL(`../../../${file}`, import.meta.url),
        path.join(project, file),
      );
    }
    await cp(path.join(source, "README.md"), path.join(model, "README.md"));
    await cp(path.join(source, "app"), path.join(model, "app"), {
      recursive: true,
    });
    const publicRoot = path.join(temporary, "public");
    const catalog = await buildCatalog(
      path.join(temporary, "projects"),
      publicRoot,
    );
    assert.equal(catalog.length, 1);
    assert.equal(catalog[0].models.length, 1);
    assert.equal(catalog[0].models[0].name, "gpt-6-astra");
    assert.equal(catalog[0].models[0].reasoning, "xhigh");
    assert.equal(
      catalog[0].models[0].preview,
      "/previews/neon-serpent/gpt-6-astra-xhigh/index.html",
    );
    const preview = path.join(
      publicRoot,
      "previews",
      "neon-serpent",
      "gpt-6-astra-xhigh",
    );
    for (const asset of [
      "index.html",
      "style.css",
      "bundle.js",
      "third-party.html",
    ]) {
      assert.deepEqual(
        await readFile(path.join(preview, asset)),
        await readFile(path.join(source, "app", asset)),
      );
    }
    assert.match(
      await readFile(path.join(preview, "index.html"), "utf8"),
      /<script defer src="\.\/bundle\.js"><\/script>/,
    );
  } finally {
    assert.equal(path.dirname(path.resolve(temporary)), path.resolve(tmpdir()));
    assert.ok(path.basename(temporary).startsWith("variora-neon-catalog-"));
    await rm(temporary, { recursive: true, force: true });
  }
});
