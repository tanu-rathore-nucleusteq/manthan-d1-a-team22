import { useQuery } from '@tanstack/react-query'

import { backend } from '../../api/backend'

export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: () => backend.getDashboard(),
    refetchInterval: 60_000,
  })
}
