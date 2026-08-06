import { pick, other, t } from '../i18n'
import type { Card, Lang } from '../types'
import { ArkMark, NexusLogo } from './NexusLogo'
import styles from './IdentityCard.module.css'

interface Props {
  card: Card
  lang: Lang
}

/**
 * The identity block — inked stock on the cream page.
 *
 * Kept to four lines: name, title, the SFC line where there is one, and the member-firm
 * line. Everything else a regulator wants on record (licensed entity, central entity
 * number, full licence descriptions, registered address) lives in the page footer. A phone
 * screen has room for one thing above the fold, and that thing is who this person is —
 * pushing the fine print down is what keeps the contact buttons reachable without a scroll.
 */
export function IdentityCard({ card, lang }: Props) {
  const name = pick(card.name, lang)
  const nameAlt = other(card.name, lang)
  const title = pick(card.title, lang)
  const titleAlt = other(card.title, lang)
  const licence = card.licence

  const licenceLine = licence
    ? [
        `${t(lang, 'ceNumber')} ${licence.ceNumber}`,
        licence.types.length > 0 &&
          (lang === 'zh'
            ? `第 ${licence.types.map((type) => type.code).join(' / ')} 类`
            : `Type ${licence.types.map((type) => type.code).join(' / ')}`),
      ]
        .filter(Boolean)
        .join(' · ')
    : null

  return (
    <article className={styles.card}>
      <header className={styles.brand}>
        <NexusLogo variant="light" height={22} />
        {card.coBrand === 'ark' && (
          <>
            <span className={styles.divider} aria-hidden="true" />
            <ArkMark height={19} />
          </>
        )}
      </header>

      <div className={styles.identity}>
        <h1 className={styles.name}>
          {name}
          {nameAlt && <span className={styles.nameAlt}>{nameAlt}</span>}
        </h1>
        <p className={styles.title}>{title}</p>
        {titleAlt && <p className={styles.titleAlt}>{titleAlt}</p>}
      </div>

      <hr className={styles.rule} />

      <div className={styles.fine}>
        {licenceLine && <p className={styles.licence}>{licenceLine}</p>}
        {card.memberLine && <p className={styles.member}>{pick(card.memberLine, lang)}</p>}
      </div>
    </article>
  )
}
