import { useState, useRef, type FormEvent, type DragEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link2, Type, Upload, CloudUpload } from 'lucide-react'
import { ingestUrl, ingestText, ingestFile, listJobs, type Job } from '../api/ingest'
import { JobCard } from '../components/ui/JobCard'
import { Spinner } from '../components/ui/Spinner'
import { useToast } from '../components/ui/Toast'

type Tab = 'url' | 'text' | 'file'

export function IngestPage() {
  const [tab, setTab] = useState<Tab>('url')
  const [activeJobIds, setActiveJobIds] = useState<string[]>([])
  const [dragOver, setDragOver] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)
  const { toast } = useToast()
  const queryClient = useQueryClient()

  const { data: allJobs = [] } = useQuery({
    queryKey: ['jobs'],
    queryFn: listJobs,
    refetchInterval: 5_000,
  })

  const addJob = (job: Job) => {
    setActiveJobIds(prev => [job.job_id, ...prev.filter(id => id !== job.job_id)])
    queryClient.invalidateQueries({ queryKey: ['jobs'] })
  }

  const urlMutation = useMutation({
    mutationFn: ({ url, name }: { url: string; name?: string }) => ingestUrl(url, name),
    onSuccess: (job, { url: ingestedUrl }) => { addJob(job); toast(`Ingesting "${ingestedUrl}"`, 'success') },
    onError: () => toast('Failed to start ingest', 'error'),
  })

  const textMutation = useMutation({
    mutationFn: ({ content, name }: { content: string; name: string }) => ingestText(content, name),
    onSuccess: job => { addJob(job); toast('Text ingestion started', 'success') },
    onError: () => toast('Failed to start ingest', 'error'),
  })

  const fileMutation = useMutation({
    mutationFn: (file: File) => ingestFile(file),
    onSuccess: job => { addJob(job); toast(`Ingesting "${job.result?.source_name ?? 'file'}"`, 'success') },
    onError: () => toast('Failed to upload file', 'error'),
  })

  function handleUrl(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = new FormData(e.currentTarget)
    urlMutation.mutate({
      url: form.get('url') as string,
      name: (form.get('name') as string) || undefined,
    })
    e.currentTarget.reset()
  }

  function handleText(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = new FormData(e.currentTarget)
    textMutation.mutate({
      content: form.get('content') as string,
      name: form.get('name') as string,
    })
    e.currentTarget.reset()
  }

  function handleFile(file: File) {
    fileMutation.mutate(file)
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  const allJobIds = Array.from(new Set([
    ...activeJobIds,
    ...allJobs.map(j => j.job_id),
  ]))

  const tabClass = (t: Tab) =>
    `flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
      tab === t
        ? 'border-violet-500 text-violet-300'
        : 'border-transparent text-slate-500 hover:text-slate-300'
    }`

  return (
    <div className="p-8 max-w-2xl mx-auto space-y-8">
      <div>
        <h1 className="font-display text-4xl text-[#ede9e3]">Ingest</h1>
        <p className="text-sm text-white/35 mt-2">Add a source to your wiki</p>
      </div>

      {/* Tabs */}
      <div className="border-b border-indigo-900/40 flex">
        <button className={tabClass('url')} onClick={() => setTab('url')}>
          <Link2 className="h-4 w-4" /> URL
        </button>
        <button className={tabClass('text')} onClick={() => setTab('text')}>
          <Type className="h-4 w-4" /> Text
        </button>
        <button className={tabClass('file')} onClick={() => setTab('file')}>
          <Upload className="h-4 w-4" /> File
        </button>
      </div>

      {/* URL form */}
      {tab === 'url' && (
        <form onSubmit={handleUrl} className="space-y-3">
          <div>
            <label htmlFor="url-input" className="block text-xs font-medium text-slate-400 mb-1.5">URL *</label>
            <input
              id="url-input"
              name="url"
              type="url"
              required
              placeholder="https://example.com/article"
              className="w-full bg-surface-800 border border-white/5 rounded-lg px-3.5 py-2.5 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-violet-500 transition-colors"
            />
          </div>
          <div>
            <label htmlFor="url-name-input" className="block text-xs font-medium text-slate-400 mb-1.5">Source name (optional)</label>
            <input
              id="url-name-input"
              name="name"
              type="text"
              placeholder="e.g. Anthropic Blog Post"
              className="w-full bg-surface-800 border border-white/5 rounded-lg px-3.5 py-2.5 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-violet-500 transition-colors"
            />
          </div>
          <button
            type="submit"
            disabled={urlMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white text-sm rounded-md transition-colors"
          >
            {urlMutation.isPending ? <Spinner size="sm" /> : <Upload className="h-4 w-4" />}
            Ingest URL
          </button>
        </form>
      )}

      {/* Text form */}
      {tab === 'text' && (
        <form onSubmit={handleText} className="space-y-3">
          <div>
            <label htmlFor="text-name-input" className="block text-xs font-medium text-slate-400 mb-1.5">Source name *</label>
            <input
              id="text-name-input"
              name="name"
              required
              placeholder="my-notes"
              className="w-full bg-surface-800 border border-white/5 rounded-lg px-3.5 py-2.5 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-violet-500 transition-colors"
            />
          </div>
          <div>
            <label htmlFor="text-content-input" className="block text-xs font-medium text-slate-400 mb-1.5">Content *</label>
            <textarea
              id="text-content-input"
              name="content"
              required
              rows={8}
              placeholder="Paste your text here..."
              className="w-full bg-surface-800 border border-white/5 rounded-lg px-3.5 py-2.5 text-sm text-white/80 placeholder-white/20 focus:outline-none focus:border-violet-500 transition-colors resize-y font-mono"
            />
          </div>
          <button
            type="submit"
            disabled={textMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white text-sm rounded-md transition-colors"
          >
            {textMutation.isPending ? <Spinner size="sm" /> : <Upload className="h-4 w-4" />}
            Ingest Text
          </button>
        </form>
      )}

      {/* File form */}
      {tab === 'file' && (
        <div className="space-y-3">
          <div
            onDragOver={e => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            onClick={() => fileRef.current?.click()}
            className={`border-2 border-dashed rounded-lg p-10 text-center cursor-pointer transition-colors ${
              dragOver ? 'border-violet-500 bg-violet-500/5' : 'border-white/10 hover:border-white/20'
            }`}
          >
            <CloudUpload className="h-8 w-8 mx-auto mb-3 text-white/30" />
            <p className="text-sm text-white/60">Drop a file here or click to browse</p>
            <p className="text-xs text-white/25 mt-1">.txt, .md, .pdf</p>
            <input
              ref={fileRef}
              type="file"
              accept=".txt,.md,.pdf"
              className="hidden"
              onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f) }}
            />
          </div>
          {fileMutation.isPending && <Spinner label="Uploading..." />}
        </div>
      )}

      {/* Job list */}
      {allJobIds.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-white/30 uppercase tracking-widest mb-3">Jobs</p>
          <div className="space-y-2">
            {allJobIds.map(id => <JobCard key={id} jobId={id} />)}
          </div>
        </div>
      )}
    </div>
  )
}
