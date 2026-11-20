import { useQuery } from '@tanstack/react-query'

import { backend } from './backend'

/** Shared by the warehouse and finance screens. */
export const staffReturnKey = (code: string) => ['staff', 'return', code.toUpperCase()] as const

export function useStaffReturn(code: string) {
  return useQuery({
    queryKey: staffReturnKey(code),
    queryFn: () => backend.getReturnForStaff(code),
    retry: false,
  })
}
