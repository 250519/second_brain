import type { JobStatus } from '../../api/ingest'

interface BadgeProps {
  status: JobStatus
}

const config: Record<JobStatus, { label: string; className: string }> = {
  pending: { label: 'Pending', className: 'bg-yellow-500/15 text-yellow-400 border border-yellow-500/30' },
  running: { label: 'Running', className: 'bg-blue-500/15 text-blue-400 border border-blue-500/30 animate-pulse' },
  done: { label: 'Done', className: 'bg-green-500/15 text-green-400 border border-green-500/30' },
  failed: { label: 'Failed', className: 'bg-red-500/15 text-red-400 border border-red-500/30' },
}

export function Badge({ status }: BadgeProps) {
  const { label, className } = config[status]
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${className}`}>
      {label}
    </span>
  )
}
