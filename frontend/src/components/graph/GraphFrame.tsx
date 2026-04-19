import { useState, useCallback } from 'react'
import { RefreshCw } from 'lucide-react'
import { BASE_URL } from '../../api/client'

export function GraphFrame() {
  const [key, setKey] = useState(0)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(() => {
    setLoading(true)
    setKey(k => k + 1)
  }, [])

  const graphUrl = `${BASE_URL}/api/v1/graph/view`

  return (
    <div className="relative rounded-2xl overflow-hidden border border-white/[0.06] bg-surface-800 grain">
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.05]">
        <span className="text-sm font-medium text-white/50">Knowledge Graph</span>
        <button
          onClick={refresh}
          className="flex items-center gap-1.5 text-xs text-white/30 hover:text-white/70 transition-colors"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </button>
      </div>
      <div className="relative">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-surface-800 z-10">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-600 border-t-violet-500" />
          </div>
        )}
        <iframe
          key={key}
          src={graphUrl}
          className="w-full h-[550px] border-0"
          onLoad={() => setLoading(false)}
          title="Knowledge Graph"
        />
      </div>
    </div>
  )
}
