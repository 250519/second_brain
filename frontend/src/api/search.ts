import { apiClient } from './client'

export interface WebSearchResult {
  title: string
  url: string
  snippet: string
}

export interface WebSearchResponse {
  results: WebSearchResult[]
  error?: string
}

export const searchWeb = (q: string): Promise<WebSearchResponse> =>
  apiClient.get('/api/v1/search', { params: { q } }).then(r => r.data)
