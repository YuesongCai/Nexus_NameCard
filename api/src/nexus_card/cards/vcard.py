"""vCard 3.0 generation.

Served from the API rather than built in the browser: iOS Safari is unreliable with
blob:/data: downloads, but a real `text/vcard` response with a filename opens the Contacts
sheet every time — which is the single most important action on this page.
"""

from __future__ import annotations

from nexus_card.models import Card, Lang


def _escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", r"\;")
        .replace(",", r"\,")
        .replace("\n", r"\n")
    )


def _fold(line: str) -> str:
    """RFC 2426 §2.6 — fold at 75 octets, continuation lines start with a space."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    out: list[str] = []
    chunk = bytearray()
    for ch in line:
        encoded = ch.encode("utf-8")
        limit = 75 if not out else 74
        if len(chunk) + len(encoded) > limit:
            out.append(chunk.decode("utf-8"))
            chunk = bytearray()
        chunk += encoded
    if chunk:
        out.append(chunk.decode("utf-8"))
    return "\r\n ".join(out)


def render_vcard(card: Card, lang: Lang = "en") -> str:
    zh_first = lang == "zh"
    primary_name = card.name.zh if zh_first else card.name.en
    other_name = card.name.en if zh_first else card.name.zh
    full_name = primary_name if primary_name == other_name else f"{primary_name} {other_name}"

    title = card.title.zh if zh_first else card.title.en
    org = card.org.zh if zh_first else card.org.en

    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"N:;{_escape(primary_name)};;;",
        f"FN:{_escape(full_name)}",
        f"ORG:{_escape(org)}",
        f"TITLE:{_escape(title)}",
    ]

    if card.contacts.email:
        lines.append(f"EMAIL;TYPE=INTERNET,WORK:{card.contacts.email}")

    for i, phone in enumerate(card.contacts.phones):
        label = phone.label.zh if zh_first else phone.label.en
        types = "CELL,VOICE" if i == 0 else "CELL"
        lines.append(f"TEL;TYPE=WORK,{types}:{phone.value}")
        lines.append(f"item{i + 1}.TEL;TYPE=WORK:{phone.value}")
        lines.append(f"item{i + 1}.X-ABLabel:{_escape(label)}")

    if card.contacts.whatsapp:
        lines.append(f"X-SOCIALPROFILE;TYPE=whatsapp:https://wa.me/{card.contacts.whatsapp.lstrip('+')}")

    if card.contacts.wechat and card.contacts.wechat.id:
        # No standard vCard field for WeChat; X-SOCIALPROFILE is what iOS/Android read,
        # and X-WECHAT is what most Chinese address-book apps look for.
        wechat_id = card.contacts.wechat.id
        lines.append(f"X-SOCIALPROFILE;TYPE=wechat:{wechat_id}")
        lines.append(f"X-WECHAT:{wechat_id}")

    if card.contacts.website:
        lines.append(f"URL;TYPE=WORK:{card.contacts.website}")
    if card.contacts.linkedin:
        lines.append(f"X-SOCIALPROFILE;TYPE=linkedin:{card.contacts.linkedin}")

    note_parts: list[str] = []
    if card.licence:
        types = " / ".join(
            f"Type {t.code} {t.zh if zh_first else t.en}" for t in card.licence.types
        )
        entity = card.licence.entity.zh if zh_first else card.licence.entity.en
        note_parts.append(f"SFC CE No. {card.licence.ce_number}")
        if types:
            note_parts.append(types)
        note_parts.append(entity)
        if card.licence.entity_ce_number:
            note_parts.append(f"Entity CE No. {card.licence.entity_ce_number}")
        if card.licence.address:
            address = card.licence.address.zh if zh_first else card.licence.address.en
            lines.append(f"ADR;TYPE=WORK:;;{_escape(address)};;;;")
    if card.member_line:
        note_parts.append(card.member_line.zh if zh_first else card.member_line.en)
    if note_parts:
        lines.append(f"NOTE:{_escape(' · '.join(note_parts))}")

    lines.append("END:VCARD")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"


def vcard_filename(card: Card) -> str:
    """ASCII-only filename — non-Latin filenames break download prompts on some clients."""
    base = "".join(ch for ch in card.name.en if ch.isalnum() or ch in " -_").strip()
    return f"{(base or card.slug).replace(' ', '-')}.vcf"
