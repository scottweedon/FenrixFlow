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

### Ollama base URL and default model from environment

- **File:** `src/bundles/ollama/src/lfx_ollama/components/ollama/ollama.py`
  (`ChatOllamaComponent`'s `base_url` `StrInput` and `model_name` `DropdownInput`).
- **Why not a seam:** every new Ollama node in every flow defaults to
  `http://localhost:11434` with no way to point it at this platform's actual shared
  Ollama server - confirmed via a real source read that, unlike OpenAI/Anthropic
  (`services/settings`'s env-var-imported credentials), Ollama's base URL has no env var,
  settings hook, or global-variable import path anywhere in the component or the
  settings/variable services. FenrixCloud runs one shared self-hosted Ollama server for
  every tenant (design-spec.md's existing shared-inference-service pattern, same shape as
  vLLM) - without this, a tenant's flow builder would have to manually retype the real
  server URL into every single Ollama node they ever add.
- **Interface:** `value=os.environ.get("LANGFLOW_OLLAMA_BASE_URL", "http://localhost:11434")`
  instead of the hardcoded literal - a single-line default-value change, not new
  behavior. Reads once at component-definition time (matching how the field's static
  default already worked); a user can still override it per-node exactly as before.
  `model_name` gets the same treatment - `value=os.environ.get("LANGFLOW_OLLAMA_DEFAULT_MODEL", "")`
  - since its `options` list is only ever populated live from `update_build_config`
  (never pre-filled), a brand new node otherwise starts with no model selected at all even
  when the server default is already correct, forcing a manual pick before the node is
  usable.
- **Expected upstream conflicts:** any upstream change to these inputs' declarations or to
  `ChatOllamaComponent`'s constructor signature.
- **Verified:** built a real image (`docker/build_and_push.Dockerfile`), ran it as a tenant
  container with `LANGFLOW_OLLAMA_BASE_URL` and `LANGFLOW_OLLAMA_DEFAULT_MODEL` set to real
  values (the latter against the real hosted Ollama server via the platform's SSH tunnel,
  not a placeholder), and confirmed directly (`ChatOllamaComponent().inputs` inspected
  inside the running container) that both fields default to the configured values, not the
  upstream `http://localhost:11434` / empty-selection defaults.

### OLLAMA_BASE_URL auto-imported as a global variable

- **File:** `src/lfx/src/lfx/services/settings/constants.py`
  (`VARIABLES_TO_GET_FROM_ENVIRONMENT`).
- **Why not a seam:** the new `src/bundles/fenrix/` provider bundle (a plain
  extension, no core edit) registers a "Fenrix" entry in Langflow's Model
  Providers dialog backed by the `OLLAMA_BASE_URL` global variable. That
  dialog's "configured" state is driven entirely by whether the variable
  already exists for the user - and `initialize_user_variables` only
  auto-creates variables named in this fixed list at login, confirmed via a
  real source read that `OLLAMA_BASE_URL` was not already in it (every other
  built-in provider's key already is). Without this addition, every tenant
  user would have to manually click into the Fenrix card and type in the
  platform's own internal Ollama proxy URL themselves.
- **Interface:** one additional string in the list. FenrixCloud's provisioner
  sets a plain (unprefixed) `OLLAMA_BASE_URL` env var on the `langflow-app`
  container (`infra/templates/tenant-stack/docker-compose.template.yml`,
  alongside the existing `LANGFLOW_OLLAMA_BASE_URL` this file's component
  patch above reads), so the auto-import now seeds the same value as a global
  variable at every login - no separate mechanism, no manual entry.
- **Expected upstream conflicts:** none beyond a routine merge conflict if
  upstream reorders/extends this same list.
- **Verified:** built a real image (`docker/build_and_push.Dockerfile`, target
  `full`), ran it standalone with `OLLAMA_BASE_URL` set, logged in via the
  real API, and confirmed directly against the running container:
  `GET /api/v1/variables` lists `OLLAMA_BASE_URL` with `has_value: true`
  (auto-imported, not manually created), and `GET /api/v1/models` - the same
  endpoint the frontend's Model Providers dialog reads - returns a `"Fenrix"`
  entry with `"is_configured": true` and `"live_discovery": true`, alongside
  every other provider (all `is_configured: false`, as expected with no keys
  set). Also unit-verified the registration path directly: loaded
  `src/bundles/fenrix/src/lfx_fenrix/extension.json` through
  `lfx.extension.manifest.load_manifest`, called `register_provider` on the
  resulting spec, and confirmed it merges into `MODEL_PROVIDER_METADATA` and
  `LIVE_MODEL_PROVIDERS` without conflict (reusing the already-registered
  `ChatOllama` class import - `model_class` is deliberately omitted from the
  spec, so no new import is added), that `live_discovery_for("Fenrix")` and
  `validator_for("Fenrix")` resolve the dotted-path callables, and that
  calling the live-discovery callable with no reachable server degrades to an
  empty list rather than raising.
