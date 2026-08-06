/** Mirrors `api/src/nexus_card/models.py`. Keep the two in step. */

export type Lang = 'en' | 'zh'

export interface Localized {
  en: string
  zh: string
}

export interface Phone {
  label: Localized
  value: string
}

export interface LicenceType {
  code: string
  en: string
  zh: string
}

export interface Licence {
  ceNumber: string
  entityCeNumber?: string
  entity: Localized
  regulator: Localized
  types: LicenceType[]
  address?: Localized
}

export interface WeChat {
  /** WeChat ID (微信号) — the universal fallback: copy, then paste into WeChat search. */
  id?: string | null
  /** Path to the person's exported 个人二维码 image, relative to the site base. */
  qr?: string | null
}

export interface Contacts {
  whatsapp?: string | null
  wechat?: WeChat | null
  phones: Phone[]
  email?: string | null
  linkedin?: string | null
  website?: string | null
}

export interface Card {
  slug: string
  variant: 'standard' | 'licensed'
  coBrand?: 'ark' | null
  name: Localized
  title: Localized
  org: Localized
  location?: Localized
  contacts: Contacts
  licence?: Licence | null
  memberLine?: Localized
}

export interface Suggestion {
  id: string
  label: string
  question: string
}

export interface Intro {
  greeting: string
  suggestions: Suggestion[]
}

export interface Source {
  id: string
  title: string
  score: number
}

export interface ChatTurn {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  status?: 'streaming' | 'done' | 'error'
}

/** §6 event envelopes the client consumes (subset). */
export type AgentEvent =
  | { type: 'response.created'; seq: number; runId: string; model: string }
  | { type: 'response.sources'; seq: number; sources: Source[] }
  | { type: 'response.output_text.delta'; seq: number; delta: string; ttftMs?: number }
  | { type: 'response.completed'; seq: number }
  | { type: 'response.failed'; seq: number; reason: string; code?: string }

export type AnalyticsName =
  | 'card_view'
  | 'contact_tap'
  | 'vcard_save'
  | 'chat_ask'
  | 'chat_error'
  | 'lang_switch'
