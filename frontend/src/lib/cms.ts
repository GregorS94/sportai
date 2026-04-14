// Thin client for the Seelenmut CMS JSON API.
// In production the frontend container talks to the cms container over the
// internal docker network, e.g. http://cms:8000. Override with env CMS_URL.

const CMS_URL: string =
  (import.meta.env.CMS_URL as string | undefined) ||
  process.env.CMS_URL ||
  "http://cms:8000";

export type CmsMeta = {
  title: string;
  description: string;
};

export type CmsPage = {
  slug: string;
  title: string;
  excerpt: string;
  content: string;
  content_html: string;
  show_in_menu: boolean;
  sort_order: number;
  updated_at: string;
  meta: CmsMeta;
};

export type CmsTag = {
  id?: number;
  slug: string;
  name: string;
  count?: number;
};

export type CmsPost = {
  slug: string;
  title: string;
  excerpt: string;
  content: string;
  content_html: string;
  cover_image: string | null;
  published_at: string | null;
  tags: CmsTag[];
  meta: CmsMeta;
};

export type PostList = {
  items: CmsPost[];
  total: number;
  limit: number;
  offset: number;
};

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${CMS_URL}${path}`, init);
  if (!res.ok) {
    throw new Error(`CMS ${path} -> ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

// Make the CMS media URL absolute for the browser.
// CMS returns paths like "/media/foo.jpg" – we proxy /media via Caddy so the
// relative path is actually fine on the real deployment. For local dev we
// rewrite it to point directly at the CMS.
export function mediaUrl(path: string | null | undefined): string {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  if (import.meta.env.DEV) return `${CMS_URL}${path}`;
  return path;
}

export const cms = {
  menuPages: () => fetchJSON<CmsPage[]>("/api/pages"),
  page: (slug: string) => fetchJSON<CmsPage>(`/api/pages/${slug}`),
  posts: (opts: { limit?: number; offset?: number; tag?: string } = {}) => {
    const qs = new URLSearchParams();
    if (opts.limit != null) qs.set("limit", String(opts.limit));
    if (opts.offset != null) qs.set("offset", String(opts.offset));
    if (opts.tag) qs.set("tag", opts.tag);
    const q = qs.toString();
    return fetchJSON<PostList>(`/api/posts${q ? `?${q}` : ""}`);
  },
  post: (slug: string) => fetchJSON<CmsPost>(`/api/posts/${slug}`),
  tags: () => fetchJSON<CmsTag[]>("/api/tags"),
};

// Soft wrapper that swallows network errors so the layout still renders.
export async function safe<T>(p: Promise<T>, fallback: T): Promise<T> {
  try {
    return await p;
  } catch (err) {
    console.error("[cms]", err);
    return fallback;
  }
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString("de-DE", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  } catch {
    return "";
  }
}
