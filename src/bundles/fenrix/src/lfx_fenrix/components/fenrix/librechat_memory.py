"""Read/write a user's persistent memories in this platform's LibreChat instance.

LibreChat already has a full, simple key-value memory store with a real per-user REST
API (`/api/memories`) - this component makes LibreChat the single source of truth for
"memories" rather than standing up a second, separate store inside Langflow. See
FORK_CHANGES.md-adjacent design discussion: Langflow's own Memory Base feature distills
conversation history into a semantic vector store, a fundamentally different shape of
data from LibreChat's literal, hand-editable facts - so this deliberately does not try
to sync the two, it just lets a flow read/write LibreChat's copy directly.
"""

from __future__ import annotations

import os

import httpx

from lfx.custom.custom_component.component import Component
from lfx.io import DropdownInput, MessageTextInput, Output, SecretStrInput, StrInput
from lfx.schema.data import Data
from lfx.utils.ssrf_httpx import (
    ssrf_protected_httpx_client_kwargs_for_url,
    ssrf_safe_async_get,
    ssrf_safe_async_post,
)

HTTP_STATUS_CONFLICT = 409
_OPERATIONS = ["List", "Get", "Set", "Delete"]


class LibreChatMemoryComponent(Component):
    display_name = "LibreChat Memory"
    description = (
        "Read or write a user's persistent memories in this platform's LibreChat "
        "instance. LibreChat's memories API is the canonical store - this component "
        "never keeps its own copy."
    )
    icon = "Brain"
    name = "LibreChatMemory"

    inputs = [
        StrInput(
            name="librechat_base_url",
            display_name="LibreChat Base URL",
            value=os.environ.get("LIBRECHAT_BASE_URL", ""),
            advanced=True,
            info="Falls back to the LIBRECHAT_BASE_URL environment variable.",
        ),
        SecretStrInput(
            name="user_token",
            display_name="LibreChat Access Token",
            required=True,
            info=(
                "The LibreChat JWT (access_token) for the specific user whose memories "
                "this call should read or write. LibreChat's memories API is strictly "
                "per-user with no service-account bypass - this must be that user's own "
                "token; there is no way to derive it automatically from this flow's own "
                "identity."
            ),
        ),
        DropdownInput(
            name="operation",
            display_name="Operation",
            options=_OPERATIONS,
            value="List",
            info=(
                "List returns every memory. Get/Set/Delete act on one Key. "
                "Set creates the memory if it doesn't exist yet, otherwise updates it."
            ),
            real_time_refresh=True,
            tool_mode=True,
        ),
        MessageTextInput(
            name="key",
            display_name="Key",
            info="Required for Get, Set, and Delete.",
            tool_mode=True,
        ),
        MessageTextInput(
            name="value",
            display_name="Value",
            info="Required for Set.",
            tool_mode=True,
        ),
    ]

    outputs = [
        Output(display_name="Result", name="result", method="run_operation"),
    ]

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.user_token}", "Content-Type": "application/json"}

    def _memories_url(self, key: str | None = None) -> str:
        base = (self.librechat_base_url or "").rstrip("/")
        if not base:
            msg = "LibreChat Base URL is not configured (LIBRECHAT_BASE_URL)."
            raise ValueError(msg)
        if key:
            return f"{base}/api/memories/{key}"
        return f"{base}/api/memories"

    async def _ssrf_safe_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """PATCH/DELETE variant of the GET/POST helpers lfx.utils.ssrf_httpx already ships."""
        _sync_kwargs, async_kwargs = ssrf_protected_httpx_client_kwargs_for_url(url)
        async with httpx.AsyncClient(**async_kwargs) as client:
            return await client.request(method, url, **kwargs)

    async def run_operation(self) -> Data:
        operation = self.operation
        key = (self.key or "").strip()
        value = (self.value or "").strip()
        headers = self._headers()

        try:
            if operation == "List":
                response = await ssrf_safe_async_get(self._memories_url(), headers=headers)
            elif operation == "Get":
                if not key:
                    msg = "Key is required for Get."
                    raise ValueError(msg)  # noqa: TRY301
                list_response = await ssrf_safe_async_get(self._memories_url(), headers=headers)
                list_response.raise_for_status()
                memories = list_response.json().get("memories", [])
                match = next((m for m in memories if m.get("key") == key), None)
                result = Data(data={"memory": match} if match else {"error": f"Memory '{key}' not found."})
                self.status = result
                return result
            elif operation == "Set":
                if not key or not value:
                    msg = "Key and Value are both required for Set."
                    raise ValueError(msg)  # noqa: TRY301
                response = await ssrf_safe_async_post(
                    self._memories_url(), headers=headers, json={"key": key, "value": value}
                )
                if response.status_code == HTTP_STATUS_CONFLICT:
                    # Memory already exists under this key - Set is an upsert, so fall
                    # back to the update endpoint instead of surfacing the 409.
                    response = await self._ssrf_safe_request(
                        "PATCH", self._memories_url(key), headers=headers, json={"value": value}
                    )
            elif operation == "Delete":
                if not key:
                    msg = "Key is required for Delete."
                    raise ValueError(msg)  # noqa: TRY301
                response = await self._ssrf_safe_request("DELETE", self._memories_url(key), headers=headers)
            else:
                msg = f"Unknown operation: {operation}"
                raise ValueError(msg)  # noqa: TRY301

            response.raise_for_status()
            result = Data(data=response.json())
        except httpx.HTTPStatusError as exc:
            result = Data(data={"error": exc.response.text, "status_code": exc.response.status_code})
        except httpx.HTTPError as exc:
            result = Data(data={"error": str(exc)})

        self.status = result
        return result
