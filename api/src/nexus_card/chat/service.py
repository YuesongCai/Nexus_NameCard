"""The Ask Nexus turn: retrieve → prompt → stream → emit §6-shaped events."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import structlog
from ulid import ULID

from nexus_card.chat.events import EventStream
from nexus_card.chat.prompt import build_system_prompt, fallback_answer
from nexus_card.config import Settings
from nexus_card.llm.base import LlmError, LlmProvider
from nexus_card.models import Card, ChatMessage, ChatRequest, Lang
from nexus_card.rag.retriever import Hit, Retriever

log = structlog.get_logger(__name__)


class ChatService:
    def __init__(
        self, settings: Settings, retriever: Retriever, provider: LlmProvider
    ) -> None:
        self.settings = settings
        self.retriever = retriever
        self.provider = provider

    def _messages(self, request: ChatRequest) -> list[ChatMessage]:
        history = [m for m in request.history if m.content.strip()]
        history = history[-(self.settings.max_history_turns * 2) :]
        question = request.question[: self.settings.max_question_chars]
        return [*history, ChatMessage(role="user", content=question)]

    async def stream(self, request: ChatRequest, card: Card | None) -> AsyncIterator[str]:
        run_id = f"run_{ULID()}"
        events = EventStream(run_id=run_id, model=getattr(self.provider, "model_id", "n/a"))
        yield _frame(events.created())

        # Retrieval is CPU-bound and fast (small KB, in-process); no need to offload.
        hits = self.retriever.search(request.question)
        yield _frame(events.sources(_source_chips(hits, request.lang)))

        system = build_system_prompt(card, request.lang, self.retriever.as_context(hits))
        messages = self._messages(request)

        emitted = False
        try:
            async for delta in self.provider.stream(
                system,
                messages,
                max_tokens=self.settings.llm_max_tokens,
                temperature=self.settings.llm_temperature,
                # Stateful runtimes (AgentKit) key their own memory off these; the
                # stateless providers ignore them.
                session_id=request.session_id,
                user_id=request.slug or "visitor",
            ):
                emitted = True
                yield _frame(events.delta(delta))
        except LlmError as exc:
            log.warning("chat.llm_failed", run_id=run_id, error=str(exc))
            if not emitted:
                # Degrade to a useful hand-off rather than an empty bubble.
                yield _frame(events.delta(fallback_answer(card, request.lang)))
                yield _frame(events.completed())
                return
            yield _frame(events.failed("llm_error", code="upstream_unavailable"))
            return
        except Exception as exc:
            log.error("chat.unexpected", run_id=run_id, error=str(exc))
            yield _frame(events.failed("internal_error"))
            return

        if not emitted:
            yield _frame(events.delta(fallback_answer(card, request.lang)))
        yield _frame(events.completed())


def _source_chips(hits: list[Hit], lang: Lang) -> list[dict[str, Any]]:
    """One chip per source document, in the reader's language.

    Chunk headings are bilingual and uneven ("01 · Workspace / 工作台"), which reads as
    noise under an answer. Document titles are written as "English / 中文", so splitting on
    the separator gives a clean, short label on either side.
    """
    chips: list[dict[str, Any]] = []
    seen: set[str] = set()
    for hit in hits:
        if hit.chunk.doc_id in seen:
            continue
        seen.add(hit.chunk.doc_id)
        title = hit.chunk.title
        if " / " in title:
            english, _, chinese = title.partition(" / ")
            title = (chinese if lang == "zh" else english).strip()
        chips.append({"id": hit.chunk.doc_id, "title": title, "score": round(hit.score, 4)})
    return chips


def _frame(envelope: dict[str, Any]) -> str:
    """One JSON envelope, serialised.

    The transport writes it as a bare `data: {...}` line — the same wire shape AgentCore
    Runtime produces, so the frontend parser works against either backend unchanged.
    """
    return json.dumps(envelope, ensure_ascii=False)
