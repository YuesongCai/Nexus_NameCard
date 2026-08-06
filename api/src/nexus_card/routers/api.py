"""HTTP surface: card profiles, vCard, suggestions, chat (SSE) and analytics."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from sse_starlette.sse import EventSourceResponse

from nexus_card.cards.store import CardNotFound
from nexus_card.cards.vcard import render_vcard, vcard_filename
from nexus_card.models import AnalyticsEvent, Card, ChatRequest, Lang
from nexus_card.ratelimit import client_key
from nexus_card.suggestions import greeting_for, suggestions_for

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api")


def _state(request: Request) -> Any:
    return request.app.state


def _card_or_404(request: Request, slug: str) -> Card:
    try:
        return _state(request).cards.get(slug)
    except CardNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="card not found") from exc


@router.get("/cards/{slug}")
def get_card(request: Request, slug: str) -> dict[str, Any]:
    card = _card_or_404(request, slug)
    return card.model_dump(by_alias=True, exclude_none=True)


@router.get("/cards/{slug}/vcard")
def get_vcard(
    request: Request,
    slug: str,
    lang: Annotated[Lang, Query()] = "en",
) -> Response:
    card = _card_or_404(request, slug)
    body = render_vcard(card, lang)
    return Response(
        content=body.encode("utf-8"),
        media_type="text/vcard; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{vcard_filename(card)}"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/cards/{slug}/intro")
def get_intro(
    request: Request,
    slug: str,
    lang: Annotated[Lang, Query()] = "en",
) -> dict[str, Any]:
    """Greeting + starter chips — one round trip so the chat renders complete."""
    card = _state(request).cards.try_get(slug)
    return {
        "greeting": greeting_for(card, lang),
        "suggestions": [s.model_dump() for s in suggestions_for(card, lang)],
    }


@router.post("/chat")
async def chat(request: Request, payload: ChatRequest) -> EventSourceResponse:
    state = _state(request)
    if not state.limiter.allow(client_key(request)):
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many questions in a short time. Give it a moment.",
        )

    card = state.cards.try_get(payload.slug)
    log.info(
        "chat.ask",
        slug=payload.slug,
        lang=payload.lang,
        chars=len(payload.question),
        session=payload.session_id,
    )

    async def frames() -> AsyncIterator[dict[str, str]]:
        async for envelope in state.chat.stream(payload, card):
            yield {"data": envelope}

    return EventSourceResponse(
        frames(),
        headers={
            "Cache-Control": "no-cache, no-transform",
            # Nginx/ALB buffering is what turns a streaming answer into a 20s freeze.
            "X-Accel-Buffering": "no",
        },
        ping=15,
    )


@router.post("/events", status_code=status.HTTP_204_NO_CONTENT)
def post_event(request: Request, payload: AnalyticsEvent) -> Response:
    """Product analytics only — no PII, no question bodies, no cookies."""
    log.info(
        "card.event",
        event=payload.name,
        slug=payload.slug,
        detail=payload.detail,
        session=payload.session_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/healthz")
def healthz(request: Request) -> dict[str, Any]:
    state = _state(request)
    return {
        "status": "ok",
        "chunks": len(state.retriever.chunks),
        "cards": len(state.cards.slugs()),
        "provider": state.chat.provider.name,
    }
