import { useEffect, useRef, useState } from 'react'

import { track } from '../api/client'
import { asset } from '../api/config'
import { t } from '../i18n'
import type { Card, Lang } from '../types'
import { Icon } from './Icon'
import styles from './WechatSheet.module.css'

/**
 * WeChat has no "add this person" link.
 *
 * LinkedIn is a URL: one tap, done, works in any browser. WeChat has no public equivalent —
 * `weixin://` schemes cover Mini Programs only, and WeChat itself blocks schemes that
 * aren't on its whitelist. So adding someone always goes through one of two human steps,
 * and which one is available depends entirely on **where the page is open**:
 *
 * - **Inside WeChat's browser** — long-press the QR and WeChat offers 识别图中二维码.
 *   Its recognition is screenshot-based: it fires on a long-press over an `<img>`, grabs
 *   the screen and runs detection. Hence the rules this component follows — a real `<img>`
 *   (never a CSS background), fully visible, generous quiet zone, ~200px.
 * - **Anywhere else** (Safari/Chrome — where a camera scan of a paper card lands you)
 *   long-press only offers "save image". So the primary action there is copying the
 *   WeChat ID, with saving the QR as the secondary path.
 *
 * Detecting `MicroMessenger` and swapping the instructions is the whole trick: showing
 * "长按识别" to someone in Safari is telling them to do something that cannot work.
 */

interface Props {
  card: Card
  lang: Lang
  sessionId: string
  onClose: () => void
}

export function isWeChatBrowser(): boolean {
  return /MicroMessenger/i.test(navigator.userAgent)
}

export function WechatSheet({ card, lang, sessionId, onClose }: Props) {
  const [copied, setCopied] = useState(false)
  const inWeChat = isWeChatBrowser()
  const closeRef = useRef<HTMLButtonElement>(null)
  const wechat = card.contacts.wechat

  useEffect(() => {
    closeRef.current?.focus()
    const onKey = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    // The page behind must not scroll while the sheet is up.
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = previous
    }
  }, [onClose])

  if (!wechat) return null

  const copyId = async (): Promise<void> => {
    if (!wechat.id) return
    try {
      await navigator.clipboard.writeText(wechat.id)
    } catch {
      // Older iOS WebViews reject the async clipboard API; the range trick still works.
      const field = document.createElement('textarea')
      field.value = wechat.id
      field.style.position = 'fixed'
      field.style.opacity = '0'
      document.body.appendChild(field)
      field.select()
      document.execCommand('copy')
      document.body.removeChild(field)
    }
    setCopied(true)
    track('contact_tap', { slug: card.slug, sessionId, detail: 'wechat_copy_id' })
    setTimeout(() => setCopied(false), 2200)
  }

  const qrSrc = wechat.qr ? asset(wechat.qr) : null

  return (
    <div className={styles.backdrop} onClick={onClose} role="presentation">
      <div
        className={styles.sheet}
        role="dialog"
        aria-modal="true"
        aria-label={t(lang, 'wechat')}
        onClick={(event) => event.stopPropagation()}
      >
        <button ref={closeRef} className={styles.close} onClick={onClose} type="button">
          <Icon name="close" />
          <span className="sr-only">{t(lang, 'close')}</span>
        </button>

        <h2 className={styles.heading}>{t(lang, 'wechatAdd')}</h2>

        {qrSrc && (
          <>
            {/* A plain <img>, un-cropped, on a quiet light panel — the conditions WeChat's
                screenshot-based detector needs. Do not move this into a background-image. */}
            <div className={styles.qrPanel}>
              <img className={styles.qr} src={qrSrc} alt={t(lang, 'wechatQrAlt')} />
            </div>
            <p className={styles.hint}>
              {inWeChat ? t(lang, 'wechatHintInApp') : t(lang, 'wechatHintOutside')}
            </p>
          </>
        )}

        {wechat.id && (
          <button type="button" className={styles.copy} onClick={copyId}>
            <Icon name={copied ? 'check' : 'copy'} />
            <span className={styles.copyId}>{wechat.id}</span>
            <span className={styles.copyAction}>
              {copied ? t(lang, 'copied') : t(lang, 'copy')}
            </span>
          </button>
        )}

        {wechat.id && !inWeChat && <p className={styles.steps}>{t(lang, 'wechatSteps')}</p>}
      </div>
    </div>
  )
}
