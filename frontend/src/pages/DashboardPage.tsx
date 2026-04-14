import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { FileText, Upload, MessageSquare, Lightbulb, BookOpen, ArrowRight } from 'lucide-react'
import { useWikiStatus } from '../hooks/useWikiStatus'
import { listJobs } from '../api/ingest'
import { Badge } from '../components/ui/Badge'
import { Spinner } from '../components/ui/Spinner'

const TYPE_CONFIG: Record<string, { color: string; label: string }> = {
  summary:    { color: 'bg-sky-400',    label: 'Summary'    },
  concept:    { color: 'bg-violet-400', label: 'Concept'    },
  connection: { color: 'bg-teal-400',   label: 'Connection' },
  insight:    { color: 'bg-amber-400',  label: 'Insight'    },
  qa:         { color: 'bg-emerald-400',label: 'Q&A'        },
  lint:       { color: 'bg-white/20',   label: 'Lint'       },
}

export function DashboardPage() {
  const { data: status, isLoading: statusLoading } = useWikiStatus()
  const { data: jobs = [] } = useQuery({
    queryKey: ['jobs'],
    queryFn: listJobs,
    refetchInterval: 10_000,
  })

  const recentJobs = [...jobs].reverse().slice(0, 8)
  const totalPages = status?.total_pages ?? 0
  const byType     = status?.by_type ?? {}

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-10">

      {/* Header */}
      <div className="animate-fade-up">
        <h1 className="font-display text-4xl text-[#ede9e3]">Dashboard</h1>
        <p className="text-sm text-white/35 mt-2 font-sans">Your personal knowledge OS</p>
      </div>

      {/* Stats */}
      {statusLoading ? (
        <Spinner label="Loading…" />
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 animate-fade-up-d1">
          {[
            { label: 'Total Pages', value: totalPages,               icon: FileText,   accent: 'text-violet-400' },
            { label: 'Sources',     value: status?.raw_sources ?? 0, icon: BookOpen,   accent: 'text-amber-400'  },
            { label: 'Ideas',       value: status?.ideas_count ?? 0, icon: Lightbulb,  accent: 'text-amber-400'  },
            { label: 'Jobs Run',    value: jobs.length,              icon: Upload,     accent: 'text-white/40'   },
          ].map(({ label, value, icon: Icon, accent }) => (
            <div key={label} className="grain bg-surface-800 border border-white/[0.06] rounded-2xl p-5 relative overflow-hidden">
              {/* subtle top-left glow */}
              <div className="absolute -top-6 -left-6 h-16 w-16 rounded-full bg-violet-500/10 blur-xl pointer-events-none" />
              <div className="flex items-center gap-1.5 mb-4 relative">
                <Icon className={`h-3.5 w-3.5 ${accent}`} />
                <span className="text-[11px] font-medium text-white/30 uppercase tracking-wider">{label}</span>
              </div>
              <p className="stat-number text-4xl text-[#ede9e3] relative">{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Pages by Type */}
      {Object.keys(byType).length > 0 && (() => {
        const sorted   = Object.entries(byType).sort((a, b) => b[1] - a[1])
        const maxCount = sorted[0]?.[1] ?? 1
        return (
          <div className="grain bg-surface-800 border border-white/[0.06] rounded-2xl p-7 animate-fade-up-d2">
            <p className="text-[11px] font-medium text-white/25 uppercase tracking-[0.15em] mb-6">Pages by Type</p>
            <div className="space-y-4">
              {sorted.map(([type, count]) => {
                const cfg = TYPE_CONFIG[type] ?? { color: 'bg-white/20', label: type }
                const pct = (count / maxCount) * 100
                return (
                  <div key={type} className="flex items-center gap-5">
                    <span className="text-sm text-white/60 w-24 shrink-0 font-medium">{cfg.label}</span>
                    <div className="flex-1 h-px bg-white/[0.06]">
                      <div
                        className={`h-px ${cfg.color} transition-all duration-700`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="font-display text-lg text-[#ede9e3] w-8 text-right tabular-nums shrink-0">{count}</span>
                  </div>
                )
              })}
            </div>
          </div>
        )
      })()}

      {/* Quick actions */}
      <div className="grid grid-cols-2 gap-4 animate-fade-up-d3">
        <Link
          to="/ingest"
          className="group grain flex items-center gap-4 p-6 bg-surface-800 border border-white/[0.06] rounded-2xl hover:border-violet-500/25 hover:bg-surface-700 transition-all duration-200"
        >
          <div className="h-11 w-11 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center shrink-0 group-hover:bg-violet-500/15 transition-colors">
            <Upload className="h-5 w-5 text-violet-400" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-medium text-[#ede9e3]">Ingest Source</p>
            <p className="text-xs text-white/30 mt-0.5">URL, text, or file</p>
          </div>
          <ArrowRight className="h-4 w-4 text-white/15 group-hover:text-white/40 group-hover:translate-x-0.5 transition-all shrink-0" />
        </Link>
        <Link
          to="/query"
          className="group grain flex items-center gap-4 p-6 bg-surface-800 border border-white/[0.06] rounded-2xl hover:border-white/15 hover:bg-surface-700 transition-all duration-200"
        >
          <div className="h-11 w-11 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center shrink-0 group-hover:bg-white/8 transition-colors">
            <MessageSquare className="h-5 w-5 text-white/50" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-medium text-[#ede9e3]">Ask a Question</p>
            <p className="text-xs text-white/30 mt-0.5">Query your wiki</p>
          </div>
          <ArrowRight className="h-4 w-4 text-white/15 group-hover:text-white/40 group-hover:translate-x-0.5 transition-all shrink-0" />
        </Link>
      </div>

      {/* Recent jobs */}
      {recentJobs.length > 0 && (
        <div className="animate-fade-up-d4">
          <p className="text-[11px] font-medium text-white/25 uppercase tracking-[0.15em] mb-4">Recent Jobs</p>
          <div className="space-y-2">
            {recentJobs.map(job => (
              <div key={job.job_id} className="flex items-center gap-4 px-5 py-3.5 bg-surface-800 border border-white/[0.05] rounded-xl">
                <span className="text-sm text-white/70 flex-1 truncate font-medium">
                  {job.result?.source_name ?? job.job_id.slice(0, 12)}
                </span>
                <Badge status={job.status} />
                {job.status === 'done' && (
                  <span className="text-xs text-white/25 tabular-nums shrink-0">{job.result?.count} pages</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {totalPages === 0 && !statusLoading && (
        <div className="text-center py-20">
          <BookOpen className="h-12 w-12 mx-auto mb-5 text-white/8" />
          <p className="font-display text-2xl text-white/20">No wiki pages yet</p>
          <p className="text-sm mt-2 text-white/15">Start by ingesting a source.</p>
        </div>
      )}
    </div>
  )
}
