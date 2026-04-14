import { useState, useMemo } from 'react'
import { Link, Outlet, useMatch } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { BookOpen, Search, List, AlignLeft } from 'lucide-react'
import { getWikiIndex } from '../api/wiki'
import { useWikiPages } from '../hooks/useWikiPages'
import { parseIndex, type IndexEntry } from '../lib/parseIndex'
import { parseWikiPath } from '../lib/parseWikiPath'
import { MarkdownRenderer } from '../components/ui/MarkdownRenderer'
import { Spinner } from '../components/ui/Spinner'

// ── Type config ────────────────────────────────────────────────────────────────

const TYPE_ORDER = ['summary', 'concept', 'connection', 'insight', 'qa', 'lint'] as const

const TYPE_CONFIG: Record<string, { label: string; border: string; badge: string; dot: string }> = {
  summary:    { label: 'Summary',    border: 'border-l-blue-500',   badge: 'bg-blue-500/15 text-blue-400',   dot: 'bg-blue-500'   },
  concept:    { label: 'Concept',    border: 'border-l-violet-500', badge: 'bg-violet-500/15 text-violet-400', dot: 'bg-violet-500' },
  connection: { label: 'Connection', border: 'border-l-cyan-500',   badge: 'bg-cyan-500/15 text-cyan-400',   dot: 'bg-cyan-500'   },
  insight:    { label: 'Insight',    border: 'border-l-amber-500',  badge: 'bg-amber-500/15 text-amber-400', dot: 'bg-amber-500'  },
  qa:         { label: 'Q&A',        border: 'border-l-green-500',  badge: 'bg-green-500/15 text-green-400', dot: 'bg-green-500'  },
  lint:       { label: 'Lint',       border: 'border-l-white/30',   badge: 'bg-white/5 text-white/40',       dot: 'bg-white/30'   },
}

// ── Page card ──────────────────────────────────────────────────────────────────

function PageCard({ entry, active }: { entry: IndexEntry; active: boolean }) {
  const { type, title, summary, path } = entry
  const [t, slug] = path.split('/')
  const cfg = TYPE_CONFIG[type] ?? TYPE_CONFIG.concept

  return (
    <Link
      to={`/wiki/${t}/${slug}`}
      className={`block border-l-2 pl-3 pr-3 py-2.5 rounded-r-md transition-colors ${
        active
          ? `${cfg.border} bg-white/5`
          : `border-l-transparent hover:${cfg.border} hover:bg-white/5`
      }`}
    >
      <p className={`text-sm font-medium truncate ${active ? 'text-white' : 'text-white/70'}`}>
        {title}
      </p>
      {summary && (
        <p className="text-xs text-white/30 truncate mt-0.5">{summary}</p>
      )}
    </Link>
  )
}

// ── Index view ─────────────────────────────────────────────────────────────────

function IndexView() {
  const { data, isLoading } = useQuery({
    queryKey: ['wiki-index'],
    queryFn: getWikiIndex,
    staleTime: 30_000,
  })

  if (isLoading) return <div className="flex justify-center pt-16"><Spinner label="Loading index…" /></div>
  if (!data?.index) return <p className="p-8 text-sm text-white/30">Index is empty — ingest some sources first.</p>

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <MarkdownRenderer content={data.index} />
    </div>
  )
}

// ── Main WikiPage ──────────────────────────────────────────────────────────────

type Tab = 'browse' | 'index'

export function WikiPage() {
  const [tab, setTab] = useState<Tab>('browse')
  const [filter, setFilter] = useState('')
  const [activeType, setActiveType] = useState<string>('all')

  const { data: pages = [], isLoading } = useWikiPages()
  const { data: indexData } = useQuery({
    queryKey: ['wiki-index'],
    queryFn: getWikiIndex,
    staleTime: 30_000,
  })

  const onDetail = useMatch('/wiki/:type/:slug')

  // Parse index entries for rich metadata (title + summary)
  const indexEntries = useMemo<IndexEntry[]>(() => {
    if (!indexData?.index) return []
    return parseIndex(indexData.index)
  }, [indexData])

  // Build a lookup: path → entry (for cards)
  const entryByPath = useMemo(() => {
    const m: Record<string, IndexEntry> = {}
    for (const e of indexEntries) m[e.path] = e
    return m
  }, [indexEntries])

  // Fallback: build entries from raw page list when index hasn't loaded yet
  const allEntries = useMemo<IndexEntry[]>(() => {
    return pages.map(p => {
      const { type, slug, displayName } = parseWikiPath(p)
      const path = `${type}/${slug}`
      return entryByPath[path] ?? { path, type, title: displayName, summary: '' }
    })
  }, [pages, entryByPath])

  const filtered = useMemo(() => {
    return allEntries.filter(e => {
      const matchType = activeType === 'all' || e.type === activeType
      const matchText = filter === '' ||
        e.title.toLowerCase().includes(filter.toLowerCase()) ||
        e.summary.toLowerCase().includes(filter.toLowerCase())
      return matchType && matchText
    })
  }, [allEntries, activeType, filter])

  const grouped = useMemo(() => {
    const g: Record<string, IndexEntry[]> = {}
    for (const e of filtered) {
      ;(g[e.type] ??= []).push(e)
    }
    return g
  }, [filtered])

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: allEntries.length }
    for (const e of allEntries) c[e.type] = (c[e.type] ?? 0) + 1
    return c
  }, [allEntries])

  const tabClass = (t: Tab) =>
    `flex items-center gap-1.5 px-3 py-2.5 text-sm font-medium border-b-2 transition-colors ${
      tab === t
        ? 'border-violet-500 text-violet-300'
        : 'border-transparent text-white/40 hover:text-white/70'
    }`

  return (
    <div className="flex h-full overflow-hidden flex-col">
      {/* Top bar: tabs */}
      <div className="flex items-center border-b border-white/5 px-4 shrink-0">
        <button className={tabClass('browse')} onClick={() => setTab('browse')}>
          <List className="h-4 w-4" /> Browse
        </button>
        <button className={tabClass('index')} onClick={() => setTab('index')}>
          <AlignLeft className="h-4 w-4" /> Index
        </button>
        {pages.length > 0 && (
          <span className="ml-auto text-xs text-white/20">{pages.length} pages</span>
        )}
      </div>

      {tab === 'index' ? (
        <div className="flex-1 overflow-y-auto">
          <IndexView />
        </div>
      ) : (
        <div className="flex flex-1 overflow-hidden">
          {/* Left: page list */}
          <div className="w-72 shrink-0 flex flex-col border-r border-white/5 overflow-hidden">
            {/* Search */}
            <div className="px-3 pt-3 pb-2">
              <div className="flex items-center gap-2 bg-surface-800 border border-white/5 rounded-lg px-2.5 py-1.5">
                <Search className="h-3.5 w-3.5 text-white/30 shrink-0" />
                <input
                  value={filter}
                  onChange={e => setFilter(e.target.value)}
                  placeholder="Search pages…"
                  aria-label="Search pages"
                  className="flex-1 bg-transparent text-sm text-white/80 placeholder-white/20 focus:outline-none min-w-0"
                />
              </div>
            </div>

            {/* Type filter chips */}
            <div className="px-3 pb-2 flex flex-wrap gap-1.5">
              {(['all', ...TYPE_ORDER] as const).map(t => {
                const cfg = t === 'all' ? null : TYPE_CONFIG[t]
                const count = counts[t] ?? 0
                if (t !== 'all' && count === 0) return null
                return (
                  <button
                    key={t}
                    onClick={() => setActiveType(t)}
                    className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-xs transition-colors ${
                      activeType === t
                        ? t === 'all'
                          ? 'bg-white/15 text-white'
                          : `${cfg!.badge} ring-1 ring-current`
                        : 'bg-white/5 text-white/40 hover:text-white/70'
                    }`}
                  >
                    {cfg && <span className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} />}
                    {t === 'all' ? 'All' : cfg!.label}
                    <span className="text-white/30 ml-0.5">{count}</span>
                  </button>
                )
              })}
            </div>

            {/* Page list */}
            <div className="flex-1 overflow-y-auto px-2 pb-3 space-y-0.5">
              {isLoading ? (
                <div className="flex justify-center py-8"><Spinner size="sm" /></div>
              ) : filtered.length === 0 ? (
                <div className="text-center py-10 text-white/20">
                  <BookOpen className="h-6 w-6 mx-auto mb-2 opacity-30" />
                  <p className="text-xs">{pages.length === 0 ? 'No pages yet' : 'No matches'}</p>
                </div>
              ) : activeType === 'all' ? (
                TYPE_ORDER.filter(t => grouped[t]?.length > 0).map(type => (
                  <div key={type} className="mb-3">
                    <div className="flex items-center gap-1.5 px-1 py-1 mb-1">
                      <span className={`h-2 w-2 rounded-full ${TYPE_CONFIG[type]?.dot ?? 'bg-white/30'}`} />
                      <span className="text-xs font-semibold text-white/30 uppercase tracking-widest">
                        {TYPE_CONFIG[type]?.label ?? type}
                      </span>
                      <span className="text-xs text-white/20 ml-auto">{grouped[type].length}</span>
                    </div>
                    {grouped[type].map(entry => (
                      <PageCard
                        key={entry.path}
                        entry={entry}
                        active={
                          onDetail?.params.type === entry.path.split('/')[0] &&
                          onDetail?.params.slug === entry.path.split('/')[1]
                        }
                      />
                    ))}
                  </div>
                ))
              ) : (
                filtered.map(entry => (
                  <PageCard
                    key={entry.path}
                    entry={entry}
                    active={
                      onDetail?.params.type === entry.path.split('/')[0] &&
                      onDetail?.params.slug === entry.path.split('/')[1]
                    }
                  />
                ))
              )}
            </div>
          </div>

          {/* Right: page detail */}
          <div className="flex-1 overflow-y-auto">
            {onDetail ? (
              <Outlet />
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-white/20 gap-3">
                <BookOpen className="h-10 w-10 opacity-20" />
                <p className="text-sm">Select a page to read</p>
                {pages.length > 0 && (
                  <p className="text-xs text-white/15">
                    {pages.length} pages · click any item on the left
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
