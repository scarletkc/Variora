import { execFileSync } from "node:child_process";
import { appendFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export function needsBrowserTests(files) {
  const contentOnly =
    /^(?:site\/README\.md|projects\/[^/]+\/(?:README\.md|PROMPT\.md|site\.json|models\/[^/]+\/(?:README\.md|screenshots\/.+)))$/;
  return files.length === 0 || files.some((file) => !contentOnly.test(file));
}

export function selectBrowserTests(
  { event, before, after },
  git = (args) =>
    execFileSync("git", args, {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    }),
) {
  if (
    event !== "push" ||
    !/^[a-f0-9]{40}$/.test(before ?? "") ||
    /^0+$/.test(before) ||
    !/^[a-f0-9]{40}$/.test(after ?? "")
  )
    return true;
  try {
    try {
      git(["cat-file", "-e", `${before}^{commit}`]);
    } catch {
      git(["fetch", "--no-tags", "--depth=1", "origin", before]);
    }
    // Include both paths of renames and all commits in the push.
    const files = git([
      "diff",
      "--name-only",
      "--no-renames",
      "-z",
      before,
      after,
      "--",
    ])
      .split("\0")
      .filter(Boolean);
    return needsBrowserTests(files);
  } catch {
    console.warn("Change detection unavailable; running full browser checks.");
    return true;
  }
}

if (
  process.argv[1] &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
  const full = selectBrowserTests({
    event: process.env.GITHUB_EVENT_NAME,
    before: process.env.BEFORE_SHA,
    after: process.env.GITHUB_SHA,
  });
  console.log(
    full
      ? "Full checks: browser tests and production build."
      : "Content changes: unit checks and production build.",
  );
  appendFileSync(process.env.GITHUB_OUTPUT, `browser_tests=${full}\n`);
}
