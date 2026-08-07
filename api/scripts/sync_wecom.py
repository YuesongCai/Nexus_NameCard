#!/usr/bin/env python3
"""Sync card profiles straight from the WeCom smart sheet.

This is the "card content is pluggable" half: colleagues fill the WeCom 收集表, and one
command turns that into `api/data/cards/*.json`. No CSV export, no copy-paste, no second
source of truth.

    python scripts/sync_wecom.py                 # dry run — report only
    python scripts/sync_wecom.py --write         # write card profiles
    python scripts/sync_wecom.py --write --prune # also delete cards no longer in the sheet

Then the rest of the pipeline:

    python scripts/export_static.py
    python scripts/gen_qr.py --png

Needs `wecom-cli` on PATH and authorised for 文档 (the bot's document permission expires
periodically — re-authorise in 企业微信 → 工作台 → 智能机器人 if this errors).

Rows are skipped unless 本人已确认无误 is 是: an unconfirmed row means the person has not
checked their own licence details, and those are the ones that force a reprint.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from nexus_card.cards.from_sheet import FIELD_MAP, build_card, check_duplicate_slugs
from nexus_card.config import get_settings

DEFAULT_DOC = (
    "dcDwo6yDTER4mWxT13nz4ygRl-cEX26S1ygKMuHdIXmzkrz_4VHfxM65CtauSli216YQ7sYD9t91PyFaNVm-KIog"
)
DEFAULT_SHEET = "q979lj"


def wecom(method: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Call one wecom-cli doc method and unwrap its double-encoded JSON envelope."""
    try:
        proc = subprocess.run(
            ["wecom-cli", "doc", method, "--json", json.dumps(payload, ensure_ascii=False)],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        raise SystemExit("wecom-cli 不在 PATH 上，装好再跑") from None
    except subprocess.TimeoutExpired:
        raise SystemExit(f"wecom-cli {method} 超时") from None

    if proc.returncode != 0:
        raise SystemExit(f"wecom-cli {method} 失败:\n{proc.stderr[:500]}")

    try:
        outer = json.loads(proc.stdout)
        inner = json.loads(outer["result"]["content"][0]["text"])
    except (json.JSONDecodeError, KeyError, IndexError) as exc:
        raise SystemExit(f"看不懂 wecom-cli 的返回: {exc}\n{proc.stdout[:400]}") from exc

    if inner.get("errcode") not in (0, None):
        message = inner.get("errmsg", "")
        if inner.get("errcode") == 851014 or "authorization" in message.lower():
            raise SystemExit(
                "企微机器人的「文档」权限已过期。\n"
                "到 企业微信 → 工作台 → 智能机器人 → 找到机器人 → 授权管理 → 开启「文档」，再重跑。"
            )
        raise SystemExit(f"企微返回错误 {inner.get('errcode')}: {message}")
    return inner


def cell_to_text(value: Any) -> str:
    """Flatten one smart-sheet cell to plain text across the shapes WeCom returns."""
    if value is None:
        return ""
    if isinstance(value, str | int | float):
        return str(value)
    if isinstance(value, dict):
        for key in ("text", "name", "link", "url"):
            if key in value and isinstance(value[key], str):
                return value[key]
        return ""
    if isinstance(value, list):
        # Text cells, select options and image cells all arrive as lists of objects;
        # joining with a comma is what the licence-type parser already expects.
        parts = [cell_to_text(item) for item in value]
        return ",".join(p for p in parts if p)
    return ""


def fetch_rows(docid: str, sheet_id: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    cursor = ""
    while True:
        payload: dict[str, Any] = {"docid": docid, "sheet_id": sheet_id, "limit": 200}
        if cursor:
            payload["cursor"] = cursor
        data = wecom("smartsheet_get_records", payload)

        for record in data.get("records", []):
            values = record.get("values", {})
            row: dict[str, str] = {}
            for header, key in FIELD_MAP.items():
                # Headers in the sheet may carry the `*` required marker.
                raw = values.get(header, values.get(f"{header} *"))
                row[key] = cell_to_text(raw).strip()
            rows.append(row)

        cursor = data.get("next_cursor") or ""
        if not cursor or not data.get("has_more"):
            break
    return rows


def main() -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser()
    parser.add_argument("--docid", default=DEFAULT_DOC)
    parser.add_argument("--sheet-id", default=DEFAULT_SHEET)
    parser.add_argument("--write", action="store_true", help="真正写入 card profiles")
    parser.add_argument(
        "--prune",
        action="store_true",
        help="删除表里已不存在的 card（默认保留，避免误删手工维护的卡）",
    )
    parser.add_argument("--out", type=Path, default=settings.cards_dir)
    args = parser.parse_args()

    print(f"读取企微智能表格 {args.sheet_id} …")
    rows = fetch_rows(args.docid, args.sheet_id)
    print(f"取到 {len(rows)} 行")

    problems: list[str] = []
    cards: list[dict[str, Any]] = []
    skipped: list[str] = []

    for row in rows:
        name = row.get("name_en", "")
        # The two seeded example rows are prefixed 【示例】 and must never become cards.
        if name.startswith("【示例】"):
            continue
        if row.get("confirmed") != "是":
            if name or row.get("slug"):
                skipped.append(name or row.get("slug", ""))
            continue
        card = build_card(row, problems)
        if card:
            cards.append(card)

    check_duplicate_slugs(cards, problems)

    print(f"\n可导入 {len(cards)} 人")
    for card in cards:
        variant = "B版持牌" if card["variant"] == "licensed" else "A版"
        wechat = card["contacts"].get("wechat") or {}
        mark = "微信✓" if wechat.get("id") else "微信✗"
        print(f"  · {card['slug']:<16} {card['name']['en']:<20} {variant:<8} {mark}")

    if skipped:
        print(f"\n跳过 {len(skipped)} 行（未勾「本人已确认无误」）: {', '.join(skipped)}")

    if problems:
        print(f"\n⚠️  {len(problems)} 个问题：", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)

    if not args.write:
        print("\n（dry run —— 加 --write 才会写入）")
        return 1 if problems else 0

    if problems:
        print("\n有问题未解决，拒绝写入。修好企微表再跑一次。", file=sys.stderr)
        return 2

    args.out.mkdir(parents=True, exist_ok=True)
    written = set()
    for card in cards:
        path = args.out / f"{card['slug']}.json"
        path.write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.add(path.name)
    print(f"\n已写入 {len(cards)} 个 card profile → {args.out}")

    if args.prune:
        # `nexus` is the company fallback card and is maintained by hand, never by the sheet.
        keep = written | {"nexus.json"}
        for path in args.out.glob("*.json"):
            if path.name not in keep:
                path.unlink()
                print(f"  已删除 {path.name}（表里已不存在）")

    print("\n接着跑：")
    print("  python scripts/export_static.py")
    print("  python scripts/gen_qr.py --png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
