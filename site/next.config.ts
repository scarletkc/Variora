import type { NextConfig } from "next";
import { PHASE_DEVELOPMENT_SERVER } from "next/constants";

export default function config(phase: string): NextConfig {
  const development = phase === PHASE_DEVELOPMENT_SERVER;
  return {
    output: development ? undefined : "export",
    trailingSlash: true,
    poweredByHeader: false,
    images: { unoptimized: true },
    // Static exports receive response headers from their hosting server.
    ...(development && {
      async headers() {
        return [
          {
            source: "/previews/:path*",
            headers: [{ key: "Access-Control-Allow-Origin", value: "*" }],
          },
        ];
      },
    }),
  };
}
