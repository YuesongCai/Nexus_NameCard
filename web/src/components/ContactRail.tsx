import { track, vcardUrl } from '../api/client'
import { t } from '../i18n'
import type { Card, Lang } from '../types'
import { Icon } from './Icon'
import styles from './ContactRail.module.css'

interface Props {
  card: Card
  lang: Lang
  sessionId: string
  onSaved: () => void
}

interface Action {
  key: string
  href: string
  label: string
  icon: 'whatsapp' | 'linkedin' | 'mail' | 'phone'
  external?: boolean
}

function buildActions(card: Card, lang: Lang): Action[] {
  const actions: Action[] = []
  const { whatsapp, linkedin, email, phones } = card.contacts

  if (whatsapp) {
    actions.push({
      key: 'whatsapp',
      href: `https://wa.me/${whatsapp.replace(/[^\d]/g, '')}`,
      label: t(lang, 'whatsapp'),
      icon: 'whatsapp',
      external: true,
    })
  }
  if (linkedin) {
    actions.push({
      key: 'linkedin',
      href: linkedin,
      label: t(lang, 'linkedin'),
      icon: 'linkedin',
      external: true,
    })
  }
  if (email) {
    actions.push({ key: 'email', href: `mailto:${email}`, label: t(lang, 'email'), icon: 'mail' })
  }
  const primaryPhone = phones[0]
  if (primaryPhone) {
    actions.push({
      key: 'phone',
      href: `tel:${primaryPhone.value.replace(/\s/g, '')}`,
      label: t(lang, 'call'),
      icon: 'phone',
    })
  }
  return actions
}

export function ContactRail({ card, lang, sessionId, onSaved }: Props) {
  const actions = buildActions(card, lang)

  return (
    <section className={styles.wrap} aria-label={t(lang, 'saveContact')}>
      <a
        className={styles.save}
        href={vcardUrl(card.slug, lang)}
        // `download` keeps Android/desktop from navigating away; iOS ignores it and opens
        // the Contacts sheet directly, which is the behaviour we want on both.
        download
        onClick={() => {
          track('vcard_save', { slug: card.slug, sessionId })
          onSaved()
        }}
      >
        <Icon name="contact" />
        <span>{t(lang, 'saveContact')}</span>
      </a>

      {actions.length > 0 && (
        <nav
          className={styles.rail}
          style={{ ['--rail-count' as string]: String(actions.length) }}
        >
          {actions.map((action) => (
            <a
              key={action.key}
              className={styles.tile}
              href={action.href}
              {...(action.external ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
              onClick={() => track('contact_tap', { slug: card.slug, sessionId, detail: action.key })}
            >
              <Icon name={action.icon} />
              <span className={styles.tileLabel}>{action.label}</span>
            </a>
          ))}
        </nav>
      )}

      {card.contacts.phones.length > 1 && (
        <ul className={styles.extraPhones}>
          {card.contacts.phones.slice(1).map((phone) => (
            <li key={phone.value}>
              <span className={styles.phoneLabel}>
                {lang === 'zh' ? phone.label.zh : phone.label.en}
              </span>
              <a
                href={`tel:${phone.value.replace(/\s/g, '')}`}
                onClick={() =>
                  track('contact_tap', { slug: card.slug, sessionId, detail: 'phone_alt' })
                }
              >
                {phone.value}
              </a>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
