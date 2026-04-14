import { useState, useCallback, useEffect } from 'react'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  createdAt: number
}

export interface ChatSession {
  id: string
  title: string
  messages: ChatMessage[]
  createdAt: number
  updatedAt: number
}

const STORAGE_KEY = 'second-brain-chat-sessions'

function load(): ChatSession[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')
  } catch {
    return []
  }
}

function save(sessions: ChatSession[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
}

export function useQuerySessions() {
  const [sessions, setSessions] = useState<ChatSession[]>(load)
  const [activeId, setActiveId] = useState<string | null>(
    () => load()[0]?.id ?? null
  )

  // Persist whenever sessions change
  useEffect(() => { save(sessions) }, [sessions])

  const activeSession = sessions.find(s => s.id === activeId) ?? null

  const createSession = useCallback((): ChatSession => {
    const s: ChatSession = {
      id: crypto.randomUUID(),
      title: 'New Chat',
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    }
    setSessions(prev => [s, ...prev])
    setActiveId(s.id)
    return s
  }, [])

  const deleteSession = useCallback((id: string) => {
    setSessions(prev => {
      const next = prev.filter(s => s.id !== id)
      if (activeId === id) setActiveId(next[0]?.id ?? null)
      return next
    })
  }, [activeId])

  const appendMessage = useCallback((sessionId: string, msg: ChatMessage) => {
    setSessions(prev => prev.map(s =>
      s.id !== sessionId ? s : {
        ...s,
        title: s.messages.length === 0 && msg.role === 'user'
          ? msg.content.slice(0, 60)
          : s.title,
        messages: [...s.messages, msg],
        updatedAt: Date.now(),
      }
    ))
  }, [])

  const updateLastAssistantMessage = useCallback((sessionId: string, content: string) => {
    setSessions(prev => prev.map(s => {
      if (s.id !== sessionId) return s
      const msgs = [...s.messages]
      const last = msgs[msgs.length - 1]
      if (last?.role === 'assistant') {
        msgs[msgs.length - 1] = { ...last, content }
      }
      return { ...s, messages: msgs, updatedAt: Date.now() }
    }))
  }, [])

  return {
    sessions,
    activeId,
    activeSession,
    setActiveId,
    createSession,
    deleteSession,
    appendMessage,
    updateLastAssistantMessage,
  }
}
