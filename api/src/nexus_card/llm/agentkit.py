"""Volcengine AgentKit (VeADK runtime) as a generation backend.

The agent deployed on AgentKit is deliberately **thin** — role and rules only, no embedded
knowledge. Retrieval runs on our side, and the retrieved passages travel with each turn as
part of the user message. That keeps `api/kb/` the single source of truth: knowledge lives
in git, gets reviewed in a PR, and is never edited in two places.

Wire protocol (from the reference proxy AgentKit ships):

    POST {base}/apps/{app}/users/{uid}/sessions/{sid}   -> create session (409 = exists)
    POST {base}/run_sse                                  -> SSE stream of ADK events

The SSE payload shape is not contractually pinned, so `_extract_text` reads defensively
across the shapes ADK-style runtimes are known to emit rather than assuming one.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
import structlog

from nexus_card.llm.base import LlmError
from nexus_card.models import ChatMessage

log = structlog.get_logger(__name__)


def _is_thought(part: Any) -> bool:
    """Reasoning tokens carry `thought: true` and must never reach the visitor.

    Measured against the live runtime: a four-character answer arrived as 178 thought
    fragments and 4 answer fragments. Without this filter the page renders the model's
    entire English reasoning monologue instead of the reply.
    """
    return isinstance(part, dict) and bool(part.get("thought"))


def _extract_text(event: Any) -> str:
    """Pull assistant text out of one ADK-style event, tolerating several shapes."""
    if isinstance(event, str):
        return event
    if not isinstance(event, dict):
        return ""

    # Errors surface as a plain object rather than a content event.
    if "error" in event and isinstance(event["error"], str):
        raise LlmError(event["error"])

    # {"content": {"parts": [{"text": "..."}]}}  — the common ADK shape
    content = event.get("content")
    if isinstance(content, dict):
        parts = content.get("parts")
        if isinstance(parts, list):
            return "".join(
                p.get("text", "")
                for p in parts
                if isinstance(p, dict) and p.get("text") and not _is_thought(p)
            )
    if isinstance(content, str):
        return content

    # Flatter variants seen in the wild.
    for key in ("delta", "text", "output_text"):
        value = event.get(key)
        if isinstance(value, str):
            return value

    parts = event.get("parts")
    if isinstance(parts, list):
        return "".join(
            p.get("text", "")
            for p in parts
            if isinstance(p, dict) and p.get("text") and not _is_thought(p)
        )
    return ""


class AgentKitProvider:
    name = "agentkit"

    def __init__(
        self,
        base_url: str,
        app_name: str,
        api_key: str,
        *,
        connect_timeout: float = 15.0,
        read_timeout: float = 120.0,
    ) -> None:
        missing = [
            key
            for key, value in (
                ("NEXUS_CARD_AGENTKIT_BASE_URL", base_url),
                ("NEXUS_CARD_AGENTKIT_APP_NAME", app_name),
                ("NEXUS_CARD_AGENTKIT_API_KEY", api_key),
            )
            if not value
        ]
        if missing:
            raise LlmError(f"AgentKit is not configured: {', '.join(missing)} unset")

        # The console shows the URL wrapped in backticks often enough to be worth stripping.
        self.base_url = base_url.strip().strip("`").rstrip("/")
        if not self.base_url.startswith(("http://", "https://")):
            raise LlmError("NEXUS_CARD_AGENTKIT_BASE_URL must start with http:// or https://")

        self.app_name = app_name
        self.model_id = f"agentkit:{app_name}"
        self._api_key = api_key
        self._timeout = httpx.Timeout(read_timeout, connect=connect_timeout)
        self._sessions: set[tuple[str, str]] = set()
        self._session_lock = asyncio.Lock()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
        }

    async def _ensure_session(
        self, client: httpx.AsyncClient, user_id: str, session_id: str
    ) -> None:
        key = (user_id, session_id)
        if key in self._sessions:
            return
        async with self._session_lock:
            if key in self._sessions:
                return
            url = (
                f"{self.base_url}/apps/{self.app_name}"
                f"/users/{user_id}/sessions/{session_id}"
            )
            try:
                response = await client.post(url, headers=self._headers(), json={})
            except httpx.HTTPError as exc:
                raise LlmError(f"AgentKit session create failed: {exc}") from exc
            # 409 means the session already exists remotely — after a restart, that is the
            # normal case, not an error.
            if response.status_code not in {200, 201, 409}:
                raise LlmError(f"AgentKit rejected session create ({response.status_code})")
            self._sessions.add(key)

    async def stream(
        self,
        system: str,
        messages: list[ChatMessage],
        *,
        max_tokens: int,
        temperature: float,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> AsyncIterator[str]:
        if not messages:
            return

        # AgentKit owns the conversation: its own short-term memory holds the history, so
        # only the newest turn is sent. The retrieved context rides along with it, because
        # the deployed agent carries no knowledge of its own.
        question = messages[-1].content
        text = f"{system}\n\n---\n\n访客提问：{question}" if system else question

        sid = session_id or "anon"
        uid = user_id or "visitor"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            await self._ensure_session(client, uid, sid)

            payload = {
                "app_name": self.app_name,
                "user_id": uid,
                "session_id": sid,
                "new_message": {"role": "user", "parts": [{"text": text}]},
                "streaming": True,
            }
            try:
                async with client.stream(
                    "POST", f"{self.base_url}/run_sse", headers=self._headers(), json=payload
                ) as response:
                    if response.status_code != 200:
                        detail = (await response.aread()).decode("utf-8", "replace")[:300]
                        raise LlmError(f"AgentKit {response.status_code}: {detail}")

                    emitted = ""
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        chunk = line[5:].strip()
                        if not chunk or chunk == "[DONE]":
                            continue
                        try:
                            event = json.loads(chunk)
                        except json.JSONDecodeError:
                            continue

                        # The runtime closes with a consolidated `partial: false` frame
                        # that repeats the entire answer. Measured live: streaming it too
                        # renders the reply twice. Use it only as a non-streaming fallback.
                        is_final = event.get("partial") is False
                        if is_final and emitted:
                            continue

                        piece = _extract_text(event)
                        if not piece:
                            continue
                        # Some runtimes stream cumulative text rather than deltas; emit only
                        # what is new so the page never shows the answer twice.
                        if piece.startswith(emitted) and len(piece) > len(emitted):
                            new, emitted = piece[len(emitted) :], piece
                            yield new
                        else:
                            emitted += piece
                            yield piece
            except httpx.HTTPError as exc:
                raise LlmError(f"AgentKit request failed: {exc}") from exc
