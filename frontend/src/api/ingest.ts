import { apiClient } from './client'

export type JobStatus = 'pending' | 'running' | 'done' | 'failed'

export interface IngestResult {
  source_name: string
  pages_written: string[]
  count: number
}

export interface Job {
  job_id: string
  status: JobStatus
  result?: IngestResult
  error?: string
}

export const ingestUrl = (url: string, source_name?: string): Promise<Job> =>
  apiClient.post('/api/v1/ingest/url', { url, source_name }).then(r => r.data)

export const ingestText = (content: string, source_name: string): Promise<Job> =>
  apiClient.post('/api/v1/ingest/text', { content, source_name }).then(r => r.data)

export const ingestFile = (file: File): Promise<Job> => {
  const form = new FormData()
  form.append('file', file)
  return apiClient.post('/api/v1/ingest/file', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)
}

export const getJob = (job_id: string): Promise<Job> =>
  apiClient.get(`/api/v1/ingest/jobs/${job_id}`).then(r => r.data)

export const listJobs = (): Promise<Job[]> =>
  apiClient.get('/api/v1/ingest/jobs').then(r => r.data)
