import { t } from '../i18n'
import type { Lang } from '../types'
import { Icon } from './Icon'
import styles from './States.module.css'

/** Skeleton that matches the identity card's silhouette, so nothing jumps on load. */
export function CardSkeleton({ lang }: { lang: Lang }) {
  return (
    <div className={styles.skeleton} role="status" aria-label={t(lang, 'loading')}>
      <div className={styles.stock}>
        <span className={`${styles.line} ${styles.logo}`} />
        <span className={`${styles.line} ${styles.name}`} />
        <span className={`${styles.line} ${styles.title}`} />
        <span className={`${styles.line} ${styles.rule}`} />
        <span className={`${styles.line} ${styles.small}`} />
      </div>
      <span className={`${styles.line} ${styles.button}`} />
      <div className={styles.tiles}>
        <span className={styles.tile} />
        <span className={styles.tile} />
        <span className={styles.tile} />
        <span className={styles.tile} />
      </div>
    </div>
  )
}

export function NotFound({ lang }: { lang: Lang }) {
  return (
    <div className={styles.notFound} role="alert">
      <Icon name="warning" />
      <h1>{t(lang, 'cardNotFound')}</h1>
      <p>{t(lang, 'cardNotFoundBody')}</p>
      <a href="https://noahnexus.ai" target="_blank" rel="noopener noreferrer">
        noahnexus.ai
      </a>
    </div>
  )
}

export function Toast({ message, visible }: { message: string; visible: boolean }) {
  return (
    <div
      className={visible ? `${styles.toast} ${styles.toastOn}` : styles.toast}
      role="status"
      aria-live="polite"
    >
      <Icon name="check" />
      {message}
    </div>
  )
}
