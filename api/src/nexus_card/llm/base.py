"""LLM provider interface.

One narrow contract — stream text deltas for a system prompt plus a message list — so the
bot can move between Bedrock (what the AgentCore runtime uses today), the Anthropic API,
and a deterministic echo provider for tests without touching the chat layer.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from nexus_card.models import ChatMessage


class LlmError(RuntimeError):
    """Provider failed in a way the caller should surface as `response.failed`."""


class LlmProvider(Protocol):
    name: str
    model_id: str

    def stream(
        self,
        system: str,
        messages: list[ChatMessage],
        *,
        max_tokens: int,
        temperature: float,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> AsyncIterator[str]:
        """Yield text deltas. Must raise `LlmError` on an unrecoverable failure.

        `session_id` / `user_id` are only meaningful for stateful runtimes (AgentKit keeps
        conversation memory server-side); stateless providers ignore them.
        """
        ...
