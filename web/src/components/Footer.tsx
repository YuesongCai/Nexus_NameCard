import { pick, t } from '../i18n'
import type { Card, Lang } from '../types'
import styles from './Footer.module.css'

/**
 * Page fine print.
 *
 * Everything the identity card deliberately doesn't carry ends up here: the licensed
 * corporation, its central entity number, the full descriptions behind the licence type
 * codes, the registered address, and the disclaimer. It is all on the page and reachable —
 * just at the bottom, where fine print belongs, instead of eating the fold.
 */
export function Footer({ card, lang }: { card: Card; lang: Lang }) {
  const licence = card.licence

  return (
    <footer className={styles.footer}>
      {licence && (
        <section className={styles.block}>
          <h2 className={styles.blockTitle}>{t(lang, 'regulatory')}</h2>
          <dl className={styles.rows}>
            <dt>{t(lang, 'licensedBy')}</dt>
            <dd>{pick(licence.entity, lang)}</dd>

            {licence.entityCeNumber && (
              <>
                <dt>{t(lang, 'entityCe')}</dt>
                <dd className={styles.mono}>{licence.entityCeNumber}</dd>
              </>
            )}

            {licence.ceNumber && (
              <>
                <dt>{t(lang, 'ceNumber')}</dt>
                <dd className={styles.mono}>{licence.ceNumber}</dd>
              </>
            )}

            {/* Descriptions only — no "第 1 类" / "Type 1" numbering. Compliance dropped the
                1/4/9 codes on 2026-08-10 ("第一类、第四类、第九类都可以不写了"); the approved
                card keeps what the person may actually do and loses the code that has to be
                re-approved whenever their permissions change. Gated on having types at all,
                so a card without them doesn't print a regulator "licensed for nothing". */}
            {licence.types.length > 0 && (
              <>
                <dt>{pick(licence.regulator, lang)}</dt>
                <dd>
                  {licence.types
                    .map((type) => (lang === 'zh' ? type.zh : type.en))
                    .join(lang === 'zh' ? '、' : ' · ')}
                </dd>
              </>
            )}

            {licence.address && (
              <>
                <dt>{lang === 'zh' ? '注册地址' : 'Address'}</dt>
                <dd>{pick(licence.address, lang)}</dd>
              </>
            )}
          </dl>
        </section>
      )}

      {card.memberLine && <p className={styles.member}>{pick(card.memberLine, lang)}</p>}

      <p className={styles.disclaimer}>{t(lang, 'disclaimer')}</p>

      <div className={styles.meta}>
        <span className={styles.powered}>{t(lang, 'poweredBy')}</span>
        <a href="https://noahnexus.ai" target="_blank" rel="noopener noreferrer">
          {t(lang, 'website')}
        </a>
      </div>
    </footer>
  )
}
