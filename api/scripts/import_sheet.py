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
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from nexus_card.config import get_settings

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
PHONE_RE = re.compile(r"^\+\d[\d ]{5,}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Column letter → meaning, mirroring 「③ 字段说明」. Positional so a renamed header does
# not silently shift every field.
COLS = {
    "variant": 1, "name_en": 2, "name_zh": 3, "title_en": 4, "title_zh": 5,
    "email": 6, "phone_hk": 7, "phone_cn": 8, "whatsapp": 9,
    "wechat_id": 10, "wechat_qr": 11,
    "org_en": 12, "org_zh": 13, "location": 14, "ce_number": 15, "licence_types": 16,
    "entity_en": 17, "entity_ce": 18, "addr_en": 19, "addr_zh": 20,
    "slug": 21, "confirmed": 24,
}

SFC_TYPES = {
    "1": ("Dealing in Securities", "证券交易"),
    "2": ("Dealing in Futures Contracts", "期货合约交易"),
    "3": ("Leveraged Foreign Exchange Trading", "杠杆式外汇交易"),
    "4": ("Advising on Securities", "就证券交易提供意见"),
    "5": ("Advising on Futures Contracts", "就期货合约提供意见"),
    "6": ("Advising on Corporate Finance", "就机构融资提供意见"),
    "7": ("Providing Automated Trading Services", "提供自动化交易服务"),
    "8": ("Securities Margin Financing", "提供证券保证金融资"),
    "9": ("Asset Management", "提供资产管理"),
    "10": ("Providing Credit Rating Services", "提供信贷评级服务"),
}

MEMBER_LINE = {
    "en": "A member firm of Noah (US: NOAH · HK: 6686)",
    "zh": "诺亚控股成员企业（美股 NOAH · 港股 6686）",
}


def cell(row: list[str], key: str) -> str:
    idx = COLS[key]
    return row[idx].strip() if idx < len(row) else ""


def build_card(row: list[str], problems: list[str]) -> dict[str, Any] | None:
    slug = cell(row, "slug").lower()
    name_en = cell(row, "name_en")
    if not slug and not name_en:
        return None  # genuinely blank row

    who = name_en or slug or "(unnamed row)"

    # Every check runs before bailing out, so one pass reports everything wrong with the
    # row. Fixing a typo only to rediscover three more on the next run is how a collection
    # round turns into a week of back-and-forth.
    slug_ok = bool(SLUG_RE.match(slug))
    if not slug_ok:
        problems.append(f"{who}: slug 不合法（只能小写字母/数字/连字符）: {slug!r}")

    for field, label in (("name_en", "英文名"), ("name_zh", "中文名"),
                         ("title_en", "职位英文"), ("title_zh", "职位中文")):
        if not cell(row, field):
            problems.append(f"{who}: 缺 {label}")

    email = cell(row, "email")
    if email and not EMAIL_RE.match(email):
        problems.append(f"{who}: 邮箱格式可疑: {email}")

    phones = []
    for field, label_en, label_zh in (
        ("phone_hk", "HK-M", "香港手机"),
        ("phone_cn", "CN-M", "内地手机"),
    ):
        value = cell(row, field)
        if not value:
            continue
        if not PHONE_RE.match(value):
            problems.append(f"{who}: {label_zh}不是国际格式（要 + 开头）: {value}")
        phones.append({"label": {"en": label_en, "zh": label_zh}, "value": value})

    # WeChat replaced LinkedIn on the card. There is no add-friend URL, so what the page
    # needs is an ID to copy and (optionally) an exported 个人二维码 image.
    wechat_id = cell(row, "wechat_id")
    wechat_qr = cell(row, "wechat_qr")
    if wechat_id.startswith("wxid_"):
        problems.append(
            f"{who}: 微信号是系统默认的 wxid_ 串（搜不到），请本人到微信设置里设一个微信号"
        )
    wechat = None
    if wechat_id or wechat_qr:
        # Colleagues type a bare filename; the page needs a path under the site base.
        qr_path = f"wechat/{wechat_qr}" if wechat_qr and "/" not in wechat_qr else wechat_qr
        wechat = {"id": wechat_id or None, "qr": qr_path or None}

    licensed = cell(row, "variant").startswith("B")
    whatsapp = cell(row, "whatsapp") or cell(row, "phone_hk")

    card: dict[str, Any] = {
        "slug": slug,
        "variant": "licensed" if licensed else "standard",
        "coBrand": "ark" if licensed else None,
        "name": {"en": name_en, "zh": cell(row, "name_zh")},
        "title": {"en": cell(row, "title_en"), "zh": cell(row, "title_zh")},
        "org": {"en": cell(row, "org_en"), "zh": cell(row, "org_zh")},
        "location": {"en": cell(row, "location"), "zh": cell(row, "location")},
        "contacts": {
            "whatsapp": whatsapp.replace(" ", "") or None,
            "wechat": wechat,
            "phones": phones,
            "email": email or None,
            "linkedin": None,
            "website": "https://noahnexus.ai",
        },
        "licence": None,
        "memberLine": MEMBER_LINE,
    }

    if licensed:
        codes = [c.strip() for c in cell(row, "licence_types").replace("/", ",").split(",")]
        types = []
        for code in filter(None, codes):
            if code not in SFC_TYPES:
                problems.append(f"{who}: 未知持牌类别 {code!r}（只能 1–10）")
                continue
            en, zh = SFC_TYPES[code]
            types.append({"code": code, "en": en, "zh": zh})

        if not cell(row, "ce_number"):
            problems.append(f"{who}: B 版但没有 SFC 中央编号")
        if not types:
            problems.append(f"{who}: B 版但没有持牌类别")

        card["licence"] = {
            "ceNumber": cell(row, "ce_number"),
            "entityCeNumber": cell(row, "entity_ce") or None,
            "entity": {"en": cell(row, "entity_en"), "zh": cell(row, "entity_en")},
            "regulator": {"en": "SFC", "zh": "香港证监会"},
            "types": types,
            "address": {"en": cell(row, "addr_en"), "zh": cell(row, "addr_zh")},
        }

    return card if slug_ok else None


def main() -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, required=True, help="Exported 「② 信息收集表」 CSV")
    parser.add_argument("--write", action="store_true", help="Actually write card JSON files")
    parser.add_argument("--out", type=Path, default=settings.cards_dir)
    args = parser.parse_args()

    if not args.csv.is_file():
        print(f"No such file: {args.csv}", file=sys.stderr)
        return 1

    with args.csv.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))

    problems: list[str] = []
    cards: list[dict[str, Any]] = []
    skipped_unconfirmed: list[str] = []

    # Rows 1–4 are header, hint and the two example rows.
    for row in rows[4:]:
        if not any(c.strip() for c in row):
            continue
        if cell(row, "confirmed") != "是":
            name = cell(row, "name_en") or cell(row, "slug")
            if name:
                skipped_unconfirmed.append(name)
            continue
        card = build_card(row, problems)
        if card:
            cards.append(card)

    seen: dict[str, int] = {}
    for card in cards:
        seen[card["slug"]] = seen.get(card["slug"], 0) + 1
    for slug, count in seen.items():
        if count > 1:
            problems.append(f"slug 重复 {count} 次: {slug} —— 每人必须唯一")

    print(f"可导入 {len(cards)} 人")
    for card in cards:
        variant = "B版持牌" if card["variant"] == "licensed" else "A版"
        print(f"  · {card['slug']:<16} {card['name']['en']:<20} {variant}")

    if skipped_unconfirmed:
        names = ", ".join(skipped_unconfirmed)
        print(f"\n跳过 {len(skipped_unconfirmed)} 行（X 列未选「是」）: {names}")

    if problems:
        print(f"\n⚠️  {len(problems)} 个问题：", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)

    if not args.write:
        print("\n（dry run —— 加 --write 才会真正写入）")
        return 1 if problems else 0

    if problems:
        print("\n有问题未解决，拒绝写入。修好表格再跑一次。", file=sys.stderr)
        return 2

    args.out.mkdir(parents=True, exist_ok=True)
    for card in cards:
        path = args.out / f"{card['slug']}.json"
        path.write_text(
            json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(f"\n已写入 {len(cards)} 个 card profile → {args.out}")
    print("接着跑：python scripts/export_static.py && python scripts/gen_qr.py --png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
