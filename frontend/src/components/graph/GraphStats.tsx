import { useQuery } from '@tanstack/react-query'
import { getGraphData } from '../../api/graph'
import { Spinner } from '../ui/Spinner'
import { Network } from 'lucide-react'

export function GraphStats() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['graph-data'],
    queryFn: getGraphData,
    retry: false,
  })

  if (isLoading) return <Spinner size="sm" label="Loading graph data..." />
  if (isError || !data) return (
    <p className="text-sm text-white/30">No graph data yet — ingest some sources first.</p>
  )

  const topNodes = [...data.nodes]
    .sort((a, b) => b.centrality - a.centrality)
    .slice(0, 5)

  return (
    <div className="grid grid-cols-3 gap-4">
      {[
        { label: 'Nodes',      value: data.nodes.length },
        { label: 'Edges',      value: data.edges.length },
        { label: 'Avg Degree', value: data.nodes.length > 0
          ? (data.nodes.reduce((s, n) => s + n.degree, 0) / data.nodes.length).toFixed(1)
          : '—' },
      ].map(({ label, value }) => (
        <div key={label} className="grain bg-surface-800 border border-white/[0.06] rounded-2xl p-5">
          <p className="text-[11px] font-medium text-white/25 uppercase tracking-wider mb-3">{label}</p>
          <p className="stat-number text-4xl text-[#ede9e3]">{value}</p>
        </div>
      ))}

      {topNodes.length > 0 && (
        <div className="col-span-3 grain bg-surface-800 border border-white/[0.06] rounded-2xl p-5">
          <p className="text-[11px] font-medium text-white/25 uppercase tracking-[0.15em] mb-4 flex items-center gap-1.5">
            <Network className="h-3 w-3" /> Top Concepts by Centrality
          </p>
          <div className="space-y-3">
            {topNodes.map((node, i) => (
              <div key={node.id} className="flex items-center gap-4">
                <span className="font-display text-sm text-white/20 w-4 shrink-0">{i + 1}</span>
                <span className="text-sm text-white/70 flex-1 truncate font-medium">{node.id}</span>
                <div className="w-20 bg-white/[0.05] rounded-full h-px">
                  <div
                    className="bg-violet-400 h-px rounded-full"
                    style={{ width: `${Math.min(node.centrality * 500, 100)}%` }}
                  />
                </div>
                <span className="text-xs text-white/30 w-12 text-right font-mono">
                  {node.centrality.toFixed(3)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
