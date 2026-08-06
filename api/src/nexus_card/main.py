"""FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from nexus_card.cards.store import CardStore
from nexus_card.chat.service import ChatService
from nexus_card.config import Settings, get_settings
from nexus_card.llm.providers import build_provider
from nexus_card.rag.retriever import Retriever
from nexus_card.ratelimit import RateLimiter
from nexus_card.routers.api import router as api_router
from nexus_card.web import SpaHost

log = structlog.get_logger(__name__)


def configure_logging(settings: Settings) -> None:
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer()
            if settings.is_prod
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper(), logging.INFO)
        ),
        cache_logger_on_first_use=True,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = settings
        app.state.cards = CardStore(settings.cards_dir)
        app.state.retriever = Retriever(settings)
        app.state.limiter = RateLimiter(settings.rate_limit_per_min, settings.rate_limit_burst)
        app.state.chat = ChatService(
            settings, app.state.retriever, build_provider(settings)
        )
        app.state.spa = SpaHost(
            settings.web_dist_dir,
            app.state.cards,
            settings.public_base_url,
            settings.default_card_slug,
        )
        log.info(
            "app.ready",
            env=settings.env,
            provider=settings.llm_provider,
            spa=app.state.spa.available,
        )
        yield

    app = FastAPI(
        title="Nexus Card",
        version="1.0.0",
        docs_url=None if settings.is_prod else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_prod else "/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["content-type"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        return response

    app.include_router(api_router)

    @app.get("/c/{slug}", include_in_schema=False)
    def card_page(request: Request, slug: str) -> Response:
        return request.app.state.spa.page(request, slug)

    @app.get("/", include_in_schema=False)
    def root(request: Request) -> Response:
        return request.app.state.spa.page(request, None)

    @app.get("/{path:path}", include_in_schema=False)
    def catch_all(request: Request, path: str) -> Response:
        asset = request.app.state.spa.asset(path)
        if asset is not None:
            return asset
        return request.app.state.spa.page(request, None)

    return app


app = create_app()
