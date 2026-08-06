import type { AnalyticsName, Card, Intro, Lang } from '../types'
import { API_BASE, API_ORIGIN, IS_STATIC, asset } from './config'

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url, {
    signal,
    headers: { accept: 'application/json' },
  })
  if (!response.ok) {
    throw new ApiError(`${url} failed`, response.status)
  }
  return (await response.json()) as T
}

export function fetchCard(slug: string, signal?: AbortSignal): Promise<Card> {
  const safe = encodeURIComponent(slug)
  return getJson<Card>(
    IS_STATIC ? asset(`data/cards/${safe}.json`) : `${API_BASE}/cards/${safe}`,
    signal,
  )
}

export function fetchIntro(slug: string, lang: Lang, signal?: AbortSignal): Promise<Intro> {
  const safe = encodeURIComponent(slug)
  return getJson<Intro>(
    IS_STATIC
      ? asset(`data/intro/${safe}.${lang}.json`)
      : `${API_BASE}/cards/${safe}/intro?lang=${lang}`,
    signal,
  )
}

export function vcardUrl(slug: string, lang: Lang): string {
  const safe = encodeURIComponent(slug)
  // Static builds ship real `.vcf` files: a genuine file response with the right
  // content-type is the only thing iOS Safari opens into Contacts reliably.
  return IS_STATIC
    ? asset(`vcard/${safe}.${lang}.vcf`)
    : `${API_BASE}/cards/${safe}/vcard?lang=${lang}`
}

/**
 * Fire-and-forget product analytics. `sendBeacon` survives the page being backgrounded
 * the instant someone taps through to WhatsApp — which is exactly the event we care most
 * about not losing.
 *
 * On a static host with no API wired up there is nothing to receive these, so they are
 * dropped at the source rather than firing a request per tap that 404s. The moment
 * `VITE_API_BASE` points somewhere, they start flowing again.
 */
export function track(
  name: AnalyticsName,
  payload: { slug?: string; detail?: string; sessionId?: string } = {},
): void {
  if (IS_STATIC && API_ORIGIN === '') return

  const body = JSON.stringify({ name, ...payload })
  try {
    if (navigator.sendBeacon) {
      navigator.sendBeacon(`${API_BASE}/events`, new Blob([body], { type: 'application/json' }))
      return
    }
    void fetch(`${API_BASE}/events`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body,
      keepalive: true,
    })
  } catch {
    // Analytics must never break the page.
  }
}
