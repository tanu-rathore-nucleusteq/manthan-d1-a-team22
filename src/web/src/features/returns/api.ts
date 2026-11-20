import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { backend } from '../../api/backend'
import type { CreateReturnRequest, OrderLookupRequest } from '../../api/types'

export const returnKeys = {
  order: (orderNumber: string, email: string) =>
    ['order', orderNumber.toUpperCase(), email] as const,
  detail: (code: string) => ['return', code.toUpperCase()] as const,
  label: (code: string) => ['return', code.toUpperCase(), 'label'] as const,
}

export function useOrderLookup() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: OrderLookupRequest) => backend.lookupOrder(body),
    onSuccess: (order, body) =>
      queryClient.setQueryData(returnKeys.order(body.order_number, body.email), order),
  })
}

export function useOrder(orderNumber: string, email: string | null) {
  return useQuery({
    queryKey: returnKeys.order(orderNumber, email ?? ''),
    queryFn: () => backend.lookupOrder({ order_number: orderNumber, email: email! }),
    enabled: Boolean(email),
  })
}

export function useCreateReturn() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ body, photo }: { body: CreateReturnRequest; photo: File }) => {
      const created = await backend.createReturn(body)
      await backend.uploadReturnPhoto(created.return_code, body.email, photo)
      return created
    },
    onSuccess: (created) => {
      queryClient.setQueryData(returnKeys.detail(created.return_code), created)
      queryClient.invalidateQueries({ queryKey: ['order'] })
    },
  })
}

export function useReturnDetail(code: string, email: string | null) {
  return useQuery({
    queryKey: returnKeys.detail(code),
    queryFn: () => backend.getReturn(code, { email: email! }),
    enabled: Boolean(email),
  })
}

export function useReturnLabel(code: string, email: string | null) {
  return useQuery({
    queryKey: returnKeys.label(code),
    queryFn: () => backend.getLabel(code, { email: email! }),
    enabled: Boolean(email),
    staleTime: Infinity,
  })
}

export function useMarkShipped(code: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (email: string) => backend.markShipped(code, { email }),
    onSuccess: (detail) => queryClient.setQueryData(returnKeys.detail(code), detail),
  })
}
