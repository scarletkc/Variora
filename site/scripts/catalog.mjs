import {
  cp,
  mkdir,
  readdir,
  readFile,
  realpath,
  rm,
  stat,
  writeFile,
} from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const siteRoot = fileURLToPath(new URL("..", import.meta.url));
const extensions = new Set([
  ".html",
  ".css",
  ".js",
  ".mjs",
  ".json",
  ".svg",
  ".png",
  ".jpg",
  ".jpeg",
  ".webp",
  ".avif",
  ".gif",
  ".ico",
  ".woff",
  ".woff2",
  ".ttf",
  ".otf",
  ".mp3",
  ".wav",
  ".ogg",
  ".mp4",
  ".webm",
  ".wasm",
  ".glb",
  ".gltf",
  ".bin",
  ".ktx2",
  ".hdr",
]);
const ignored = new Set([
  "node_modules",
  "coverage",
  "package.json",
  "package-lock.json",
]);

async function readOptional(file) {
  try {
    return await readFile(file, "utf8");
  } catch (error) {
    if (error.code === "ENOENT") return null;
    throw error;
  }
}

async function folders(root) {
  try {
    return (await readdir(root, { withFileTypes: true }))
      .filter((entry) => entry.isDirectory() && !entry.name.startsWith("."))
      .map((entry) => entry.name)
      .sort();
  } catch (error) {
    if (error.code === "ENOENT") return [];
    throw error;
  }
}

function clean(value) {
  return value
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/[*`]/g, "")
    .trim();
}

function field(readme, name) {
  const match = readme.match(
    new RegExp(`^\\|\\s*${name}\\s*\\|([^|]+)\\|`, "im"),
  );
  return match ? clean(match[1]) : "";
}

function inside(parent, child) {
  const relative = path.relative(parent, child);
  return relative && !relative.startsWith("..") && !path.isAbsolute(relative);
}

async function resolveInside(root, relative) {
  if (
    typeof relative !== "string" ||
    path.isAbsolute(relative) ||
    relative.includes("\\")
  ) {
    throw new Error(`Preview path must be relative: ${relative}`);
  }
  const candidate = path.resolve(root, relative);
  if (!inside(root, candidate))
    throw new Error(`Preview path escapes ${root}: ${relative}`);
  const resolved = await realpath(candidate);
  if (!inside(await realpath(root), resolved))
    throw new Error(`Preview symlink escapes ${root}: ${relative}`);
  return candidate;
}

async function copyAssets(source, destination) {
  await mkdir(destination, { recursive: true });
  for (const entry of await readdir(source, { withFileTypes: true })) {
    if (entry.name.startsWith(".") || ignored.has(entry.name)) continue;
    if (entry.isSymbolicLink())
      throw new Error(
        `Symlinks are not supported in previews: ${path.join(source, entry.name)}`,
      );
    if (entry.isDirectory())
      await copyAssets(
        path.join(source, entry.name),
        path.join(destination, entry.name),
      );
    else if (
      entry.isFile() &&
      extensions.has(path.extname(entry.name).toLowerCase())
    ) {
      await cp(
        path.join(source, entry.name),
        path.join(destination, entry.name),
      );
    }
  }
}

export async function buildCatalog(projectsRoot, publicRoot) {
  const previewsRoot = path.join(publicRoot, "previews");
  // Only this generated directory is replaced; project sources are never modified.
  await rm(previewsRoot, { recursive: true, force: true });
  const projects = [];
  for (const id of await folders(projectsRoot)) {
    const root = path.join(projectsRoot, id);
    const prompt = await readOptional(path.join(root, "PROMPT.md"));
    if (!prompt) continue;
    const readme = (await readOptional(path.join(root, "README.md"))) ?? "";
    const metadataText = await readOptional(path.join(root, "site.json"));
    const metadata = metadataText ? JSON.parse(metadataText) : {};
    const title = clean(readme.match(/^#\s+(.+)$/m)?.[1] ?? id);
    const description =
      prompt.split(/\r?\n\s*\r?\n/).find((part) => !part.startsWith("#")) ?? "";
    const models = [];
    for (const modelId of await folders(path.join(root, "models"))) {
      const modelRoot = path.join(root, "models", modelId);
      const record =
        (await readOptional(path.join(modelRoot, "README.md"))) ?? "";
      const configText = await readOptional(
        path.join(modelRoot, "preview.json"),
      );
      const config = configText
        ? JSON.parse(configText)
        : { directory: "app", entry: "index.html" };
      let preview = null;
      try {
        const source = await resolveInside(modelRoot, config.directory);
        const entry = await resolveInside(source, config.entry);
        if (
          path.extname(entry).toLowerCase() !== ".html" ||
          !(await stat(entry)).isFile()
        ) {
          throw new Error(`Preview entry must be an HTML file: ${entry}`);
        }
        const destination = path.join(previewsRoot, id, modelId);
        await copyAssets(source, destination);
        try {
          await stat(path.join(destination, config.entry));
        } catch {
          throw new Error(
            `Preview entry was excluded by the asset rules: ${entry}`,
          );
        }
        preview = `/previews/${encodeURIComponent(id)}/${encodeURIComponent(modelId)}/${config.entry.split("/").map(encodeURIComponent).join("/")}`;
      } catch (error) {
        if (configText || error.code !== "ENOENT") throw error;
      }
      models.push({
        id: modelId,
        name:
          field(record, "Model") ||
          clean(record.match(/^#\s+(.+)$/m)?.[1] ?? modelId),
        provider: field(record, "Provider"),
        harness: field(record, "Harness"),
        preview,
      });
    }
    projects.push({
      id,
      title,
      description,
      category: metadata.category ?? "experiment",
      summaries: metadata.summaries ?? {},
      models,
    });
  }
  return projects;
}

if (
  process.argv[1] &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
  const projects = await buildCatalog(
    process.env.VARIORA_PROJECTS_DIR
      ? path.resolve(process.env.VARIORA_PROJECTS_DIR)
      : path.resolve(siteRoot, "../projects"),
    path.join(siteRoot, "public"),
  );
  await mkdir(path.join(siteRoot, ".generated"), { recursive: true });
  await writeFile(
    path.join(siteRoot, ".generated/catalog.json"),
    JSON.stringify(projects, null, 2) + "\n",
  );
  console.log(
    `Catalog: ${projects.length} projects, ${projects.reduce((sum, project) => sum + project.models.length, 0)} implementations.`,
  );
}
