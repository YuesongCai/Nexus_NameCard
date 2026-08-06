import type { Lang } from '../types'
import { NexusLogo } from './NexusLogo'
import styles from './TopBar.module.css'

interface Props {
  lang: Lang
  onLangChange: (lang: Lang) => void
}

export function TopBar({ lang, onLangChange }: Props) {
  return (
    <header className={styles.bar}>
      <a
        className={styles.logo}
        href="https://noahnexus.ai"
        target="_blank"
        rel="noopener noreferrer"
      >
        <NexusLogo variant="dark" height={24} />
      </a>

      <div className={styles.toggle} role="group" aria-label="Language">
        <button
          type="button"
          className={lang === 'en' ? styles.active : undefined}
          aria-pressed={lang === 'en'}
          onClick={() => onLangChange('en')}
        >
          EN
        </button>
        <button
          type="button"
          className={lang === 'zh' ? styles.active : undefined}
          aria-pressed={lang === 'zh'}
          onClick={() => onLangChange('zh')}
        >
          中
        </button>
      </div>
    </header>
  )
}
