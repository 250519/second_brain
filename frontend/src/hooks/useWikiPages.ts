import { useQuery } from '@tanstack/react-query'
import { getWikiPages } from '../api/wiki'

export function useWikiPages() {
  return useQuery<string[]>({
    queryKey: ['wiki-pages'],
    queryFn: getWikiPages,
    staleTime: 60_000,
    placeholderData: [],
  })
}
