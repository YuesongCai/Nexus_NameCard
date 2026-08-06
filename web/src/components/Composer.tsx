import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'

import { t } from '../i18n'
import type { Lang } from '../types'
import { Icon } from './Icon'
import styles from './Composer.module.css'

interface Props {
  lang: Lang
  busy: boolean
  onSubmit: (question: string) => void
  onStop: () => void
}

const MAX_CHARS = 600
const MAX_ROWS_PX = 116

export function Composer({ lang, busy, onSubmit, onStop }: Props) {
  const [value, setValue] = useState('')
  const [composing, setComposing] = useState(false)
  const ref = useRef<HTMLTextAreaElement>(null)

  // Auto-grow: reset to auto first so the box can shrink when text is deleted.
  const resize = useCallback(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, MAX_ROWS_PX)}px`
  }, [])

  useLayoutEffect(resize, [resize, value])

  // The first measurement can land before the webfont swaps in or before the viewport
  // settles, which leaves the box stuck at the wrong height. Re-measure on both.
  useEffect(() => {
    void document.fonts?.ready.then(resize)
    window.addEventListener('resize', resize)
    return () => window.removeEventListener('resize', resize)
  }, [resize])

  const submit = useCallback(() => {
    const question = value.trim()
    if (!question || busy) return
    onSubmit(question)
    setValue('')
  }, [busy, onSubmit, value])

  return (
    <form
      className={styles.bar}
      onSubmit={(event) => {
        event.preventDefault()
        submit()
      }}
    >
      <textarea
        ref={ref}
        className={styles.input}
        value={value}
        rows={1}
        maxLength={MAX_CHARS}
        placeholder={t(lang, 'placeholder')}
        aria-label={t(lang, 'placeholder')}
        enterKeyHint="send"
        onChange={(event) => setValue(event.target.value)}
        // IME guard: Enter while composing Chinese must commit the candidate, not send.
        onCompositionStart={() => setComposing(true)}
        onCompositionEnd={() => setComposing(false)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey && !composing) {
            event.preventDefault()
            submit()
          }
        }}
      />

      {busy ? (
        <button
          type="button"
          className={`${styles.action} ${styles.stop}`}
          onClick={onStop}
          aria-label={t(lang, 'stop')}
        >
          <Icon name="stop" />
        </button>
      ) : (
        <button
          type="submit"
          className={styles.action}
          disabled={value.trim().length === 0}
          aria-label={t(lang, 'send')}
        >
          <Icon name="send" />
        </button>
      )}
    </form>
  )
}
