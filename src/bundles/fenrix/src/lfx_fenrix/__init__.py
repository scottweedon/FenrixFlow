"""lfx-fenrix: Fenrix model-provider bundle.

Distribution unit ``lfx-fenrix``. At runtime Langflow's loader discovers the
``extension.json`` shipped alongside this ``__init__.py`` and registers its
``providers[]`` entry, merging a **Fenrix** provider into the unified model
system. Fenrix is FenrixCloud's shared self-hosted Ollama server, so the
provider reuses the ``ChatOllama`` class core lfx already resolves for the
built-in Ollama provider and discovers models live from the server's
``/api/tags`` endpoint (see :mod:`lfx_fenrix.discovery`).

Every tenant gets the ``OLLAMA_BASE_URL`` global variable this provider reads
auto-imported at login (``VARIABLES_TO_GET_FROM_ENVIRONMENT`` in
``lfx.services.settings.constants``, set from the platform's own
``OLLAMA_BASE_URL`` container env var) - so this card shows configured with no
manual entry, unlike the generic providers it sits alongside.
"""
