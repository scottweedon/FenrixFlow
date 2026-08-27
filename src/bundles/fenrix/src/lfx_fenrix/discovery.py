"""Live model discovery and credential validation for the Fenrix provider.

Fenrix is FenrixCloud's shared self-hosted Ollama server, so models are
discovered from its native ``/api/tags`` endpoint (not the OpenAI ``/models``
convention) and credentials are validated with a probe request against the
same endpoint. Both callables are referenced by dotted path from the bundle's
``extension.json`` provider spec and invoked lazily by lfx's provider
registry, so importing this module is cheap and only happens when Fenrix is
actually used.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
from lfx.base.models.model_metadata import create_model_metadata
from lfx.base.models.model_utils import MIN_DEFAULT_MODELS, get_provider_variable_value
from lfx.log.logger import logger
from lfx.utils.ssrf_httpx import ssrf_safe_httpx_get

if TYPE_CHECKING:
    from uuid import UUID

_TIMEOUT_SECONDS = 5
_PROVIDER = "Fenrix"


def _tags_url(base_url: str) -> str:
    """Return the ``/api/tags`` URL, tolerating a base that already ends in /v1."""
    base_url = base_url.rstrip("/").removesuffix("/v1")
    return f"{base_url}/api/tags"


def _parse_model_names(data: object) -> list[str]:
    """Parse model names from Ollama's ``{"models": [{"name": ...}, ...]}`` response."""
    if isinstance(data, dict) and "models" in data:
        return sorted(str(m.get("name", "")) for m in data["models"] if m.get("name"))
    return []


def fetch_live_fenrix_models(user_id: UUID | str | None, model_type: str = "llm") -> list[dict]:
    """Return models served by the platform's shared Ollama server, tagged with ``model_type``.

    Returns an empty list (never raises) when the endpoint is unset or
    unreachable, so a missing or broken server simply contributes no models.
    """
    base_url = get_provider_variable_value(user_id, "OLLAMA_BASE_URL")
    if not base_url:
        return []

    try:
        response = ssrf_safe_httpx_get(_tags_url(base_url), timeout=_TIMEOUT_SECONDS, follow_redirects=False)
        response.raise_for_status()
        model_names = _parse_model_names(response.json())
        return [
            create_model_metadata(
                provider=_PROVIDER,
                name=name,
                icon="Ollama",
                model_type=model_type,
                tool_calling=model_type == "llm",
                default=i < MIN_DEFAULT_MODELS,
            )
            for i, name in enumerate(model_names)
        ]
    except Exception:  # noqa: BLE001 - degrade to "no live models" on any transport/parse error
        logger.debug(f"Could not fetch live Fenrix {model_type} models from {base_url}")
        return []


def validate_fenrix_credentials(provider: str, variables: dict[str, str], model_name: str | None = None) -> None:  # noqa: ARG001
    """Validate the configured Fenrix endpoint by probing ``/api/tags``.

    Raises ``ValueError`` with an actionable message on a missing URL,
    connection error, or timeout. ``provider`` and ``model_name`` are part of
    the registry validator contract but unused here.
    """
    base_url = variables.get("OLLAMA_BASE_URL")
    if not base_url:
        msg = "Invalid Fenrix (Ollama) base URL"
        logger.error(msg)
        raise ValueError(msg)

    tags_url = _tags_url(base_url)
    try:
        response = ssrf_safe_httpx_get(tags_url, timeout=_TIMEOUT_SECONDS, follow_redirects=False)
        response.raise_for_status()
    except httpx.ConnectError as e:
        msg = (
            f"Could not connect to the Fenrix Ollama server at {base_url.rstrip('/')}. "
            "Please check that the server is running and the URL is correct."
        )
        logger.error(msg)
        raise ValueError(msg) from e
    except httpx.TimeoutException as e:
        msg = f"Connection to the Fenrix Ollama server at {base_url.rstrip('/')} timed out."
        logger.error(msg)
        raise ValueError(msg) from e
    except httpx.HTTPStatusError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        msg = (
            f"The Fenrix Ollama server at {base_url.rstrip('/')} returned HTTP {status} for {tags_url}. "
            "Check that the base URL points to an Ollama-compatible API."
        )
        logger.error(msg)
        raise ValueError(msg) from e
    except httpx.RequestError as e:
        msg = f"Could not validate the Fenrix Ollama server at {base_url.rstrip('/')}: {e}"
        logger.error(msg)
        raise ValueError(msg) from e
