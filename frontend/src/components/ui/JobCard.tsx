import { FileText } from 'lucide-react'
import { Badge } from './Badge'
import { useJobPoller } from '../../hooks/useJobPoller'

interface JobCardProps {
  jobId: string
  initialSourceName?: string
}

export function JobCard({ jobId, initialSourceName }: JobCardProps) {
  const { data: job } = useJobPoller(jobId)
  if (!job) return null

  const sourceName = job.result?.source_name ?? initialSourceName ?? job.job_id.slice(0, 8)

  return (
    <div className="flex items-start gap-3 px-4 py-3 rounded-lg bg-surface-800 border border-gray-800">
      <FileText className="h-4 w-4 text-gray-500 mt-0.5 shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm text-gray-200 truncate font-medium">{sourceName}</span>
          <Badge status={job.status} />
        </div>
        {job.status === 'done' && job.result && (
          <p className="text-xs text-gray-500 mt-1">
            {job.result.count} pages written
          </p>
        )}
        {job.status === 'failed' && job.error && (
          <p className="text-xs text-red-400 mt-1 truncate">{job.error}</p>
        )}
      </div>
    </div>
  )
}
