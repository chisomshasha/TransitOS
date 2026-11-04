/**
 * Sprint D — operations hooks.
 *
 * Three small areas the backend had fully built but the app never
 * surfaced:
 *
 *   - **Push devices** — `GET /push` lists the signed-in user's
 *     registered devices, `POST /push/unregister` deactivates one.
 *   - **Audit actors** — `GET /audit-log/actors` returns the distinct
 *     actor emails, for the audit-log filter dropdown.
 *   - **Branch manager** — `POST /branches/{id}/manager` assigns (or
 *     clears) the manager of a branch.
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from '@tanstack/react-query';
import { getPage, getSingle, postNoContent, postSingle } from '@/lib/api';

// ─── Push devices ───────────────────────────────────────────────────────────
export interface PushTokenItem {
  id: string;
  user_id: string;
  token: string;
  platform: 'ios' | 'android' | 'web';
  device_id?: string | null;
  app_version?: string | null;
  is_active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export function usePushTokens(): UseQueryResult<PushTokenItem[]> {
  return useQuery({
    queryKey: ['push', 'tokens'],
    queryFn: async () => {
      // GET /push answers with the standard list envelope.
      const page = await getPage<PushTokenItem>('/push');
      return page.items ?? [];
    },
    staleTime: 30_000,
  });
}

export function useUnregisterPushToken(): UseMutationResult<
  void,
  unknown,
  { token: string; platform: PushTokenItem['platform'] }
> {
  const qc = useQueryClient();
  return useMutation({
    // The backend needs the *same* token and platform it stored.
    mutationFn: ({ token, platform }) =>
      postNoContent('/push/unregister', { token, platform }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['push'] }),
  });
}

// ─── Audit actors ───────────────────────────────────────────────────────────
export function useAuditActors(): UseQueryResult<string[]> {
  return useQuery({
    queryKey: ['audit-log', 'actors'],
    // The endpoint defaults to 25 actors, which silently truncates the
    // filter list once an organisation has more than that. Ask for the
    // maximum it allows.
    queryFn: () => getSingle<string[]>('/audit-log/actors', { limit: 100 }),
    staleTime: 60_000,
  });
}

// ─── Branch manager ─────────────────────────────────────────────────────────
export function useSetBranchManager(
  branchId: string
): UseMutationResult<unknown, unknown, string | null> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (managerId: string | null) =>
      postSingle(`/branches/${branchId}/manager`, { manager_id: managerId }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['branches'] });
      qc.invalidateQueries({ queryKey: ['users'] });
    },
  });
}
