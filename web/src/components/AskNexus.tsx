import { useEffect, useMemo, useRef, useState } from 'react'

import { fetchIntro } from '../api/client'
import { useChat } from '../hooks/useChat'
import { CHAT_ENABLED } from '../api/config'
import { t } from '../i18n'
import type { Card, Intro, Lang } from '../types'
import { Composer } from './Composer'
import { Icon } from './Icon'
import { Markdown } from './Markdown'
import styles from './AskNexus.module.css'

interface Props {
  card: Card
  lang: Lang
  sessionId: string
}

const ERROR_KEYS: Record<string, 'errorNetwork' | 'errorRate' | 'errorGeneric'> = {
  network: 'errorNetwork',
  stream_broken: 'errorNetwork',
  rate_limited: 'errorRate',
}

export function AskNexus({ card, lang, sessionId }: Props) {
  const [intro, setIntro] = useState<Intro | null>(null)
  const [used, setUsed] = useState<string[]>([])
  const { turns, busy, ask, stop, retryLast } = useChat(card.slug, lang, sessionId)
  const endRef = useRef<HTMLDivElement>(null)
  const hasAsked = turns.length > 0

  useEffect(() => {
    const controller = new AbortController()
    fetchIntro(card.slug, lang, controller.signal)
      .then(setIntro)
      .catch(() => {
        /* The chat still works without chips; don't surface a failure for a nicety. */
      })
    return () => controller.abort()
  }, [card.slug, lang])

  // Keep the newest message in view, but only scroll the transcript — never the page,
  // which would yank the identity card off screen mid-read.
  useEffect(() => {
    if (!hasAsked) return
    endRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }, [turns, hasAsked])

  const chips = useMemo(
    () => (intro?.suggestions ?? []).filter((s) => !used.includes(s.id)),
    [intro, used],
  )

  const handleChip = (id: string, question: string): void => {
    setUsed((prev) => [...prev, id])
    ask(question)
  }

  // No visible section heading: the greeting bubble and the NEXUS AI badge already say what
  // this is, and a label plus a subtitle only pushed the first question further down the
  // screen. The name stays as the section's accessible label.
  return (
    <section className={styles.section} aria-label={t(lang, 'askNexus')}>
      <div className={styles.panel}>
        <div className={styles.transcript}>
          <div className={`${styles.bubble} ${styles.bot}`}>
            <span className={styles.badge}>Nexus AI</span>
            <p>{intro?.greeting ?? '…'}</p>
          </div>

          {turns.map((turn) =>
            turn.role === 'user' ? (
              <div key={turn.id} className={`${styles.bubble} ${styles.me}`}>
                {turn.content}
              </div>
            ) : (
              <div key={turn.id} className={`${styles.bubble} ${styles.bot}`}>
                <span className={styles.badge}>Nexus AI</span>

                {turn.status === 'error' ? (
                  <div className={styles.error}>
                    <Icon name="warning" />
                    <div>
                      <p>{t(lang, ERROR_KEYS[turn.content] ?? 'errorGeneric')}</p>
                      <button type="button" className={styles.retry} onClick={retryLast}>
                        <Icon name="refresh" />
                        {t(lang, 'retry')}
                      </button>
                    </div>
                  </div>
                ) : turn.content ? (
                  <div className={styles.prose}>
                    <Markdown text={turn.content} />
                    {turn.status === 'streaming' && <span className={styles.caret} />}
                  </div>
                ) : (
                  <div className={styles.typing} aria-label={t(lang, 'thinking')}>
                    <span />
                    <span />
                    <span />
                  </div>
                )}

                {turn.status === 'done' && turn.sources && turn.sources.length > 0 && (
                  <Sources labels={turn.sources.map((s) => s.title)} lang={lang} />
                )}
              </div>
            ),
          )}
          <div ref={endRef} />
        </div>

        {CHAT_ENABLED && chips.length > 0 && (
          <div className={styles.chips}>
            {chips.map((chip) => (
              <button
                key={chip.id}
                type="button"
                className={styles.chip}
                disabled={busy}
                onClick={() => handleChip(chip.id, chip.question)}
              >
                {chip.label}
              </button>
            ))}
          </div>
        )}

        {CHAT_ENABLED ? (
          <Composer lang={lang} busy={busy} onSubmit={ask} onStop={stop} />
        ) : (
          <p className={styles.offline}>
            <Icon name="warning" />
            {t(lang, 'chatOffline')}
          </p>
        )}
      </div>
    </section>
  )
}

function Sources({ labels, lang }: { labels: string[]; lang: Lang }) {
  return (
    <p className={styles.sources}>
      <span className={styles.sourcesLabel}>{t(lang, 'sources')}</span>
      {labels.map((label) => (
        <span key={label} className={styles.sourceChip}>
          {label}
        </span>
      ))}
    </p>
  )
}
