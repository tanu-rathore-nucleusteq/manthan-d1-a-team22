import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { backend } from '../../api/backend'
import type { CreateStaffRequest } from '../../api/types'

const staffKey = ['staff'] as const

export function useStaff() {
  return useQuery({ queryKey: staffKey, queryFn: () => backend.listStaff() })
}

export function useCreateStaff() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateStaffRequest) => backend.createStaff(body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: staffKey }),
  })
}

export function useSetStaffActive() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ staffId, isActive }: { staffId: number; isActive: boolean }) =>
      backend.updateStaff(staffId, { is_active: isActive }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: staffKey }),
  })
}
