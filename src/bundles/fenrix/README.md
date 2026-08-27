# lfx-fenrix

FenrixCloud's shared self-hosted Ollama model server, packaged as a
standalone Extension Bundle so it appears as a first-class, pre-configured
provider in Langflow's model picker.

Registers a **Fenrix** model provider alongside the built-in providers.
Fenrix is an Ollama server under the hood, so this provider reuses the
`ChatOllama` class Langflow core already resolves for its built-in Ollama
provider and discovers served models live from the server's `/api/tags`
endpoint - the same server every tenant's LibreChat instance also talks to.

Unlike a component bundle, this ships **no component**: it contributes a
provider through the `providers[]` block in `extension.json`, which
Langflow's provider registry merges into the unified model system. It edits
no Langflow core files (see the repo's `FORK_CHANGES.md` for the one
single-line core addition this depends on: `OLLAMA_BASE_URL` is added to
`VARIABLES_TO_GET_FROM_ENVIRONMENT` so this card shows configured
automatically, with no manual "Model providers" entry required).

## Configure

Every FenrixCloud tenant container sets `OLLAMA_BASE_URL` in its own
environment (the provisioner's shared tunnel to the platform's Ollama
server), so this provider is configured automatically for every user at
login. To point at a different server manually, set the `OLLAMA Base URL`
global variable under **Settings → Model Providers → Fenrix**.

## Install

```bash
pip install lfx-fenrix
```

The bundle is registered automatically via the `langflow.extensions`
entry-point. Restart your Langflow server and select **Fenrix** in any
Language Model field.

## Develop

```bash
cd src/bundles/fenrix
pip install -e .
lfx extension validate src/lfx_fenrix
```
