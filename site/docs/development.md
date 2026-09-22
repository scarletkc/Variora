# Development

Run commands from the repository root with Node.js 24.

## Local servers

```sh
npm ci
npm run dev
```

The development server regenerates the catalog before starting Next.js. To test
the static export:

```sh
npm run build
npm --workspace site run serve
```

The build writes `site/out/`; the static server serves it at
`http://127.0.0.1:4173`.

## Preview compatibility

Use the [catalog and preview configuration](../README.md#catalog-and-previews)
to register a prebuilt implementation.

The preview sandbox gives its document an opaque origin (`Origin: null`). Every
JavaScript module entry and imported dependency, including relative `.js` and
`.mjs` files on the same host, must return a JavaScript MIME type and permit
cross-origin requests. For public assets loaded without credentials,
`Access-Control-Allow-Origin: *` satisfies the CORS requirement. External data
fetched by a preview also needs suitable CORS headers. A self-contained classic
script without a `crossorigin` attribute is another supported packaging option.

The development server and local static server provide CORS headers for preview
assets. Static exports do not carry response headers: the deployment host must
provide them for the complete module graph. Verify implementations inside the
site's preview, since opening the HTML directly does not exercise the sandbox's
loading restrictions.

## Checks

```sh
npm test
npm run format:check
npm run check
npx playwright install chromium
npm --workspace site run test:e2e
npm run build
```

`npm test` runs unit tests and design-token guards. `npm run check` regenerates
the catalog and checks TypeScript types.

Browser tests require port 4173 to be free. They generate a temporary fixture
catalog, check module loading against the development server, then build and
test the static export on desktop and mobile views. Loading checks cover relative
`.mjs` imports, missing entry or dependency CORS headers, incorrect MIME types,
classic scripts, and parent isolation.

The fixture export is removed afterward. Run `npm run build` afterward to produce
a deployable export. `VARIORA_PROJECTS_DIR` overrides the catalog input directory
for isolated test builds.
