/**
 * Singleton QueryClient used by the sync helpers in lib/sync.ts.
 *
 * The app's root provider (app/_layout.tsx) also uses this instance
 * so sync-driven cache updates are immediately visible.
 */
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
});
