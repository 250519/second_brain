import { apiClient } from './client'

export interface QueryRequest {
  question: string
  file_back?: boolean
}

export interface QueryResponse {
  answer: string
}

export const postQuery = (req: QueryRequest): Promise<QueryResponse> =>
  apiClient.post('/api/v1/query', req, { timeout: 120_000 }).then(r => r.data)
