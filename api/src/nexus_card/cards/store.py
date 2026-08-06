"""Card profiles, loaded from JSON on disk.

Adding a colleague is dropping a file in `data/cards/` — no code change, no migration. The
store hot-reloads on mtime so a redeploy isn't needed to fix a typo in someone's title.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import structlog
from pydantic import ValidationError

from nexus_card.models import Card

log = structlog.get_logger(__name__)

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


class CardNotFound(KeyError):
    pass


class CardStore:
    def __init__(self, cards_dir: Path) -> None:
        self.cards_dir = cards_dir
        self._cache: dict[str, tuple[float, Card]] = {}

    def _path(self, slug: str) -> Path:
        return self.cards_dir / f"{slug}.json"

    def get(self, slug: str) -> Card:
        slug = slug.strip().lower()
        if not SLUG_RE.match(slug):
            raise CardNotFound(slug)

        path = self._path(slug)
        if not path.is_file():
            raise CardNotFound(slug)

        mtime = path.stat().st_mtime
        cached = self._cache.get(slug)
        if cached and cached[0] == mtime:
            return cached[1]

        try:
            card = Card.model_validate(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            log.error("cards.invalid", slug=slug, error=str(exc))
            raise CardNotFound(slug) from exc

        self._cache[slug] = (mtime, card)
        return card

    def try_get(self, slug: str | None) -> Card | None:
        if not slug:
            return None
        try:
            return self.get(slug)
        except CardNotFound:
            return None

    def slugs(self) -> list[str]:
        return sorted(p.stem for p in self.cards_dir.glob("*.json"))
