# Fork Changes

Tracks every place Fenrix has touched Langflow core (not just added new files
alongside it). Same rationale as FenrixChat's FORK_CHANGES.md: new features
should live in new files/directories and only touch existing files at
single-line "seam" points; this file exists for the exceptions.

## Pinned base

- Base: `langflow-ai/langflow`
- Pinned tag: `v1.12.0`
- `main` and `upstream-sync` both start from this tag.

## Why this fork exists

Langflow has no built-in support for being served from a URL subpath (no
`BASE_URL`/`BASENAME` env var, no reverse-proxy config option). Confirmed via
a real GitHub thread (langflow-ai/langflow discussions/issues on subpath
reverse-proxy deployment): a maintainer's answer to "white screen behind
/langflow" was that the `BASENAME` constant in the frontend's
`config-constants.ts` needs to be hardcoded per-deployment - there is no
runtime configuration path. design-spec.md §9.2 addresses every tenant's
Langflow instance at `/root/<tenant_id>/workflows/*`, which requires this to
be configurable per-container, not hardcoded at build time.

## Core changes

### Runtime-configurable subpath serving

- **Files:** `src/backend/base/langflow/main.py` (new `_fenrix_inject_basename`,
  called from `setup_static_files`), `src/frontend/src/customization/config-constants.ts`
  (`BASENAME`, `BASE_URL_API`, `BASE_URL_API_V2`), `src/frontend/src/hooks/use-webhook-events.ts`
  (one hardcoded `/api/v1/webhook-events/...` SSE URL).
- **Why not a seam:** `BASENAME` was a hardcoded build-time TS constant with no runtime
  or env-var override anywhere in the codebase - confirmed real via upstream GitHub
  threads on subpath reverse-proxy deployment, where a maintainer's fix was "hardcode
  BASENAME in config-constants.ts per deployment." A per-tenant frontend rebuild
  contradicts the provisioner deploying one shared image per tenant.
- **Interface:** the backend reads `LANGFLOW_BASENAME` from the environment once at
  server startup and writes `<script>window.__LANGFLOW_BASENAME__="...";</script>`
  directly into the built `index.html` on disk (idempotent - checks for the marker
  first). `config-constants.ts`'s `BASENAME` reads that global at browser runtime
  instead of a literal; `vite.config.mts` still imports the same constant for its
  build-time `base` option, where `window` is undefined and it correctly stays `""`
  (keeps Vite's own asset URLs relative, so they already resolve correctly through
  Caddy's `handle_path` prefix-stripping with zero changes needed there).
  `BASE_URL_API`/`BASE_URL_API_V2` are now derived (`` `${BASENAME}/api/v1/` ``) instead
  of literal absolute paths, so every API call built through `getURL()`/`getBaseUrl()`
  automatically carries the tenant prefix Caddy needs to see to route the request at
  all - confirmed this was a second, independent gap from the React-Router-only fix.
  A third, likely the actual cause of the upstream-reported "white screen": the built
  `index.html` has a hardcoded `<base href="/" />`, which governs how the browser
  resolves every `./`-relative asset URL on the page - `_fenrix_inject_basename`
  rewrites that too when a basename is set, otherwise every asset request 404s before
  React or the injected global ever runs, independent of the other two fixes.
- **Expected upstream conflicts:** any upstream change to `config-constants.ts`, the
  `setup_static_files`/`custom_404_handler` region of `main.py`, or anywhere else that
  starts hardcoding `/api/v1/` or `/api/v2/` literally instead of through the
  `BASE_URL_API`/`getURL()` helpers.
- **Verified:** built a real image from `docker/build_and_push.Dockerfile` (target `full`,
  the same Dockerfile `make docker_build` uses), ran it standalone with
  `LANGFLOW_BASENAME=/root/acme/workflows`, and proxied it through a throwaway Caddy
  instance with the same `handle_path` prefix-stripping pattern the provisioner's real
  Caddy labels use. Confirmed: the index page carries the injected `window.__LANGFLOW_BASENAME__`
  global and rewritten `<base href>`; the referenced JS/CSS assets both resolve (200)
  through the prefix; a client-side deep route (`/flows`) falls back to the same correctly
  injected shell via `app.frontend()`'s SPA fallback; and an API call under the prefix
  (`/api/v1/auto_login`) resolves (200 JSON), confirming `BASE_URL_API`'s derivation from
  `BASENAME` reaches Caddy correctly.
