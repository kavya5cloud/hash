import type { NextConfig } from "next";

// Static pages of the Hash landing export, which lives in `public/` as
// `<page>/index.html`. Next does not serve nested public directories as clean
// routes, so each is rewritten onto its file explicitly.
const LANDING_PAGES = [
  "contact",
  "terms-and-conditions",
  "privacy-policy",
] as const;

const nextConfig: NextConfig = {
  async rewrites() {
    return {
      // `beforeFiles` so these win over the app router, which otherwise owns
      // `/`. The landing page's own assets are absolute (`/images/...`,
      // `/*.mjs`) and resolve straight out of `public/`.
      beforeFiles: [
        { source: "/", destination: "/index.html" },
        ...LANDING_PAGES.flatMap((page) => [
          { source: `/${page}`, destination: `/${page}/index.html` },
          { source: `/${page}/`, destination: `/${page}/index.html` },
        ]),
      ],
      afterFiles: [],
      fallback: [],
    };
  },
};

export default nextConfig;
