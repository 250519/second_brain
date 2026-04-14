import { apiClient } from './client'

export interface WikiStatus {
  total_pages: number
  by_type: Record<string, number>
  raw_sources: number
  ideas_count: number
}

export interface WikiPage {
  path: string
  content: string
}

export interface WikiIndexResponse {
  index: string
}

export interface IdeasResponse {
  ideas: string[]
}

export interface LintResponse {
  report: string
}

export const getWikiStatus = (): Promise<WikiStatus> =>
  apiClient.get('/api/v1/wiki/status').then(r => r.data)

export const getWikiPages = (): Promise<string[]> =>
  apiClient.get('/api/v1/wiki/pages').then(r => r.data)

export const getWikiPage = (type: string, slug: string): Promise<WikiPage> =>
  apiClient.get(`/api/v1/wiki/pages/${type}/${slug}`).then(r => r.data)

export const getWikiIndex = (): Promise<WikiIndexResponse> =>
  apiClient.get('/api/v1/wiki/index').then(r => r.data)

export const getIdeas = (): Promise<IdeasResponse> =>
  apiClient.get('/api/v1/wiki/ideas').then(r => r.data)

export const postLint = (): Promise<LintResponse> =>
  apiClient.post('/api/v1/wiki/lint', {}, { timeout: 120_000 }).then(r => r.data)
