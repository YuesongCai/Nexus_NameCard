import { useCallback, useEffect, useRef, useState } from 'react'

import { fetchCard, track } from './api/client'
import { BASE_URL } from './api/config'
import { AskNexus } from './components/AskNexus'
import { ContactRail } from './components/ContactRail'
import { Footer } from './components/Footer'
import { IdentityCard } from './components/IdentityCard'
import { CardSkeleton, NotFound, Toast } from './components/States'
import { TopBar } from './components/TopBar'
import { detectLang, t } from './i18n'
import type { Card, Lang } from './types'
import styles from './App.module.css'

const DEFAULT_SLUG = 'grantpan'

/**
 * `/c/<slug>` is the QR target; anything else falls back to the company card.
 *
 * The deployment's base path is stripped first — on GitHub Pages the app lives under
 * `/Nexus_NameCard/`, so the real path is `/Nexus_NameCard/c/grantpan`.
 */
function slugFromPath(): string {
  let path = window.location.pathname
  if (BASE_URL !== '/' && path.startsWith(BASE_URL)) {
    path = `/${path.slice(BASE_URL.length)}`
  }
  const match = /^\/c\/([a-z0-9][a-z0-9-]{0,62})\/?$/i.exec(path)
  return match?.[1]?.toLowerCase() ?? DEFAULT_SLUG
}

/** Per-open id so analytics can group a scan's events without cookies or fingerprinting. */
function newSessionId(): string {
  return `s_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`
}

type Status = 'loading' | 'ready' | 'missing'

export function App() {
  const [lang, setLang] = useState<Lang>(detectLang)
  const [card, setCard] = useState<Card | null>(null)
  const [status, setStatus] = useState<Status>('loading')
  const [toast, setToast] = useState(false)

  const slugRef = useRef(slugFromPath())
  const sessionRef = useRef(newSessionId())
  const toastTimer = useRef<number | undefined>(undefined)

  useEffect(() => {
    const controller = new AbortController()
    fetchCard(slugRef.current, controller.signal)
      .then((loaded) => {
        setCard(loaded)
        setStatus('ready')
        track('card_view', { slug: loaded.slug, sessionId: sessionRef.current })
      })
      .catch((error: unknown) => {
        if ((error as Error).name === 'AbortError') return
        setStatus('missing')
      })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    document.documentElement.lang = lang === 'zh' ? 'zh-Hans' : 'en'
  }, [lang])

  useEffect(() => () => window.clearTimeout(toastTimer.current), [])

  const changeLang = useCallback((next: Lang) => {
    setLang(next)
    localStorage.setItem('nexus-card-lang', next)
    track('lang_switch', { slug: slugRef.current, sessionId: sessionRef.current, detail: next })
  }, [])

  const showToast = useCallback(() => {
    setToast(true)
    window.clearTimeout(toastTimer.current)
    toastTimer.current = window.setTimeout(() => setToast(false), 2400)
  }, [])

  return (
    <div className={styles.shell}>
      <TopBar lang={lang} onLangChange={changeLang} />

      <main className={styles.main}>
        {status === 'loading' && <CardSkeleton lang={lang} />}
        {status === 'missing' && <NotFound lang={lang} />}

        {status === 'ready' && card && (
          <>
            <p className={styles.eyebrow}>{t(lang, 'justMet')}</p>

            <IdentityCard card={card} lang={lang} />
            <ContactRail
              card={card}
              lang={lang}
              sessionId={sessionRef.current}
              onSaved={showToast}
            />
            <AskNexus card={card} lang={lang} sessionId={sessionRef.current} />
            <Footer card={card} lang={lang} />
          </>
        )}
      </main>

      <Toast message={t(lang, 'saved')} visible={toast} />
    </div>
  )
}
