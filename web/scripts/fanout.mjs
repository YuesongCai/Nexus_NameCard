/**
 * Post-build: give every card its own real HTML file.
 *
 * Two problems this solves on a static host:
 *
 * 1. **Deep links.** GitHub Pages has no SPA rewrite, so `/c/grantpan` would 404. Writing
 *    `c/grantpan/index.html` makes it a genuine page.
 * 2. **Link previews.** The whole point of this URL is being pasted into WhatsApp and
 *    LinkedIn. Crawlers don't run JS, so the card's own name and title are baked into each
 *    file's `<head>` — the same tags `web.py` injects when FastAPI serves the app.
 *
 * `404.html` gets the default card so an unknown slug lands somewhere useful.
 */

import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const dist = resolve(here, '..', 'dist')
const cardsDir = join(dist, 'data', 'cards')

const BASE = (process.env.VITE_BASE ?? '/').replace(/\/*$/, '/')
const SITE = (process.env.VITE_SITE_URL ?? '').replace(/\/$/, '')
const DEFAULT_SLUG = process.env.VITE_DEFAULT_SLUG ?? 'nexus'

const escapeHtml = (value) =>
  String(value).replace(
    /[&<>"']/g,
    (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch],
  )

function metaFor(card) {
  const name =
    card.name.zh && card.name.zh !== card.name.en
      ? `${card.name.en} ${card.name.zh}`
      : card.name.en
  const title = `${name} — ${card.title.en} | Nexus`
  const description =
    `${card.title.en} · ${card.org.en}. ` +
    'Nexus is the AI-native wealth operating system for EAMs and IFAs, ' +
    'built by Noah Holdings (NYSE: NOAH · HKEX: 6686).'
  const url = SITE ? `${SITE}${BASE}c/${card.slug}` : ''
  // Only advertise a preview image once one actually exists: a 404 og:image renders as a
  // broken thumbnail in WhatsApp, which looks worse than no thumbnail at all.
  const hasOgImage = existsSync(join(dist, 'og-image.png'))
  const image = SITE && hasOgImage ? `${SITE}${BASE}og-image.png` : ''

  const tags = [
    `<title>${escapeHtml(title)}</title>`,
    `<meta name="description" content="${escapeHtml(description)}">`,
    `<meta property="og:type" content="profile">`,
    `<meta property="og:title" content="${escapeHtml(title)}">`,
    `<meta property="og:description" content="${escapeHtml(description)}">`,
    `<meta property="og:site_name" content="Nexus by Noah Holdings">`,
    `<meta name="twitter:card" content="summary_large_image">`,
    `<meta name="twitter:title" content="${escapeHtml(title)}">`,
    `<meta name="twitter:description" content="${escapeHtml(description)}">`,
    // A business card is not something we want indexed and ranked.
    `<meta name="robots" content="noindex, nofollow">`,
  ]
  if (url) {
    tags.push(`<meta property="og:url" content="${escapeHtml(url)}">`)
    tags.push(`<link rel="canonical" href="${escapeHtml(url)}">`)
  }
  if (image) tags.push(`<meta property="og:image" content="${escapeHtml(image)}">`)
  return tags.join('\n    ')
}

function render(shell, card) {
  return shell
    .replace(/<title>.*?<\/title>\s*/s, '')
    .replace(/<\/head>/i, `  ${metaFor(card)}\n  </head>`)
}

if (!existsSync(cardsDir)) {
  console.error(
    `fanout: ${cardsDir} is missing — run \`python api/scripts/export_static.py\` first.`,
  )
  process.exit(1)
}

const shell = readFileSync(join(dist, 'index.html'), 'utf8')
const slugs = readdirSync(cardsDir)
  .filter((file) => file.endsWith('.json'))
  .map((file) => file.replace(/\.json$/, ''))

let written = 0
let fallback = null

for (const slug of slugs) {
  const card = JSON.parse(readFileSync(join(cardsDir, `${slug}.json`), 'utf8'))
  const dir = join(dist, 'c', slug)
  mkdirSync(dir, { recursive: true })
  writeFileSync(join(dir, 'index.html'), render(shell, card))
  written += 1
  if (slug === DEFAULT_SLUG) fallback = card
}

fallback ??= slugs.length
  ? JSON.parse(readFileSync(join(cardsDir, `${slugs[0]}.json`), 'utf8'))
  : null

if (fallback) {
  const root = render(shell, fallback)
  writeFileSync(join(dist, 'index.html'), root)
  writeFileSync(join(dist, '404.html'), root)
}

// Pages runs Jekyll by default, which silently drops files and folders starting with `_`.
writeFileSync(join(dist, '.nojekyll'), '')

console.log(`fanout: wrote ${written} card page(s) + 404.html (base "${BASE}")`)
