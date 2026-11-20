import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000, refetchOnWindowFocus: false },
    // Never auto-retry writes: a refund must be retried only with the same idempotency key.
    mutations: { retry: 0 },
  },
})
