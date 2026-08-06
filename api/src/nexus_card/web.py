"""Serve the built SPA, with per-card Open Graph tags injected server-side.

A business-card link gets pasted into WhatsApp and LinkedIn constantly. A client-side SPA
renders a generic preview there because crawlers don't run JS — so the card's own name and
title are stamped into `index.html` on the way out. Cheap, and it is the difference between
a link that looks like a person and a link that looks like spam.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

import structlog
from fastapi import Request, Response
from fastapi.responses import FileResponse, HTMLResponse

from nexus_card.cards.store import CardStore
from nexus_card.models import Card

log = structlog.get_logger(__name__)

_HEAD_END = re.compile(r"</head>", re.IGNORECASE)
_SAFE_ASSET = re.compile(r"^[A-Za-z0-9._/-]+$")


def _meta_tags(card: Card, base_url: str) -> str:
    name = card.name.en
    if card.name.zh and card.name.zh != card.name.en:
        name = f"{card.name.en} {card.name.zh}"
    title = f"{name} — {card.title.en} | Nexus"
    description = (
        f"{card.title.en} · {card.org.en}. "
        "Nexus is the AI-native wealth operating system for EAMs and IFAs, "
        "built by Noah Holdings (NYSE: NOAH · HKEX: 6686)."
    )
    url = f"{base_url.rstrip('/')}/c/{card.slug}"
    e = html.escape
    return (
        f'<title>{e(title)}</title>\n'
        f'<meta name="description" content="{e(description)}">\n'
        f'<meta property="og:type" content="profile">\n'
        f'<meta property="og:title" content="{e(title)}">\n'
        f'<meta property="og:description" content="{e(description)}">\n'
        f'<meta property="og:url" content="{e(url)}">\n'
        f'<meta property="og:site_name" content="Nexus by Noah Holdings">\n'
        f'<meta property="og:image" content="{e(base_url.rstrip("/"))}/og-image.png">\n'
        f'<meta name="twitter:card" content="summary_large_image">\n'
        f'<meta name="twitter:title" content="{e(title)}">\n'
        f'<meta name="twitter:description" content="{e(description)}">\n'
        f'<link rel="canonical" href="{e(url)}">\n'
        f'<meta name="robots" content="noindex, nofollow">\n'
    )


class SpaHost:
    """Static assets from `dist/`, everything else falls through to `index.html`."""

    def __init__(self, dist_dir: Path, cards: CardStore, base_url: str, default_slug: str):
        self.dist_dir = dist_dir
        self.cards = cards
        self.base_url = base_url
        self.default_slug = default_slug

    @property
    def available(self) -> bool:
        return (self.dist_dir / "index.html").is_file()

    def _index_html(self) -> str:
        return (self.dist_dir / "index.html").read_text(encoding="utf-8")

    def asset(self, path: str) -> Response | None:
        if not _SAFE_ASSET.match(path) or ".." in path:
            return None
        candidate = (self.dist_dir / path).resolve()
        try:
            candidate.relative_to(self.dist_dir.resolve())
        except ValueError:
            return None
        if not candidate.is_file():
            return None
        immutable = "/assets/" in f"/{path}"
        return FileResponse(
            candidate,
            headers={
                "Cache-Control": (
                    "public, max-age=31536000, immutable" if immutable else "public, max-age=300"
                )
            },
        )

    def page(self, request: Request, slug: str | None) -> Response:
        if not self.available:
            return HTMLResponse(
                "<h1>Nexus card</h1><p>Frontend bundle not built. Run <code>make build</code>.</p>",
                status_code=503,
            )

        markup = self._index_html()
        card = self.cards.try_get(slug) or self.cards.try_get(self.default_slug)
        if card is not None:
            tags = _meta_tags(card, self.base_url)
            # Drop the placeholder <title> so we don't ship two.
            markup = re.sub(r"<title>.*?</title>\s*", "", markup, count=1, flags=re.DOTALL)
            markup = _HEAD_END.sub(tags + "</head>", markup, count=1)

        return HTMLResponse(
            markup,
            headers={"Cache-Control": "no-cache", "X-Frame-Options": "DENY"},
        )
