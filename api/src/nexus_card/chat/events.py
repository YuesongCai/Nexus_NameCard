"""SSE event envelopes — a subset of the Nexus §6 event protocol.

Deliberately wire-compatible with `nexus-agentcore`'s `docs/event-protocol.md` (camelCase
envelope, monotonic `seq`, `runId`/`model` only on `response.created`, `firstTokenAt`/
`ttftMs` on the first delta, terminal `response.completed` / `response.failed`). This card
bot is a simple RAG loop today; keeping the wire shape means the frontend can be pointed at
the real AgentCore runtime later without a client rewrite.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

CREATED = "response.created"
SOURCES = "response.sources"
OUTPUT_DELTA = "response.output_text.delta"
COMPLETED = "response.completed"
FAILED = "response.failed"


def _iso_now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@dataclass(slots=True)
class EventStream:
    """Sequences envelopes for one run and stamps the protocol's timing fields."""

    run_id: str
    model: str
    _seq: int = field(default=0, init=False)
    _started: float = field(default_factory=time.perf_counter, init=False)
    _received_at: str = field(default_factory=_iso_now, init=False)
    _first_token_sent: bool = field(default=False, init=False)

    def _next(self, type_: str, **fields: Any) -> dict[str, Any]:
        self._seq += 1
        return {"type": type_, "seq": self._seq, **fields}

    def created(self) -> dict[str, Any]:
        return self._next(
            CREATED,
            runId=self.run_id,
            model=self.model,
            requestReceivedAt=self._received_at,
        )

    def sources(self, sources: list[dict[str, Any]]) -> dict[str, Any]:
        return self._next(SOURCES, sources=sources)

    def delta(self, text: str) -> dict[str, Any]:
        extra: dict[str, Any] = {}
        if not self._first_token_sent:
            self._first_token_sent = True
            extra = {
                "firstTokenAt": _iso_now(),
                "ttftMs": int((time.perf_counter() - self._started) * 1000),
            }
        return self._next(OUTPUT_DELTA, delta=text, **extra)

    def completed(self) -> dict[str, Any]:
        return self._next(COMPLETED, timing=self._timing())

    def failed(self, reason: str, code: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"reason": reason, "timing": self._timing()}
        if code:
            payload["code"] = code
        return self._next(FAILED, **payload)

    def _timing(self) -> dict[str, int]:
        return {"totalMs": int((time.perf_counter() - self._started) * 1000)}
