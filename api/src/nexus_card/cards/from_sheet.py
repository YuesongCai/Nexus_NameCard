"""Turn one collected sheet row into a card profile.

Both intake paths land here — the WeCom smart sheet (read live over the API) and a CSV
export from Feishu — so the field mapping and the validation exist exactly once. Two
copies of this logic would drift, and the failure mode is a card that prints wrong.

Keyed by **field name**, not column position, so reordering columns in either sheet is
harmless.
"""

from __future__ import annotations

import re
from typing import Any

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
PHONE_RE = re.compile(r"^\+\d[\d ]{5,}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

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

# Sheet column header → internal key. Both sheets use these headers verbatim.
FIELD_MAP = {
    "名片版本": "variant",
    "英文名": "name_en",
    "中文名": "name_zh",
    "职位（英文）": "title_en",
    "职位（中文）": "title_zh",
    "邮箱": "email",
    "香港手机 HK-M": "phone_hk",
    "内地手机 CN-M": "phone_cn",
    "WhatsApp 号码": "whatsapp",
    "微信号": "wechat_id",
    "微信二维码图片": "wechat_qr",
    "所属机构（英文）": "org_en",
    "所属机构（中文）": "org_zh",
    "常驻地": "location",
    "SFC 中央编号（本人）": "ce_number",
    "持牌类别": "licence_types",
    "持牌法团（英文）": "entity_en",
    "法团中央编号": "entity_ce",
    "办公地址（英文）": "addr_en",
    "办公地址（中文）": "addr_zh",
    "页面链接后缀 slug": "slug",
    "页面默认语言": "default_lang",
    "本人已确认无误": "confirmed",
    "备注": "note",
}


def normalise_headers(headers: list[str]) -> list[str]:
    """Map sheet headers to internal keys, tolerating the `*` required-marker and spacing."""
    out = []
    for header in headers:
        clean = header.replace("*", "").strip()
        out.append(FIELD_MAP.get(clean, f"_unmapped:{clean}"))
    return out


def build_card(row: dict[str, str], problems: list[str]) -> dict[str, Any] | None:
    """Validate one row and return a card profile, or None if it cannot be used.

    Every check runs before returning, so one pass reports everything wrong with the row.
    Fixing one typo only to rediscover three more is how a collection round turns into a
    week of back-and-forth.
    """
    get = lambda key: (row.get(key) or "").strip()  # noqa: E731

    slug = get("slug").lower()
    name_en = get("name_en")
    if not slug and not name_en:
        return None

    who = name_en or slug or "(未命名行)"

    slug_ok = bool(SLUG_RE.match(slug))
    if not slug_ok:
        problems.append(f"{who}: slug 不合法（只能小写字母/数字/连字符）: {slug!r}")

    for key, label in (
        ("name_en", "英文名"),
        ("name_zh", "中文名"),
        ("title_en", "职位英文"),
        ("title_zh", "职位中文"),
    ):
        if not get(key):
            problems.append(f"{who}: 缺 {label}")

    email = get("email")
    if email and not EMAIL_RE.match(email):
        problems.append(f"{who}: 邮箱格式可疑: {email}")

    phones = []
    for key, label_en, label_zh in (
        ("phone_hk", "HK-M", "香港手机"),
        ("phone_cn", "CN-M", "内地手机"),
    ):
        value = get(key)
        if not value:
            continue
        if not PHONE_RE.match(value):
            problems.append(f"{who}: {label_zh}不是国际格式（要 + 开头）: {value}")
        phones.append({"label": {"en": label_en, "zh": label_zh}, "value": value})

    # WeChat replaced LinkedIn on the card. There is no add-friend URL, so what the page
    # needs is an ID to copy and optionally an exported 个人二维码.
    wechat_id = get("wechat_id")
    wechat_qr = get("wechat_qr")
    if wechat_id.startswith("wxid_"):
        problems.append(
            f"{who}: 微信号是系统默认的 wxid_ 串（搜不到），请本人到微信设置里设一个微信号"
        )
    wechat = None
    if wechat_id or wechat_qr:
        # Colleagues give a bare filename; the page needs a path under the site base.
        qr_path = f"wechat/{wechat_qr}" if wechat_qr and "/" not in wechat_qr else wechat_qr
        wechat = {"id": wechat_id or None, "qr": qr_path or None}

    licensed = get("variant").startswith("B")
    whatsapp = get("whatsapp") or get("phone_hk")

    card: dict[str, Any] = {
        "slug": slug,
        "variant": "licensed" if licensed else "standard",
        "coBrand": "ark" if licensed else None,
        "name": {"en": name_en, "zh": get("name_zh")},
        "title": {"en": get("title_en"), "zh": get("title_zh")},
        "org": {"en": get("org_en"), "zh": get("org_zh")},
        "location": {"en": get("location"), "zh": get("location")},
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
        raw = get("licence_types").replace("/", ",").replace("、", ",")
        codes = [c.strip() for c in raw.split(",")]
        types = []
        for code in filter(None, codes):
            if code not in SFC_TYPES:
                problems.append(f"{who}: 未知持牌类别 {code!r}（只能 1–10）")
                continue
            en, zh = SFC_TYPES[code]
            types.append({"code": code, "en": en, "zh": zh})

        if not get("ce_number"):
            problems.append(f"{who}: B 版但没有 SFC 中央编号")
        if not types:
            problems.append(f"{who}: B 版但没有持牌类别")

        card["licence"] = {
            "ceNumber": get("ce_number"),
            "entityCeNumber": get("entity_ce") or None,
            "entity": {"en": get("entity_en"), "zh": get("entity_en")},
            "regulator": {"en": "SFC", "zh": "香港证监会"},
            "types": types,
            "address": {"en": get("addr_en"), "zh": get("addr_zh")},
        }

    return card if slug_ok else None


def check_duplicate_slugs(cards: list[dict[str, Any]], problems: list[str]) -> None:
    seen: dict[str, int] = {}
    for card in cards:
        seen[card["slug"]] = seen.get(card["slug"], 0) + 1
    for slug, count in seen.items():
        if count > 1:
            problems.append(f"slug 重复 {count} 次: {slug} —— 每人必须唯一")
