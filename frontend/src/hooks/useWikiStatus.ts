import { useQuery } from '@tanstack/react-query'
import { getWikiStatus, type WikiStatus } from '../api/wiki'

export function useWikiStatus() {
  return useQuery<WikiStatus>({
    queryKey: ['wiki-status'],
    queryFn: getWikiStatus,
    refetchInterval: 30_000,
    staleTime: 10_000,
  })
}
