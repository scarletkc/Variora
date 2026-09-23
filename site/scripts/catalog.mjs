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
import { pianoRoll, readMidi } from "./midi.mjs";
import { createProvenanceReader } from "./provenance.mjs";

const siteRoot = fileURLToPath(new URL("..", import.meta.url));
const audioTypes = {
  ".mp3": "audio/mpeg",
  ".m4a": "audio/mp4",
  ".aac": "audio/aac",
  ".ogg": "audio/ogg",
  ".oga": "audio/ogg",
  ".opus": "audio/ogg; codecs=opus",
  ".wav": "audio/wav",
  ".flac": "audio/flac",
  ".webm": "audio/webm",
};
const midiExtensions = new Set([".mid", ".midi"]);
const extensions = new Set([
  ...Object.keys(audioTypes),
  ...midiExtensions,
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
  ".mp4",
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
    throw new Error(`Path must be relative: ${relative}`);
  }
  const candidate = path.resolve(root, relative);
  if (!inside(root, candidate))
    throw new Error(`Path escapes ${root}: ${relative}`);
  const resolved = await realpath(candidate);
  if (!inside(await realpath(root), resolved))
    throw new Error(`A symlink escapes ${root}: ${relative}`);
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

// Only raster captures are exported: SVG may contain active or external content.
const screenshotExtensions = new Set([".png", ".jpg", ".jpeg", ".webp"]);
async function copyScreenshot(modelRoot, destination, url) {
  const configText = await readOptional(
    path.join(modelRoot, "comparison.json"),
  );
  let relative;
  if (configText) {
    const config = JSON.parse(configText);
    if (config.screenshot === null) return null;
    relative = config.screenshot;
  } else {
    let entries;
    try {
      entries = await readdir(path.join(modelRoot, "screenshots"), {
        withFileTypes: true,
      });
    } catch (error) {
      if (error.code === "ENOENT") return null;
      throw error;
    }
    const names = entries
      .filter(
        (entry) =>
          !entry.name.startsWith(".") &&
          (entry.isFile() || entry.isSymbolicLink()) &&
          screenshotExtensions.has(path.extname(entry.name).toLowerCase()),
      )
      .map((entry) => entry.name)
      .sort();
    const preferred = ["illustration", "scene", "preview", "desktop"];
    const name =
      preferred
        .map((stem) => names.find((name) => path.parse(name).name === stem))
        .find(Boolean) ?? names[0];
    if (!name) return null;
    relative = `screenshots/${name}`;
  }
  const source = await resolveInside(modelRoot, relative);
  const extension = path.extname(source).toLowerCase();
  if (!screenshotExtensions.has(extension) || !(await stat(source)).isFile())
    throw new Error(
      `Comparison screenshot must be a raster image: ${relative}`,
    );
  await mkdir(destination, { recursive: true });
  await cp(source, path.join(destination, `screenshot${extension}`));
  return `${url}/screenshot${extension}`;
}

const outputFields = new Set(["type", "audio", "midi", "source", "rendering"]);
const origins = new Set(["model", "contributor"]);
async function readOutput(modelRoot, destination, url) {
  const file = path.join(modelRoot, "output.json");
  const text = await readOptional(file);
  if (text === null) return null;
  const fail = (message) => {
    throw new Error(`${file}: ${message}`);
  };
  let config;
  try {
    config = JSON.parse(text);
  } catch (error) {
    fail(`invalid JSON (${error.message})`);
  }
  if (config?.type !== "music")
    fail(`unsupported output type ${JSON.stringify(config?.type)}`);
  for (const key of Object.keys(config))
    if (!outputFields.has(key)) fail(`unknown field "${key}"`);
  if (config.rendering != null && typeof config.rendering !== "string")
    fail("rendering must be a string");
  async function entry(value, label) {
    const item = typeof value === "string" ? { path: value } : value;
    if (typeof item?.path !== "string" || !item.path)
      fail(`${label} must be a relative path or { "path", "origin" }`);
    const origin = item.origin ?? "model";
    if (!origins.has(origin))
      fail(`${label} origin must be "model" or "contributor"`);
    const relative = path.posix.normalize(item.path).replace(/\/+$/, "");
    let source;
    try {
      source = await resolveInside(modelRoot, relative);
    } catch (error) {
      fail(
        error.code === "ENOENT"
          ? `${label} not found: ${relative}`
          : `${label}: ${error.message}`,
      );
    }
    return { path: relative, origin, source, info: await stat(source) };
  }
  async function publish(item) {
    const target = path.join(destination, ...item.path.split("/"));
    await mkdir(path.dirname(target), { recursive: true });
    await cp(item.source, target, { dereference: true });
    return {
      path: item.path,
      name: path.posix.basename(item.path),
      url: `${url}/${item.path.split("/").map(encodeURIComponent).join("/")}`,
      origin: item.origin,
    };
  }
  let audio = null;
  if (config.audio != null) {
    const item = await entry(config.audio, "audio");
    const extension = path.extname(item.path).toLowerCase();
    if (!item.info.isFile() || !audioTypes[extension])
      fail(
        `audio must be a ${Object.keys(audioTypes).join(", ")} file: ${item.path}`,
      );
    audio = {
      ...(await publish(item)),
      format: extension.slice(1).toUpperCase(),
      type: audioTypes[extension],
    };
  }
  let midi = null;
  if (config.midi != null) {
    const item = await entry(config.midi, "midi");
    if (
      !item.info.isFile() ||
      !midiExtensions.has(path.extname(item.path).toLowerCase())
    )
      fail(`midi must be a .mid or .midi file: ${item.path}`);
    midi = { ...(await publish(item)), summary: null, roll: null };
    try {
      const parsed = readMidi(await readFile(item.source));
      midi.summary = parsed.summary;
      const roll = pianoRoll(parsed.notes, parsed.summary.duration);
      if (roll) {
        await writeFile(path.join(destination, "roll.svg"), roll);
        midi.roll = `${url}/roll.svg`;
      }
    } catch (error) {
      console.warn(`${file}: MIDI details unavailable (${error.message})`);
    }
  }
  const source = [];
  for (const value of [config.source ?? []].flat()) {
    const item = await entry(value, "source");
    source.push({
      path: item.path,
      directory: item.info.isDirectory(),
      origin: item.origin,
    });
  }
  if (!audio && !midi && !source.length)
    fail("list at least one audio, midi, or source file");
  return {
    type: "music",
    audio,
    midi,
    source,
    rendering: config.rendering?.trim() ?? "",
  };
}

export async function buildCatalog(projectsRoot, publicRoot) {
  const provenance = createProvenanceReader();
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
        reasoning: field(record, "Reasoning effort"),
        harness: field(record, "Harness"),
        ...(await provenance(modelRoot)),
        preview,
        screenshot: await copyScreenshot(
          modelRoot,
          path.join(previewsRoot, "_comparisons", id, modelId),
          `/previews/_comparisons/${encodeURIComponent(id)}/${encodeURIComponent(modelId)}`,
        ),
        output: await readOutput(
          modelRoot,
          path.join(previewsRoot, "_outputs", id, modelId),
          `/previews/_outputs/${encodeURIComponent(id)}/${encodeURIComponent(modelId)}`,
        ),
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
