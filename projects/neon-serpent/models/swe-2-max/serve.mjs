// Minimal static server: `npm run serve` then open http://localhost:8080/
import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL(".", import.meta.url));
const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
};

export function serve(port = 8080) {
  const server = createServer(async (req, res) => {
    try {
      let url = decodeURIComponent(new URL(req.url, "http://x").pathname);
      if (url === "/") {
        res.writeHead(302, { location: "/app/index.html" });
        return res.end();
      }
      const file = path.join(root, url);
      if (!file.startsWith(root)) throw new Error("path escapes root");
      const s = await stat(file);
      const target = s.isDirectory() ? path.join(file, "index.html") : file;
      const body = await readFile(target);
      res.writeHead(200, {
        "content-type": MIME[path.extname(target).toLowerCase()] || "application/octet-stream",
        "cache-control": "no-store",
      });
      res.end(body);
    } catch {
      res.writeHead(404);
      res.end("not found");
    }
  });
  return new Promise((resolve) =>
    server.listen(port, () => resolve(server)),
  );
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const port = Number(process.argv[2] || 8080);
  serve(port).then(() =>
    console.log(`Neon Serpent → http://localhost:${port}/`),
  );
}
