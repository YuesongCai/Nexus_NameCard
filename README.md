# Nexus Card

The H5 page the business-card QR opens.

Top half: who you just met, and every way to reach them — one tap saves the contact.
Bottom half: **Ask Nexus**, a retrieval-grounded bot that answers questions about Nexus from
a curated knowledge base.

```
QR on the printed card  →  https://card.noahnexus.ai/c/<slug>
```

---

## Design

The page sits on the brand's cream stock (`#F4F1EA`) — the same colour as the printed card.
That inverts the usual depth order: white is *above* the page, not below it, so the stack
runs **cream ground → white panels → inked identity card**.

The identity block is the concept deck's *"02 · Inverted Ink"* direction: near-black with
the lime lockup. On cream it is the highest-contrast object available, so the person leads
the page with no extra decoration. Lime appears exactly twice — the rule under the name, and
the Save-contact button — per the concept rule of one accent per face.

The card itself carries only what a phone screen can hold: name, title, the SFC line, and
the member-firm line. The licensed corporation, its central entity number, the full licence
descriptions and the registered address are all on the page, as fine print in the footer.

Palette and type come from `noahnexus.ai` — Inter / JetBrains Mono / Noto Sans SC,
`--carbon #0A0C08`, `--lime #B8FF3A`, `--bone #F4F1EA`. On light surfaces lime is only ever a
*fill behind ink text*: lime type on cream is ~1.4:1 and unreadable.

---

## Layout

```
nexus-card/
├── web/                     React 18 + Vite + TS, CSS Modules, no UI framework
│   └── src/
│       ├── App.tsx              route (/c/:slug), language, analytics session
│       ├── api/chat.ts          §6 SSE reader (POST + bare `data:` lines)
│       ├── components/          IdentityCard · ContactRail · AskNexus · Composer · Footer
│       └── styles/tokens.css    the whole palette, semantically named
└── api/                     FastAPI + pydantic v2 + sse-starlette
    ├── kb/*.md                  the knowledge base (bilingual markdown)
    ├── data/cards/*.json        one file per person
    └── src/nexus_card/
        ├── rag/                 chunking · CJK BM25 · Titan embeddings · hybrid retrieval
        ├── llm/                 Bedrock ConverseStream · Anthropic · echo
        ├── chat/                prompt + guardrails, §6 event envelopes, the turn
        └── web.py               serves the SPA with per-card Open Graph tags
```

Both sides mirror the conventions of `nexus-frontend-statements` and `nexus_ai_backend`, so
this is not a new stack to learn.

---

## Run it

```bash
make install     # venv + npm install
make run         # builds the SPA, serves everything from the API on :8099
```

Two-process dev loop, with hot reload on both sides:

```bash
make dev-api     # :8099
make dev-web     # :5173, proxies /api to the API
```

`make check` runs lint, types, tests and the production build.

Without AWS credentials, set `NEXUS_CARD_LLM_PROVIDER=echo` for a deterministic offline
stub, or `anthropic` with an API key.

---

## Adding a person

Drop a file in `api/data/cards/`. No code change, no redeploy — the store reloads on mtime.

```jsonc
{
  "slug": "grantpan",              // the URL: /c/grantpan
  "variant": "standard",           // "licensed" for SFC-registered staff (B-version card)
  "coBrand": "ark",                // adds the Ark lockup beside the Nexus mark; null for none
  "name":  { "en": "Grant Pan", "zh": "潘青" },
  "title": { "en": "CEO, Hong Kong · Group CFO", "zh": "香港行政总裁 · 集团财务总监" },
  "org":   { "en": "Nexus", "zh": "Nexus" },
  "contacts": {
    "whatsapp": "+85200000000",    // E.164; drives the wa.me link
    "phones": [{ "label": { "en": "Mobile", "zh": "手机" }, "value": "+852 0000 0000" }],
    "email": "grant.pan@nexus.ai",
    "linkedin": "https://www.linkedin.com/company/noah-nexus",
    "website": "https://noahnexus.ai"
  },
  "licence": null,                 // "licensed" cards add ceNumber / entity / types / address
  "memberLine": { "en": "A member firm of Noah (US: NOAH · HK: 6686)", "zh": "…" }
}
```

Seeded: `grantpan` (default) and `nexus` (the company fallback at `/`). The licensed
(B-version) shape is supported in code and covered by tests against a synthetic fixture —
no real person's SFC registration is checked into this repo.

**vCard** is generated server-side (`/api/cards/<slug>/vcard`) rather than in the browser:
iOS Safari is unreliable with `blob:` downloads, but a real `text/vcard` response opens the
Contacts sheet every time — and that is the single most important action on the page.

---

## The bot

A retrieval-grounded Q&A loop, not an agent. It has no tools, no client data, and cannot
act.

**Knowledge base** — `api/kb/*.md`, bilingual by design: each `##` section states the same
fact in English and Chinese, so one chunk answers a question asked in either language and
the model always has both wordings when it drafts. Sourced from `noahnexus.ai`.

**Retrieval** — hybrid. BM25 over a CJK-aware tokenizer (Latin runs → words, CJK runs →
character bigrams, which is what makes `客户数据安全吗` retrievable without a segmentation
model), fused with dense cosine over Titan embeddings, plus a small boost when the query hits
a document's `tags:`. Tags disambiguate passages that mention a term in passing from passages
that are *about* it.

Rebuild the dense index after editing the KB:

```bash
make index       # needs bedrock:InvokeModel on the Titan embeddings model
```

If the index is missing or stale, the retriever logs it and runs **BM25-only** rather than
failing to start. Recall on paraphrased questions is noticeably worse in that mode, so
`make index` belongs in the release step.

**Guardrails** — the bot introduces and routes; it never advises. No recommendations, no
suitability opinions, no return or yield quotes, no forward-looking statements, no pricing
commitments beyond the KB, no client data. Out-of-scope questions hand off to the person on
the card by name. Prompt-injection attempts get one sentence and a redirect. The compliance
line sits under every answer in the UI.

When the model is unreachable the visitor gets a hand-off to the human, not an empty bubble.

**Wire protocol** — a subset of the Nexus §6 event protocol
(`nexus-agentcore/docs/event-protocol.md`): camelCase envelope, monotonic `seq`,
`runId`/`model` on `response.created`, `firstTokenAt`/`ttftMs` on the first delta, terminal
`response.completed` / `response.failed`. The client parser ignores anything that isn't a
`data:` line and reads `type` out of the JSON — so it already tolerates AgentCore's bare-
`data:` wire and the `: ok` comment the AWS data plane injects. Pointing this page at the
real AgentCore runtime later is a backend swap, not a client rewrite.

---

## Deploy

Two shapes, one codebase.

### A · Static (GitHub Pages) — the card, no bot

`https://yuesongcai.github.io/Nexus_NameCard/c/<slug>`

Pushed to `main` → `.github/workflows/pages.yml` builds and publishes. Everything the page
needs at request time is a pure function of a card profile, so it is all pre-rendered:

```bash
python api/scripts/export_static.py     # card JSON, greetings, chips, .vcf — both languages
cd web && npm run build:static          # vite build + per-card HTML fan-out
```

The exporter calls the *same* `render_vcard` / `greeting_for` / `suggestions_for` the live
API calls, so the static build cannot drift from the served one. `scripts/fanout.mjs` then
writes a real `c/<slug>/index.html` per person — GitHub Pages has no SPA rewrite, and
crawlers do not run JS, so this is what makes both deep links and WhatsApp link previews
work.

The chat needs a server. Without `VITE_API_BASE` the composer is replaced by an explicit
"not switched on for this deployment" line — disabled, not broken. Point it at a deployed
API and the bot lights up with no rebuild of anything else:

```bash
VITE_API_BASE=https://card-api.example.com npm run build:static
```

Everything else is fully live on the static build: contact taps, Save-contact, both
languages, per-card Open Graph.

### B · Full stack (Docker) — the card *and* the bot

```bash
make docker
docker run -p 8080:8080 --env-file .env nexus-card:latest
```

One image: the SPA is built in the first stage and served by the API, so there is one
origin, no CORS in production, and no separate static host. Runs as a non-root user.

Set at minimum `NEXUS_CARD_PUBLIC_BASE_URL` (canonical + Open Graph URLs) and the LLM
provider block — see `.env.example`.

Behind a proxy, do not buffer `/api/chat`: the response sets `X-Accel-Buffering: no`, and
nginx/ALB buffering is what turns a streaming answer into a twenty-second freeze.

**Abuse control** is an in-process token bucket keyed by client IP — enough to stop one
bored visitor burning tokens on a public page. If this ever scales past a single instance,
swap the bucket store for Redis; the interface does not change.

**Analytics** — `card_view`, `contact_tap`, `vcard_save`, `chat_ask`, `chat_error`,
`lang_switch`, posted via `sendBeacon` so the event survives the tap-through to WhatsApp.
No cookies, no PII, no question bodies; the session id is per-page-open and random.

---

## Known gaps

- **Grant Pan's phone number is the placeholder** `+852 0000 0000` carried over from the
  concept deck, and `潘青` is inferred from the public Noah Holdings listing. Both need
  confirming before print.
- **`web/public/og-image.png` (1200×630) and `apple-touch-icon.png` (180×180) are not in the
  repo.** Both tags are omitted rather than pointed at a 404, so nothing is broken — link
  previews simply have no thumbnail and iOS uses a page snapshot for Add to Home Screen.
  Drop the files in and the build picks them up; `index.html` has the icon link commented
  out ready to restore.
- **The public Pages deploy has no bot.** GitHub Pages is static-only, so `Ask Nexus` shows
  the not-configured line there. It needs an LLM key and a host that can run the API —
  see *Deploy · A*.
- **The Bedrock path has not been exercised against live AWS** from this machine (no
  credentials). It is covered by tests against a stubbed client — delta extraction and error
  normalisation — but the first real deploy should watch the `chat.llm_failed` log line.
