#!/usr/bin/env python3
"""Turn the Feishu collection sheet into card profiles.

The spreadsheet is the source of truth for who exists and what goes on their card; this
script is the one-way door from that sheet into `data/cards/*.json`. Run it after a
collection round and the whole pipeline follows: profiles → static export → QR codes.

    # Export "② 信息收集表" from Feishu as CSV, then:
    python scripts/import_sheet.py --csv ~/Downloads/collection.csv
    python scripts/import_sheet.py --csv ~/Downloads/collection.csv --write

Without `--write` it only reports what it would do — rows are written by real colleagues,
so a dry run first is the difference between catching a malformed phone number and
publishing it.

Rows are skipped unless column X (本人已确认无误) is 是: an unconfirmed row means the person
has not checked their own licence details, and those are the ones that force a reprint.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from nexus_card.cards.from_sheet import build_card, check_duplicate_slugs
from nexus_card.config import get_settings

# Column order in the exported CSV. The mapping and validation live in
# `nexus_card.cards.from_sheet` so this path and the WeCom API path cannot drift.
COLUMNS = [
    "_seq", "variant", "name_en", "name_zh", "title_en", "title_zh", "email",
    "phone_hk", "phone_cn", "whatsapp", "wechat_id", "wechat_qr",
    "org_en", "org_zh", "location", "ce_number", "licence_types",
    "entity_en", "entity_ce", "addr_en", "addr_zh",
    "slug", "default_lang", "_print_qty", "confirmed", "_date", "note",
]


def row_to_dict(row: list[str]) -> dict[str, str]:
    return {key: (row[i].strip() if i < len(row) else "") for i, key in enumerate(COLUMNS)}


def main() -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, required=True, help="导出的「② 信息收集表」CSV")
    parser.add_argument("--write", action="store_true", help="真正写入 card JSON")
    parser.add_argument("--out", type=Path, default=settings.cards_dir)
    args = parser.parse_args()

    if not args.csv.is_file():
        print(f"找不到文件: {args.csv}", file=sys.stderr)
        return 1

    with args.csv.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))

    problems: list[str] = []
    cards: list[dict[str, Any]] = []
    skipped: list[str] = []

    # Rows 1-4 are header, hint and the two example rows.
    for raw in rows[4:]:
        if not any(c.strip() for c in raw):
            continue
        row = row_to_dict(raw)
        if row["confirmed"] != "是":
            name = row["name_en"] or row["slug"]
            if name:
                skipped.append(name)
            continue
        card = build_card(row, problems)
        if card:
            cards.append(card)

    check_duplicate_slugs(cards, problems)

    print(f"可导入 {len(cards)} 人")
    for card in cards:
        variant = "B版持牌" if card["variant"] == "licensed" else "A版"
        print(f"  · {card['slug']:<16} {card['name']['en']:<20} {variant}")

    if skipped:
        names = ", ".join(skipped)
        print(f"\n跳过 {len(skipped)} 行（未勾「本人已确认无误」）: {names}")

    if problems:
        print(f"\n⚠️  {len(problems)} 个问题：", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)

    if not args.write:
        print("\n（dry run —— 加 --write 才会写入）")
        return 1 if problems else 0

    if problems:
        print("\n有问题未解决，拒绝写入。修好表格再跑一次。", file=sys.stderr)
        return 2

    args.out.mkdir(parents=True, exist_ok=True)
    for card in cards:
        path = args.out / f"{card['slug']}.json"
        path.write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n已写入 {len(cards)} 个 card profile → {args.out}")
    print("接着跑：python scripts/export_static.py && python scripts/gen_qr.py --png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
