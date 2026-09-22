import { test } from "node:test";
import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { promisify } from "node:util";
import { createProvenanceReader } from "../scripts/provenance.mjs";

const exec = promisify(execFile);
async function fixture(t, email = "123+original@users.noreply.github.com") {
  const root = await mkdtemp(path.join(tmpdir(), "variora-provenance-"));
  t.after(() =>
    rm(root, { recursive: true, force: true, maxRetries: 3, retryDelay: 100 }),
  );
  const model = path.join(root, "projects/example/models/demo");
  await mkdir(model, { recursive: true });
  const env = {
    ...process.env,
    GIT_AUTHOR_NAME: "Original author",
    GIT_AUTHOR_EMAIL: email,
    GIT_COMMITTER_NAME: "Merge bot",
    GIT_COMMITTER_EMAIL: "bot@example.com",
    GIT_AUTHOR_DATE: "2026-09-20T23:30:00-07:00",
    GIT_COMMITTER_DATE: "2026-09-21T12:00:00Z",
  };
  const git = async (...args) =>
    (await exec("git", ["-C", root, ...args], { env })).stdout.trim();
  await git("init");
  await writeFile(path.join(model, "README.md"), "# Model");
  await git("add", ".");
  await git("-c", "commit.gpgsign=false", "commit", "-m", "Add model");
  return { root, model, git, commit: await git("rev-parse", "HEAD") };
}

test("retains the first addition's date and author after later edits and additions", async (t) => {
  const f = await fixture(t);
  await writeFile(path.join(f.model, "README.md"), "# Updated");
  await writeFile(path.join(f.model, "new.html"), "new");
  await f.git("add", ".");
  await f.git(
    "-c",
    "commit.gpgsign=false",
    "commit",
    "--author=Editor <editor@example.com>",
    "-m",
    "Edit model",
  );
  const read = createProvenanceReader({
    fetchImpl: () => {
      throw new Error("Unexpected request");
    },
  });
  assert.deepEqual(await read(f.model), {
    firstCommittedAt: "2026-09-20T23:30:00-07:00",
    author: { name: "Original author", login: "original" },
    commit: f.commit,
  });
  const untracked = path.join(f.root, "untracked");
  await mkdir(untracked);
  assert.equal((await read(untracked)).firstCommittedAt, null);
});

test("resolves the GitHub author rather than committer and caches requests", async (t) => {
  const f = await fixture(t, "person@example.com");
  let requests = 0;
  const read = createProvenanceReader({
    fetchImpl: async (url) => {
      requests++;
      assert.ok(url.endsWith(`/commits/${f.commit}`));
      return {
        ok: true,
        json: async () => ({
          author: { login: "contributor" },
          committer: { login: "web-flow" },
        }),
      };
    },
  });
  assert.deepEqual((await read(f.model)).author, {
    name: "Original author",
    login: "contributor",
  });
  await read(f.model);
  assert.equal(requests, 1);
});

for (const response of [
  { ok: true, json: async () => ({ author: null }) },
  { ok: false, status: 403 },
]) {
  test(`keeps the Git author name when GitHub cannot resolve it (${response.status ?? "unlinked"})`, async (t) => {
    const f = await fixture(t, "person@example.com");
    const read = createProvenanceReader({ fetchImpl: async () => response });
    assert.deepEqual((await read(f.model)).author, {
      name: "Original author",
      login: null,
    });
  });
}

test("does not treat a shallow boundary as the first commit", async (t) => {
  const f = await fixture(t);
  await writeFile(path.join(f.root, ".git/shallow"), f.commit + "\n");
  assert.deepEqual(await createProvenanceReader()(f.model), {
    firstCommittedAt: null,
    author: null,
    commit: null,
  });
});
