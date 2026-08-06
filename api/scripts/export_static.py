#!/usr/bin/env python3
"""Pre-render every API response a static host needs.

GitHub Pages can't run FastAPI, but almost nothing on this page actually needs a server at
request time: the card, the greeting, the starter chips and the vCard are all pure
functions of a card profile. So they get evaluated once at build time and written into
`web/public/`, which Vite copies verbatim into `dist/`.

Deliberately reuses `render_vcard` / `greeting_for` / `suggestions_for` rather than
reimplementing them in JS — one source of truth, and the static build can never drift from
what the live API serves.

    python scripts/export_static.py [--out ../web/public]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, get_args

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from nexus_card.cards.store import CardStore
from nexus_card.cards.vcard import render_vcard
from nexus_card.config import get_settings
from nexus_card.models import Lang
from nexus_card.suggestions import greeting_for, suggestions_for

LANGS: tuple[Lang, ...] = get_args(Lang)


def main() -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent.parent.parent / "web" / "public",
        help="Directory Vite copies into dist/ (default: web/public)",
    )
    args = parser.parse_args()

    store = CardStore(settings.cards_dir)
    slugs = store.slugs()
    if not slugs:
        print(f"No cards found in {settings.cards_dir}", file=sys.stderr)
        return 1

    cards_out = args.out / "data" / "cards"
    intro_out = args.out / "data" / "intro"
    vcard_out = args.out / "vcard"

    # Rebuild from scratch: a card deleted from data/ must disappear from the deploy too.
    for directory in (cards_out, intro_out, vcard_out):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True, exist_ok=True)

    manifest: list[dict[str, Any]] = []

    for slug in slugs:
        card = store.get(slug)
        payload = card.model_dump(by_alias=True, exclude_none=True)
        (cards_out / f"{slug}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        for lang in LANGS:
            intro = {
                "greeting": greeting_for(card, lang),
                "suggestions": [s.model_dump() for s in suggestions_for(card, lang)],
            }
            (intro_out / f"{slug}.{lang}.json").write_text(
                json.dumps(intro, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (vcard_out / f"{slug}.{lang}.vcf").write_text(
                render_vcard(card, lang), encoding="utf-8", newline=""
            )

        manifest.append(
            {
                "slug": slug,
                "nameEn": card.name.en,
                "nameZh": card.name.zh,
                "titleEn": card.title.en,
                "orgEn": card.org.en,
            }
        )

    (args.out / "data" / "cards.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Exported {len(slugs)} card(s) × {len(LANGS)} language(s) → {args.out}")
    for slug in slugs:
        print(f"  · {slug}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
