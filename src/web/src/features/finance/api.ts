import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { backend } from '../../api/backend'
import { staffReturnKey } from '../../api/staffQueries'
import type { ApprovalDecisionRequest } from '../../api/types'

export const financeKeys = {
  pending: ['finance', 'pending'] as const,
  ledger: ['finance', 'ledger'] as const,
}

export function usePendingApprovals() {
  return useQuery({
    queryKey: financeKeys.pending,
    queryFn: () => backend.listPendingApprovals(),
    refetchInterval: 30_000,
  })
}

export function useLedger() {
  return useQuery({ queryKey: financeKeys.ledger, queryFn: () => backend.listLedger() })
}

/** Approve or reject. Never retried automatically: a retry could only be a deliberate second click. */
export function useDecideApproval(code: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: ApprovalDecisionRequest) => backend.decideApproval(code, body),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['finance'] })
      queryClient.invalidateQueries({ queryKey: staffReturnKey(code) })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}
