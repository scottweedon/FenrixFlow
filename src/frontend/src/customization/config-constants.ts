declare global {
  interface Window {
    __LANGFLOW_BASENAME__?: string;
  }
}

// Fenrix: reads the per-tenant subpath the backend injected into index.html at server
// startup (see main.py's _fenrix_inject_basename) instead of a hardcoded build-time
// literal, so one shared image/build can be deployed at any tenant's
// /root/<tenant_id>/workflows prefix. `typeof window === "undefined"` when this file is
// imported by vite.config.mts (a Node build-time context, not a browser) - BASENAME
// correctly stays "" there, which is what keeps Vite's own asset paths relative.
export const BASENAME =
  (typeof window !== "undefined" && window.__LANGFLOW_BASENAME__) || "";
export const PORT = 3000;
export const PROXY_TARGET = "http://localhost:7860";
export const API_ROUTES = ["^/api/v1/", "^/api/v2/", "/health"];
// Fenrix: derived from BASENAME (not a literal absolute path) - otherwise these would
// still point at domain-root /api/v1/ even under a tenant subpath, missing the prefix
// Caddy's handle_path route needs to see in order to route the request to this tenant's
// container at all.
export const BASE_URL_API = `${BASENAME}/api/v1/`;
export const BASE_URL_API_V2 = `${BASENAME}/api/v2/`;
export const HEALTH_CHECK_URL = "/health_check";
export const DOCS_LINK = "https://docs.langflow.org";

export default {
  DOCS_LINK,
  BASENAME,
  PORT,
  PROXY_TARGET,
  API_ROUTES,
  BASE_URL_API,
  BASE_URL_API_V2,
  HEALTH_CHECK_URL,
};
