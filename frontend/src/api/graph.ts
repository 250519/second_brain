import { apiClient } from './client'

export interface GraphNode {
  id: string
  centrality: number
  degree: number
  in_degree: number
  out_degree: number
}

export interface GraphEdge {
  source: string
  target: string
  relation: string
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

export interface GraphAnalysisResponse {
  report: string
}

export const getGraphData = (): Promise<GraphData> =>
  apiClient.get('/api/v1/graph/data').then(r => r.data)

export const postGraphAnalyze = (): Promise<GraphAnalysisResponse> =>
  apiClient.post('/api/v1/graph/analyze', {}, { timeout: 120_000 }).then(r => r.data)
