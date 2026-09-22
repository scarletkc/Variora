import { test } from "node:test";
import assert from "node:assert/strict";
import {
  needsBrowserTests,
  selectBrowserTests,
} from "../scripts/ci-changes.mjs";

test("project descriptions, metadata, and screenshots skip browser checks", () => {
  assert.equal(
    needsBrowserTests([
      "projects/demo/README.md",
      "projects/demo/PROMPT.md",
      "projects/demo/site.json",
      "projects/demo/models/model/README.md",
      "projects/demo/models/model/screenshots/mobile.png",
      "site/README.md",
    ]),
    false,
  );
});

test("mixed changes retain checks for code, assets, tests, dependencies, and workflows", () => {
  for (const file of [
    "site/app/page.tsx",
    "site/app/globals.css",
    "site/public/icon.svg",
    "site/tests/catalog.test.mjs",
    "projects/demo/models/model/app/index.html",
    "projects/demo/models/model/app/image.png",
    "projects/demo/models/model/preview.json",
    "package-lock.json",
    "site/package.json",
    ".github/workflows/pages.yml",
    ".prettierignore",
  ]) {
    assert.equal(
      needsBrowserTests(["projects/demo/README.md", file]),
      true,
      file,
    );
  }
  assert.equal(needsBrowserTests([]), true);
});

test("manual and initial pushes always run full checks", () => {
  const git = () => {
    throw new Error("Should not need Git");
  };
  assert.equal(selectBrowserTests({ event: "workflow_dispatch" }, git), true);
  assert.equal(
    selectBrowserTests(
      { event: "push", before: "0".repeat(40), after: "b".repeat(40) },
      git,
    ),
    true,
  );
});

test("compares the whole push and disables rename folding", () => {
  const calls = [];
  const git = (args) => {
    calls.push(args);
    return args[0] === "diff" ? "projects/demo/README.md\0" : "";
  };
  const before = "a".repeat(40),
    after = "b".repeat(40);
  assert.equal(
    selectBrowserTests({ event: "push", before, after }, git),
    false,
  );
  assert.deepEqual(calls[1], [
    "diff",
    "--name-only",
    "--no-renames",
    "-z",
    before,
    after,
    "--",
  ]);
});

test("shallow checkouts fetch the previous commit and failures retain full checks", () => {
  const input = {
    event: "push",
    before: "a".repeat(40),
    after: "b".repeat(40),
  };
  const calls = [];
  const git = (args) => {
    calls.push(args[0]);
    if (args[0] === "cat-file") throw new Error("Shallow history");
    return args[0] === "diff" ? "projects/demo/site.json\0" : "";
  };
  assert.equal(selectBrowserTests(input, git), false);
  assert.deepEqual(calls, ["cat-file", "fetch", "diff"]);
  assert.equal(
    selectBrowserTests(input, () => {
      throw new Error("Unavailable base");
    }),
    true,
  );
});
