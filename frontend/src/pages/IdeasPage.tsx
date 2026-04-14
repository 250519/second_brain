import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Lightbulb, Copy, Check, ShieldCheck, Clock } from 'lucide-react'
import { getIdeas, postLint } from '../api/wiki'
import { MarkdownRenderer } from '../components/ui/MarkdownRenderer'
import { Spinner } from '../components/ui/Spinner'
import { useToast } from '../components/ui/Toast'

export function IdeasPage() {
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null)
  const [lintReport, setLintReport] = useState<string | null>(null)
  const { toast } = useToast()

  const { data: ideasData, isLoading } = useQuery({
    queryKey: ['ideas'],
    queryFn: getIdeas,
  })

  const lintMutation = useMutation({
    mutationFn: postLint,
    onSuccess: data => setLintReport(data.report),
    onError: () => toast('Lint failed', 'error'),
  })

  function copyIdea(text: string, i: number) {
    navigator.clipboard.writeText(text)
    setCopiedIdx(i)
    setTimeout(() => setCopiedIdx(null), 2000)
  }

  const ideas = ideasData?.ideas ?? []

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="font-display text-4xl text-[#ede9e3]">Ideas</h1>
        <p className="text-sm text-white/35 mt-2">Research questions and directions from your wiki</p>
      </div>

      {/* Ideas list */}
      {isLoading ? (
        <Spinner label="Loading ideas..." />
      ) : ideas.length === 0 ? (
        <div className="text-center py-12 text-white/20">
          <Lightbulb className="h-10 w-10 mx-auto mb-3 opacity-30" />
          <p className="text-sm">No ideas yet — ingest some sources first</p>
        </div>
      ) : (
        <div>
          <p className="text-[11px] font-medium text-white/25 uppercase tracking-[0.15em] mb-4">
            {ideas.length} research ideas
          </p>
          <ul className="space-y-2">
            {ideas.map((idea, i) => (
              <li
                key={i}
                className="flex items-start gap-3 px-5 py-4 bg-surface-800 border border-white/[0.06] rounded-2xl grain group"
              >
                <Lightbulb className="h-4 w-4 text-amber-400 mt-0.5 shrink-0" />
                <span className="flex-1 text-sm text-white/80">{idea}</span>
                <button
                  onClick={() => copyIdea(idea, i)}
                  aria-label={copiedIdx === i ? 'Idea copied' : 'Copy idea'}
                  className="text-white/20 hover:text-white/60 opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  {copiedIdx === i ? <Check className="h-3.5 w-3.5 text-green-400" /> : <Copy className="h-3.5 w-3.5" />}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Lint section */}
      <div className="border-t border-white/5 pt-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="font-display text-xl text-[#ede9e3]">Wiki Health Check</h2>
            <p className="text-xs text-white/35 mt-1">Detect contradictions, orphan pages, and knowledge gaps</p>
          </div>
          <button
            onClick={() => lintMutation.mutate()}
            disabled={lintMutation.isPending}
            className="flex items-center gap-2 px-3 py-1.5 bg-surface-700 hover:bg-surface-600 border border-white/10 disabled:opacity-50 text-white/70 text-sm rounded-lg transition-colors"
          >
            {lintMutation.isPending ? <Spinner size="sm" /> : <ShieldCheck className="h-4 w-4" />}
            Run Lint
          </button>
        </div>

        {lintMutation.isPending && (
          <p className="text-xs text-white/30 flex items-center gap-1.5 mb-3">
            <Clock className="h-3.5 w-3.5" />
            Analyzing wiki — this may take up to 30 seconds...
          </p>
        )}

        {lintReport && (
          <div className="bg-surface-800 border border-white/5 rounded-xl p-5">
            <MarkdownRenderer content={lintReport} />
          </div>
        )}
      </div>
    </div>
  )
}
