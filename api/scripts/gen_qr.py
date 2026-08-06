#!/usr/bin/env python3
"""Generate one QR code per person, ready to hand to the printer.

Every colleague gets their own URL (`/c/<slug>`) and therefore their own QR — they are not
interchangeable, and a card printed with the wrong one points at the wrong person. So this
reads the card profiles as the single source of truth and emits a file per slug, plus a
manifest the print vendor can check against.

    python scripts/gen_qr.py --base-url https://card.noahnexus.ai
    python scripts/gen_qr.py --base-url https://card.noahnexus.ai --slug frankxiao

SVG is the default because business cards are printed from vector artwork; `--png` also
emits a raster copy for slide decks and previews.

Requires `segno` (pure Python, no native deps): pip install segno
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from nexus_card.cards.store import CardStore
from nexus_card.config import get_settings

# Brand ink on brand stock. Error correction M survives a card being handled and scuffed;
# H would be more robust but inflates the module count and shrinks the printed modules.
DARK = "#0A0C08"
LIGHT = "#F4F1EA"
ERROR_LEVEL = "m"


def main() -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        default="https://yuesongcai.github.io/Nexus_NameCard",
        help="Public origin (plus base path) the QR should point at",
    )
    parser.add_argument("--slug", action="append", help="Only this slug (repeatable)")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent.parent.parent / "qr",
        help="Output directory (default: <repo>/qr)",
    )
    parser.add_argument("--png", action="store_true", help="Also emit PNG alongside SVG")
    parser.add_argument("--scale", type=int, default=12, help="PNG module scale")
    args = parser.parse_args()

    try:
        import segno
    except ImportError:
        print("segno is required: pip install segno", file=sys.stderr)
        return 1

    store = CardStore(settings.cards_dir)
    slugs = args.slug or store.slugs()
    if not slugs:
        print(f"No cards found in {settings.cards_dir}", file=sys.stderr)
        return 1

    base = args.base_url.rstrip("/")
    args.out.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, str]] = []

    for slug in slugs:
        try:
            card = store.get(slug)
        except KeyError:
            print(f"  ! unknown slug: {slug}", file=sys.stderr)
            continue

        url = f"{base}/c/{card.slug}"
        qr = segno.make(url, error=ERROR_LEVEL)

        svg_path = args.out / f"{card.slug}.svg"
        qr.save(svg_path, scale=10, dark=DARK, light=LIGHT, border=3)
        written = [svg_path.name]

        if args.png:
            png_path = args.out / f"{card.slug}.png"
            qr.save(png_path, scale=args.scale, dark=DARK, light=LIGHT, border=3)
            written.append(png_path.name)

        manifest.append(
            {
                "slug": card.slug,
                "name_en": card.name.en,
                "name_zh": card.name.zh,
                "variant": card.variant,
                "url": url,
                "files": " + ".join(written),
            }
        )
        print(f"  · {card.slug:<16} {url}")

    # The manifest is the artefact the print vendor and the card owner sign off against:
    # it pairs a person with the exact URL their QR encodes.
    manifest_path = args.out / "manifest.csv"
    with manifest_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["slug", "name_en", "name_zh", "variant", "url", "files"]
        )
        writer.writeheader()
        writer.writerows(manifest)

    print(f"\n{len(manifest)} QR code(s) → {args.out}")
    print(f"manifest → {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
