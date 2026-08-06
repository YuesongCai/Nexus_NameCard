/**
 * Where the frontend gets its data.
 *
 * Two deployment shapes, one bundle:
 *
 * - **Served by the API** (`make dev`, Docker, any single-origin host). Everything is a
 *   relative `/api/...` call and the chat is live.
 * - **Static host** (GitHub Pages). Card, intro and vCard are pre-rendered files emitted by
 *   `api/scripts/export_static.py`; the chat needs a separately-hosted API, so it stays
 *   disabled until `VITE_API_BASE` is pointed at one. Disabled — not broken: the composer
 *   is replaced by an explicit notice rather than a button that spins forever.
 */

/** Vite's `base`, always with a trailing slash (`/` or `/Nexus_NameCard/`). */
export const BASE_URL: string = import.meta.env.BASE_URL || '/'

/** True when this bundle was built for a static host with no co-located API. */
export const IS_STATIC: boolean = import.meta.env.VITE_STATIC === '1'

/**
 * Origin of the chat API. Empty means same-origin. On a static host an empty value means
 * there is no API at all, which is what `CHAT_ENABLED` keys off.
 */
export const API_ORIGIN: string = (import.meta.env.VITE_API_BASE ?? '').replace(/\/$/, '')

export const API_BASE = `${API_ORIGIN}/api`

/** The chat can only run when something is actually serving `/api/chat`. */
export const CHAT_ENABLED: boolean = !IS_STATIC || API_ORIGIN !== ''

/** Resolve a path against the deployment's base path. */
export function asset(path: string): string {
  return `${BASE_URL}${path.replace(/^\//, '')}`
}
