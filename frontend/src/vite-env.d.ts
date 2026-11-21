/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** URL du backend en production (vide en local : proxy Vite). */
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
