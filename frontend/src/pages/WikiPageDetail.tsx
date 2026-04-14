import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { parseFrontmatter } from '../lib/parseFrontmatter'
import { ChevronRight, Copy, Check } from 'lucide-react'
import { useState } from 'react'
import { getWikiPage } from '../api/wiki'
import { MarkdownRenderer } from '../components/ui/MarkdownRenderer'
import { Spinner } from '../components/ui/Spinner'

const TYPE_BADGE: Record<string, string> = {
  summary: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  concept: 'bg-violet-500/15 text-violet-400 border-violet-500/30',
  connection: 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30',
  insight: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  qa: 'bg-green-500/15 text-green-400 border-green-500/30',
  lint: 'bg-white/5 text-white/40 border-white/10',
}

export function WikiPageDetail() {
  const { type = '', slug = '' } = useParams<{ type: string; slug: string }>()
  const [copied, setCopied] = useState(false)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['wiki-page', type, slug],
    queryFn: () => getWikiPage(type, slug),
    enabled: !!type && !!slug,
  })

  function copy() {
    navigator.clipboard.writeText(window.location.href)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (isLoading) return (
    <div className="flex justify-center pt-16"><Spinner label="Loading page..." /></div>
  )

  if (isError || !data) return (
    <div className="p-6 text-center text-white/30">
      <p className="text-sm">Page not found.</p>
      <Link to="/wiki" className="text-xs text-violet-400 hover:underline mt-2 block">← Back to wiki</Link>
    </div>
  )

  const { data: frontmatter, content: rawBody } = parseFrontmatter(data.content)
  const title = frontmatter.title ?? slug.replace(/-/g, ' ')
  const summary = frontmatter.summary as string | undefined

  // Strip the leading H1 if it duplicates the title shown in the header
  // rawBody may start with \n before the # so trim first
  const body = rawBody.trimStart().replace(/^#\s+[^\n]+\n?/, '').trimStart()

  return (
    <div className="p-6 max-w-3xl mx-auto">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1 text-xs text-white/30 mb-4">
        <Link to="/wiki" className="hover:text-white/60">Wiki</Link>
        <ChevronRight className="h-3 w-3" />
        <Link to="/wiki" className="hover:text-white/60 capitalize">{type}</Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-white/50">{slug}</span>
      </nav>

      {/* Page header */}
      <div className="mb-6">
        <div className="flex items-start justify-between gap-3">
          <h1 className="font-display text-3xl text-[#ede9e3] capitalize">{title}</h1>
          <button onClick={copy} aria-label={copied ? 'Link copied' : 'Copy link to page'} className="flex items-center gap-1.5 text-xs text-white/30 hover:text-white/60 shrink-0 mt-1">
            {copied ? <Check className="h-3.5 w-3.5 text-green-400" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? 'Copied' : 'Copy link'}
          </button>
        </div>
        <div className="flex items-center gap-2 mt-2">
          <span className={`text-xs px-2 py-0.5 rounded border capitalize ${TYPE_BADGE[type] ?? 'bg-white/5 text-white/40 border-white/10'}`}>
            {type}
          </span>
          {summary && <span className="text-xs text-white/30">{summary}</span>}
        </div>
      </div>

      {/* Body */}
      <MarkdownRenderer content={body} />
    </div>
  )
}
