import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { backend } from '../../api/backend'
import { staffReturnKey } from '../../api/staffQueries'
import type { InspectionRequest } from '../../api/types'

export const warehouseQueueKey = (status: 'in_transit' | 'received') =>
  ['warehouse', 'queue', status] as const

export function useWarehouseQueue(status: 'in_transit' | 'received') {
  return useQuery({
    queryKey: warehouseQueueKey(status),
    queryFn: () => backend.listWarehouseQueue(status),
    refetchInterval: 30_000,
  })
}

export function useMarkReceived(code: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => backend.markReceived(code),
    onSuccess: (detail) => {
      queryClient.setQueryData(staffReturnKey(code), detail)
      queryClient.invalidateQueries({ queryKey: ['warehouse', 'queue'] })
    },
  })
}

export function useInspectReturn(code: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: InspectionRequest) => backend.inspectReturn(code, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: staffReturnKey(code) })
      queryClient.invalidateQueries({ queryKey: ['warehouse', 'queue'] })
      queryClient.invalidateQueries({ queryKey: ['finance'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}
