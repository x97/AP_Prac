import type { MetadataRoute } from "next";

import { brand } from "@/config/brand";

// App screens require an account and render as a loading shell for crawlers.
// Keep them out of the index; the public landing page is the SEO entry point.
const PRIVATE_ROUTES = [
  "/api/",
  "/dashboard",
  "/practice",
  "/knowledge",
  "/exams",
  "/cards",
  "/wrong",
  "/bookmarks",
  "/notes",
  "/history",
  "/me",
];

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: PRIVATE_ROUTES,
      },
    ],
    sitemap: `${brand.url}/sitemap.xml`,
    host: brand.url,
  };
}
