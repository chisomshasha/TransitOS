/**
 * TanStack Query client — see api-contract.md §0.6 + sprint-a-tasks.md §6.
 *
 * Conventions:
 *   - staleTime: 30s for list queries (keeps the offline experience graceful)
 *   - refetchOnWindowFocus: true (default — helps in low-connectivity areas)
 *   - retry: 1 (a 5xx will still show the error state fast)
 */

import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      retry: 1,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
    },
    mutations: {
      retry: 0,
    },
  },
});
