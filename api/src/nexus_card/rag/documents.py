"""Load the markdown knowledge base and split it into retrievable chunks.

The KB is bilingual by design: each `##` section carries the English and the Chinese
statement of the same fact, so a single chunk answers a question asked in either language
and the model always has both wordings available when it drafts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_HEADING = re.compile(r"^(#{2,3})\s+(.*)$", re.MULTILINE)

# Chunks below this are folded into the previous one; above it, split on paragraph breaks.
_MIN_CHARS = 180
_MAX_CHARS = 1400


@dataclass(slots=True)
class Chunk:
    id: str
    doc_id: str
    title: str
    heading: str
    text: str
    tags: list[str] = field(default_factory=list)
    weight: float = 1.0

    @property
    def embed_text(self) -> str:
        return f"{self.title}\n{self.heading}\n{self.text}"


def _parse_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    m = _FRONTMATTER.match(raw)
    if not m:
        return {}, raw
    meta: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, raw[m.end() :]


def _parse_tags(value: str) -> list[str]:
    return [t.strip() for t in value.strip().strip("[]").split(",") if t.strip()]


def _split_long(text: str) -> list[str]:
    if len(text) <= _MAX_CHARS:
        return [text]
    parts: list[str] = []
    buf: list[str] = []
    size = 0
    for para in text.split("\n\n"):
        if size + len(para) > _MAX_CHARS and buf:
            parts.append("\n\n".join(buf))
            buf, size = [], 0
        buf.append(para)
        size += len(para) + 2
    if buf:
        parts.append("\n\n".join(buf))
    return parts


def _sections(body: str) -> list[tuple[str, str]]:
    """Split a document body on `##`/`###` headings into (heading, text) pairs."""
    matches = list(_HEADING.finditer(body))
    if not matches:
        return [("", body.strip())]

    sections: list[tuple[str, str]] = []
    preamble = body[: matches[0].start()].strip()
    if preamble:
        sections.append(("", preamble))

    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        heading = m.group(2).strip()
        text = body[m.end() : end].strip()
        if not text:
            continue
        if sections and len(text) < _MIN_CHARS:
            prev_heading, prev_text = sections[-1]
            sections[-1] = (prev_heading, f"{prev_text}\n\n{heading}\n{text}")
            continue
        sections.append((heading, text))
    return sections


def load_chunks(kb_dir: Path) -> list[Chunk]:
    """Parse every `*.md` under `kb_dir` into chunks, in stable filename order."""
    chunks: list[Chunk] = []
    for path in sorted(kb_dir.glob("*.md")):
        meta, body = _parse_frontmatter(path.read_text(encoding="utf-8"))
        doc_id = meta.get("id") or path.stem
        title = meta.get("title") or doc_id
        tags = _parse_tags(meta.get("tags", ""))
        try:
            weight = float(meta.get("weight", "1.0"))
        except ValueError:
            weight = 1.0

        for heading, text in _sections(body):
            for piece in _split_long(text):
                if not piece.strip():
                    continue
                chunks.append(
                    Chunk(
                        id=f"{doc_id}#{len(chunks):03d}",
                        doc_id=doc_id,
                        title=title,
                        heading=heading,
                        text=piece.strip(),
                        tags=tags,
                        weight=weight,
                    )
                )
    return chunks
