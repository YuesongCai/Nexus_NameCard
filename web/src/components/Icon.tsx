/** Inline icon set. Stroke icons inherit `currentColor`; brand glyphs are filled. */

export type IconName =
  | 'whatsapp'
  | 'linkedin'
  | 'mail'
  | 'phone'
  | 'contact'
  | 'send'
  | 'stop'
  | 'chevron'
  | 'refresh'
  | 'warning'
  | 'check'
  | 'wechat'
  | 'copy'
  | 'close'

const STROKE = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.9,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
}

export function Icon({ name }: { name: IconName }) {
  switch (name) {
    case 'whatsapp':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" fill="currentColor">
          <path d="M12.04 2C6.58 2 2.13 6.45 2.13 11.91c0 1.75.46 3.46 1.32 4.96L2 22l5.25-1.38a9.9 9.9 0 0 0 4.79 1.22h.01c5.46 0 9.91-4.45 9.91-9.91 0-2.65-1.03-5.14-2.9-7.01A9.82 9.82 0 0 0 12.04 2Zm0 18.15h-.01a8.2 8.2 0 0 1-4.19-1.15l-.3-.18-3.12.82.83-3.04-.2-.31a8.19 8.19 0 0 1-1.26-4.38c0-4.54 3.7-8.24 8.25-8.24 2.2 0 4.27.86 5.83 2.42a8.2 8.2 0 0 1 2.41 5.83c0 4.54-3.7 8.23-8.24 8.23Zm4.52-6.17c-.25-.12-1.47-.72-1.69-.81-.23-.08-.39-.12-.56.13-.16.24-.64.8-.78.97-.15.16-.29.18-.53.06-.25-.13-1.05-.39-1.99-1.23-.74-.66-1.23-1.47-1.38-1.71-.14-.25-.01-.38.11-.5.11-.11.25-.29.37-.44.12-.15.16-.25.25-.41.08-.17.04-.31-.02-.43-.06-.13-.56-1.34-.76-1.84-.2-.48-.4-.42-.56-.42l-.47-.01c-.16 0-.43.06-.65.31-.22.24-.86.84-.86 2.05s.88 2.38 1 2.54c.13.17 1.73 2.64 4.19 3.7.59.25 1.04.4 1.4.52.59.18 1.12.16 1.54.1.47-.07 1.47-.6 1.67-1.18.21-.58.21-1.07.15-1.18-.06-.1-.23-.16-.47-.28Z" />
        </svg>
      )
    case 'linkedin':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" fill="currentColor">
          <path d="M6.94 5.5a1.94 1.94 0 1 1-3.88 0 1.94 1.94 0 0 1 3.88 0ZM3.3 8.94h3.35V21H3.3V8.94Zm5.62 0h3.21v1.65h.05c.45-.85 1.54-1.75 3.17-1.75 3.39 0 4.02 2.23 4.02 5.13V21h-3.35v-5.35c0-1.28-.02-2.92-1.78-2.92-1.78 0-2.05 1.39-2.05 2.83V21H8.92V8.94Z" />
        </svg>
      )
    case 'mail':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" {...STROKE}>
          <rect x="2.75" y="4.75" width="18.5" height="14.5" rx="2.5" />
          <path d="m3.5 7.5 7.53 5.1a1.75 1.75 0 0 0 1.94 0L20.5 7.5" />
        </svg>
      )
    case 'phone':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" {...STROKE}>
          <path d="M6.3 3.5h2.4l1.5 4-1.9 1.4a12.6 12.6 0 0 0 6.4 6.4l1.4-1.9 4 1.5v2.4a2.2 2.2 0 0 1-2.4 2.2C10.5 18.9 5.1 13.5 4.1 5.9A2.2 2.2 0 0 1 6.3 3.5Z" />
        </svg>
      )
    case 'contact':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" {...STROKE}>
          <rect x="3" y="4.5" width="18" height="15" rx="2.5" />
          <circle cx="9.5" cy="10.5" r="2.25" />
          <path d="M5.75 16.5a3.9 3.9 0 0 1 7.5 0M15.5 9.5h3.25M15.5 13h3.25" />
        </svg>
      )
    case 'send':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" {...STROKE}>
          <path d="M5 12h13M12 5.5 18.5 12 12 18.5" />
        </svg>
      )
    case 'stop':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" fill="currentColor">
          <rect x="7" y="7" width="10" height="10" rx="2" />
        </svg>
      )
    case 'chevron':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" {...STROKE}>
          <path d="m8 10 4 4 4-4" />
        </svg>
      )
    case 'refresh':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" {...STROKE}>
          <path d="M20 12a8 8 0 1 1-2.5-5.8M20 4v4h-4" />
        </svg>
      )
    case 'warning':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" {...STROKE}>
          <circle cx="12" cy="12" r="8.75" />
          <path d="M12 7.75v5M12 16h.01" />
        </svg>
      )
    case 'check':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" {...STROKE}>
          <path d="m5.5 12.5 4 4 9-9" />
        </svg>
      )
    case 'wechat':
      // Two overlapping speech bubbles — WeChat's recognisable silhouette, drawn filled so
      // it reads as a brand mark next to WhatsApp rather than as a stroke icon.
      return (
        <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
          <path d="M9.2 3C5.2 3 2 5.8 2 9.2c0 1.9 1 3.6 2.7 4.8l-.7 2.1 2.5-1.3c.7.2 1.5.3 2.3.3h.5a5.6 5.6 0 0 1-.2-1.4c0-3.2 3.1-5.8 6.9-5.8h.6C15.9 5.1 12.9 3 9.2 3ZM6.8 8.2a.9.9 0 1 1 0-1.8.9.9 0 0 1 0 1.8Zm4.8 0a.9.9 0 1 1 0-1.8.9.9 0 0 1 0 1.8Z" />
          <path d="M22 13.6c0-2.8-2.7-5-6-5s-6 2.2-6 5 2.7 5 6 5c.7 0 1.4-.1 2-.3l2.1 1.1-.6-1.8c1.5-.9 2.5-2.4 2.5-4Zm-8-.9a.75.75 0 1 1 0-1.5.75.75 0 0 1 0 1.5Zm4 0a.75.75 0 1 1 0-1.5.75.75 0 0 1 0 1.5Z" />
        </svg>
      )
    case 'copy':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" {...STROKE}>
          <rect x="9" y="9" width="11" height="11" rx="2" />
          <path d="M5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1" />
        </svg>
      )
    case 'close':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true" {...STROKE}>
          <path d="M18 6 6 18M6 6l12 12" />
        </svg>
      )
  }
}
