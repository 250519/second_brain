import { useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ChevronRight } from 'lucide-react'
import { apiClient } from '../../api/client'

const routeLabels: Record<string, string> = {
  '':      'Dashboard',
  ingest:  'Ingest',
  query:   'Query',
  wiki:    'Wiki',
  graph:   'Graph',
  ideas:   'Ideas',
}

export function TopBar() {
  const { pathname } = useLocation()
  const segments = pathname.split('/').filter(Boolean)

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => apiClient.get('/health').then(r => r.data),
    refetchInterval: 30_000,
    retry: false,
  })

  const isOnline = health?.status === 'ok'

  return (
    <header className="flex items-center justify-between px-6 py-3 border-b border-white/[0.05] bg-surface-900 shrink-0">
      <nav className="flex items-center gap-1.5 text-sm font-sans">
        <span className="text-white/20 text-xs">Home</span>
        {segments.map((seg, i) => (
          <span key={i} className="flex items-center gap-1.5">
            <ChevronRight className="h-3 w-3 text-white/15" />
            <span className={
              i === segments.length - 1
                ? 'text-[#ede9e3] text-xs font-medium'
                : 'text-white/25 text-xs'
            }>
              {routeLabels[seg] ?? seg.replace(/-/g, ' ')}
            </span>
          </span>
        ))}
      </nav>

      <div className="flex items-center gap-2">
        <span className={`h-1.5 w-1.5 rounded-full ${isOnline ? 'bg-emerald-400' : 'bg-red-500'}`} />
        <span className="text-[11px] text-white/25">{isOnline ? 'API online' : 'API offline'}</span>
      </div>
    </header>
  )
}
