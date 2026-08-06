import type { AgentEvent, ChatTurn, Lang } from '../types'
import { API_BASE } from './config'

/**
 * SSE reader for the §6 event stream.
 *
 * Uses `fetch` + a manual parser rather than `EventSource` for two reasons: the request is
 * a POST with a body, and AgentCore Runtime emits bare `data:` lines with no `event:` line
 * (plus an occasional `: ok` comment injected by the AWS data plane) — so the parser has to
 * ignore anything that isn't a `data:` line and read `type` out of the JSON instead.
 */

export interface ChatHandlers {
  onSources?: (event: Extract<AgentEvent, { type: 'response.sources' }>) => void
  onDelta: (text: string) => void
  onDone: () => void
  onError: (reason: string) => void
}

export interface ChatParams {
  question: string
  lang: Lang
  slug: string
  sessionId: string
  history: ChatTurn[]
  signal: AbortSignal
}

const MAX_HISTORY_TURNS = 8

export async function streamChat(params: ChatParams, handlers: ChatHandlers): Promise<void> {
  const history = params.history
    .filter((turn) => turn.status !== 'error' && turn.content.trim().length > 0)
    .slice(-MAX_HISTORY_TURNS * 2)
    .map((turn) => ({ role: turn.role, content: turn.content }))

  let response: Response
  try {
    response = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'content-type': 'application/json', accept: 'text/event-stream' },
      body: JSON.stringify({
        question: params.question,
        lang: params.lang,
        slug: params.slug,
        sessionId: params.sessionId,
        history,
      }),
      signal: params.signal,
    })
  } catch (error) {
    if ((error as Error).name === 'AbortError') return
    handlers.onError('network')
    return
  }

  if (response.status === 429) {
    handlers.onError('rate_limited')
    return
  }
  if (!response.ok || !response.body) {
    handlers.onError('unavailable')
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let sawTerminal = false

  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      // Frames are separated by a blank line; \r\n tolerated for proxies that rewrite it.
      const separator = /\r?\n\r?\n/g
      for (;;) {
        separator.lastIndex = 0
        const match = separator.exec(buffer)
        if (!match) break
        const frame = buffer.slice(0, match.index)
        buffer = buffer.slice(match.index + match[0].length)
        const event = parseFrame(frame)
        if (event) {
          sawTerminal = dispatch(event, handlers) || sawTerminal
        }
      }
    }
  } catch (error) {
    if ((error as Error).name === 'AbortError') return
    handlers.onError('stream_broken')
    return
  }

  if (!sawTerminal) {
    // Server or proxy hung up mid-answer; treat the partial text as complete rather than
    // dropping what the visitor already read.
    handlers.onDone()
  }
}

function parseFrame(frame: string): AgentEvent | null {
  const payloads: string[] = []
  for (const line of frame.split(/\r?\n/)) {
    if (!line.startsWith('data:')) continue // ignore `: ok`, `id:`, `event:`
    payloads.push(line.slice(5).trimStart())
  }
  if (payloads.length === 0) return null
  try {
    return JSON.parse(payloads.join('\n')) as AgentEvent
  } catch {
    return null
  }
}

/** Returns true when the event is terminal. */
function dispatch(event: AgentEvent, handlers: ChatHandlers): boolean {
  switch (event.type) {
    case 'response.sources':
      handlers.onSources?.(event)
      return false
    case 'response.output_text.delta':
      handlers.onDelta(event.delta)
      return false
    case 'response.completed':
      handlers.onDone()
      return true
    case 'response.failed':
      handlers.onError(event.reason || 'failed')
      return true
    default:
      return false
  }
}
