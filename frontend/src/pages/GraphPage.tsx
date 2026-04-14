import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Network, Zap } from 'lucide-react'
import { postGraphAnalyze } from '../api/graph'
import { GraphStats } from '../components/graph/GraphStats'
import { GraphFrame } from '../components/graph/GraphFrame'
import { MarkdownRenderer } from '../components/ui/MarkdownRenderer'
import { Spinner } from '../components/ui/Spinner'
import { useToast } from '../components/ui/Toast'

export function GraphPage() {
  const [report, setReport] = useState<string | null>(null)
  const { toast } = useToast()

  const mutation = useMutation({
    mutationFn: postGraphAnalyze,
    onSuccess: data => setReport(data.report),
    onError: () => toast('Graph analysis failed', 'error'),
  })

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-4xl text-[#ede9e3]">Knowledge Graph</h1>
          <p className="text-sm text-white/35 mt-1">Visualize concepts and their relationships</p>
        </div>
        <button
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className="flex items-center gap-2 px-4 py-2.5 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white text-sm font-medium rounded-xl transition-colors"
        >
          {mutation.isPending ? <Spinner size="sm" /> : <Zap className="h-4 w-4" />}
          Analyze Graph
        </button>
      </div>

      {mutation.isPending && (
        <p className="text-xs text-white/40 flex items-center gap-1.5">
          <Network className="h-3.5 w-3.5" />
          Running graph analysis — this may take up to 30 seconds...
        </p>
      )}

      <GraphStats />
      <GraphFrame />

      {report && (
        <div className="bg-surface-800 border border-white/5 rounded-xl p-5">
          <p className="text-[11px] font-medium text-white/25 uppercase tracking-[0.15em] mb-4 flex items-center gap-1.5">
            <Network className="h-3.5 w-3.5" /> Analysis Report
          </p>
          <MarkdownRenderer content={report} />
        </div>
      )}
    </div>
  )
}
