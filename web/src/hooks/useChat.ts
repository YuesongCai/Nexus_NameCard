import { useCallback, useEffect, useRef, useState } from 'react'

import { streamChat } from '../api/chat'
import { track } from '../api/client'
import type { ChatTurn, Lang, Source } from '../types'

let turnCounter = 0
const nextId = (): string => `t${++turnCounter}`

export interface UseChat {
  turns: ChatTurn[]
  busy: boolean
  ask: (question: string) => void
  stop: () => void
  retryLast: () => void
}

export function useChat(slug: string, lang: Lang, sessionId: string): UseChat {
  const [turns, setTurns] = useState<ChatTurn[]>([])
  const [busy, setBusy] = useState(false)

  const controllerRef = useRef<AbortController | null>(null)
  const turnsRef = useRef<ChatTurn[]>([])
  const lastQuestionRef = useRef<string>('')

  turnsRef.current = turns

  // A live stream must not outlive the component or a language switch.
  useEffect(() => () => controllerRef.current?.abort(), [])

  const stop = useCallback(() => {
    controllerRef.current?.abort()
    controllerRef.current = null
    setBusy(false)
    setTurns((prev) =>
      prev.map((turn) =>
        turn.status === 'streaming' ? { ...turn, status: 'done' as const } : turn,
      ),
    )
  }, [])

  const run = useCallback(
    (question: string) => {
      const controller = new AbortController()
      controllerRef.current = controller
      lastQuestionRef.current = question
      setBusy(true)

      const history = turnsRef.current
      const answerId = nextId()

      setTurns((prev) => [
        ...prev,
        { id: nextId(), role: 'user', content: question, status: 'done' },
        { id: answerId, role: 'assistant', content: '', status: 'streaming' },
      ])

      const patch = (update: (turn: ChatTurn) => ChatTurn): void => {
        setTurns((prev) => prev.map((turn) => (turn.id === answerId ? update(turn) : turn)))
      }

      track('chat_ask', { slug, sessionId, detail: lang })

      void streamChat(
        { question, lang, slug, sessionId, history, signal: controller.signal },
        {
          onSources: (event) => {
            const sources: Source[] = event.sources.slice(0, 3)
            patch((turn) => ({ ...turn, sources }))
          },
          onDelta: (text) => {
            patch((turn) => ({ ...turn, content: turn.content + text }))
          },
          onDone: () => {
            patch((turn) => ({ ...turn, status: 'done' }))
            controllerRef.current = null
            setBusy(false)
          },
          onError: (reason) => {
            track('chat_error', { slug, sessionId, detail: reason })
            patch((turn) => ({ ...turn, status: 'error', content: turn.content || reason }))
            controllerRef.current = null
            setBusy(false)
          },
        },
      )
    },
    [lang, sessionId, slug],
  )

  const ask = useCallback(
    (question: string) => {
      const trimmed = question.trim()
      if (!trimmed || busy) return
      run(trimmed)
    },
    [busy, run],
  )

  const retryLast = useCallback(() => {
    if (busy || !lastQuestionRef.current) return
    // Drop the failed exchange so the transcript doesn't accumulate dead ends.
    setTurns((prev) => {
      const next = [...prev]
      while (next.length > 0 && next[next.length - 1]?.role === 'assistant') next.pop()
      while (next.length > 0 && next[next.length - 1]?.role === 'user') next.pop()
      return next
    })
    const question = lastQuestionRef.current
    // Let the removal commit before the new turn is appended.
    queueMicrotask(() => run(question))
  }, [busy, run])

  return { turns, busy, ask, stop, retryLast }
}
