import { Fragment, type ReactNode } from 'react'

/**
 * Minimal markdown renderer for assistant replies.
 *
 * Model output is untrusted input, and the answers only ever need paragraphs, bullets,
 * bold, inline code and links — so rather than pulling in a parser plus a sanitiser, this
 * builds React elements directly. Nothing is ever passed to `dangerouslySetInnerHTML`, so
 * there is no HTML-injection surface at all.
 */

const INLINE = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)\s]+\))/g

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = []
  let index = 0

  for (const part of text.split(INLINE)) {
    if (!part) continue
    const key = `${keyPrefix}-${index++}`

    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      nodes.push(<strong key={key}>{part.slice(2, -2)}</strong>)
      continue
    }
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      nodes.push(<code key={key}>{part.slice(1, -1)}</code>)
      continue
    }
    const link = /^\[([^\]]+)\]\(([^)\s]+)\)$/.exec(part)
    if (link) {
      const [, label, href] = link
      // Only http(s) and mailto: survive — no javascript:/data: URLs from model output.
      if (href && /^(https?:|mailto:)/i.test(href)) {
        nodes.push(
          <a key={key} href={href} target="_blank" rel="noopener noreferrer nofollow">
            {label}
          </a>,
        )
      } else {
        nodes.push(<Fragment key={key}>{label}</Fragment>)
      }
      continue
    }
    nodes.push(<Fragment key={key}>{part}</Fragment>)
  }
  return nodes
}

export function Markdown({ text }: { text: string }) {
  const blocks: ReactNode[] = []
  let bullets: string[] = []
  let blockIndex = 0

  const flushBullets = (): void => {
    if (bullets.length === 0) return
    const items = bullets
    blocks.push(
      <ul key={`ul-${blockIndex++}`}>
        {items.map((item, i) => (
          <li key={i}>{renderInline(item, `li-${blockIndex}-${i}`)}</li>
        ))}
      </ul>,
    )
    bullets = []
  }

  for (const rawLine of text.split('\n')) {
    const line = rawLine.trimEnd()
    const bullet = /^\s*[-*•]\s+(.*)$/.exec(line)
    if (bullet?.[1]) {
      bullets.push(bullet[1])
      continue
    }
    flushBullets()
    if (line.trim() === '') continue
    // Strip any heading marks — the prompt bans them, but never trust that absolutely.
    const clean = line.replace(/^#{1,6}\s*/, '')
    blocks.push(<p key={`p-${blockIndex++}`}>{renderInline(clean, `p-${blockIndex}`)}</p>)
  }
  flushBullets()

  return <>{blocks}</>
}
