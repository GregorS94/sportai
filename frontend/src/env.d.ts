/// <reference types="astro/client" />

interface ImportMetaEnv {
  readonly CMS_URL: string;
  readonly PUBLIC_SITE_NAME: string;
  readonly PUBLIC_SITE_TAGLINE: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
