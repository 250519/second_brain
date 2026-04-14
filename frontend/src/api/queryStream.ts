import { BASE_URL } from './client'

interface StreamCallbacks {
  onDelta: (delta: string) => void
  onDone: () => void
  onError: (err: Error) => void
}

export async function streamQuery(
  question: string,
  fileBack: boolean,
  { onDelta, onDone, onError }: StreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  let response: Response
  try {
    response = await fetch(`${BASE_URL}/api/v1/query/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, file_back: fileBack }),
      signal,
    })
  } catch (err) {
    onError(err instanceof Error ? err : new Error(String(err)))
    return
  }

  if (!response.ok || !response.body) {
    onError(new Error(`Server error: ${response.status}`))
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''  // keep incomplete last line

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const data = line.slice(6).trim()
        if (data === '[DONE]') { onDone(); return }
        try {
          const { delta } = JSON.parse(data) as { delta: string }
          if (delta) onDelta(delta)
        } catch { /* malformed chunk, skip */ }
      }
    }
  } catch (err) {
    if ((err as Error).name !== 'AbortError') {
      onError(err instanceof Error ? err : new Error(String(err)))
    }
  }
}
