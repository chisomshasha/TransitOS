/**
 * Sync API client — pull/push/status.
 *
 * Used by:
 *   - The sync detail screen (manual sync)
 *   - The background pull-on-reconnect hook
 *   - The push-on-reconnect hook that drains the queue
 */
import { api, postSingle } from '@/lib/api';
import { useSyncStore } from '@/stores/syncStore';
import { useQueryClient } from '@tanstack/react-query';

export interface SyncPullPayload {
  data: {
    server_ts: string;
    vehicles: any[];
    drivers: any[];
    trips: any[];
    branches: any[];
  };
}

export interface SyncPushPayload {
  operations: Array<{
    op: 'create' | 'update' | 'delete';
    entity_type: string;
    entity_id?: string;
    body?: Record<string, unknown>;
  }>;
}

export interface SyncPushResponse {
  data: { applied: number; rejected: Array<{ index: number; reason: string }> };
}

/**
 * Pull entities changed since the last sync. Updates query cache
 * so screens show fresh data without a full refetch.
 */
export async function runSyncPull(): Promise<{ pulled: number; serverTs: string }> {
  const store = useSyncStore.getState();
  const lastSyncTs = store.lastSyncAt ?? undefined;

  const resp = await postSingle<SyncPullPayload['data']>('/sync/pull', {
    last_sync_ts: lastSyncTs,
  });

  const qc = (await import('@tanstack/react-query')).useQueryClient
    ? null
    : null; // placeholder; we use the global client below

  // Update the cache in-place for the entities we pulled
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const { queryClient } = await import('@/lib/queryClient');
  if (resp.branches?.length) {
    queryClient.setQueriesData({ queryKey: ['branches'] }, (old: any) => {
      if (!old?.items) return old;
      const map = new Map(old.items.map((b: any) => [b.id, b]));
      resp.branches.forEach((b) => map.set(b.id, b));
      return { ...old, items: Array.from(map.values()) };
    });
  }
  if (resp.vehicles?.length) {
    queryClient.setQueriesData({ queryKey: ['vehicles'] }, (old: any) => {
      if (!old?.items) return old;
      const map = new Map(old.items.map((v: any) => [v.id, v]));
      resp.vehicles.forEach((v) => map.set(v.id, v));
      return { ...old, items: Array.from(map.values()) };
    });
  }
  if (resp.drivers?.length) {
    queryClient.setQueriesData({ queryKey: ['drivers'] }, (old: any) => {
      if (!old?.items) return old;
      const map = new Map(old.items.map((d: any) => [d.id, d]));
      resp.drivers.forEach((d) => map.set(d.id, d));
      return { ...old, items: Array.from(map.values()) };
    });
  }
  if (resp.trips?.length) {
    queryClient.setQueriesData({ queryKey: ['trips'] }, (old: any) => {
      if (!old?.items) return old;
      const map = new Map(old.items.map((t: any) => [t.id, t]));
      resp.trips.forEach((t) => map.set(t.id, t));
      return { ...old, items: Array.from(map.values()) };
    });
  }

  const pulled =
    (resp.vehicles?.length ?? 0) +
    (resp.drivers?.length ?? 0) +
    (resp.trips?.length ?? 0) +
    (resp.branches?.length ?? 0);

  store.setLastSyncAt(resp.server_ts);
  store.setError(null);

  return { pulled, serverTs: resp.server_ts };
}

/**
 * Drain the offline queue by pushing all pending mutations to the server.
 * Removes successfully-applied ops; keeps rejected ones for the user to see.
 */
export async function runSyncPush(): Promise<{ applied: number; rejected: number }> {
  const store = useSyncStore.getState();
  const pending = store.pendingMutations;
  if (pending.length === 0) return { applied: 0, rejected: 0 };

  store.setSyncing(true);
  store.setError(null);

  try {
    const operations = pending.map((op) => ({
      op: op.op,
      entity_type: op.entityType,
      entity_id: op.entityId,
      body: op.body,
    }));

    const resp = await api.post<SyncPushResponse['data']>('/sync/push', {
      operations,
    });

    const { applied, rejected } = resp.data;

    // Remove applied ops from the queue. Rejected ops stay so the
    // user can see + retry them on the Sync screen.
    const rejectedIndices = new Set(rejected.map((r) => r.index));
    pending.forEach((op, i) => {
      if (!rejectedIndices.has(i)) {
        store.dequeue(op.id);
      }
    });

    if (rejected.length > 0) {
      store.setError(
        `${rejected.length} operation${rejected.length === 1 ? '' : 's'} failed: ${rejected[0].reason}`,
      );
    }

    return { applied, rejected: rejected.length };
  } catch (err: any) {
    store.setError(err?.response?.data?.detail ?? err?.message ?? 'Sync failed');
    throw err;
  } finally {
    store.setSyncing(false);
  }
}

/**
 * Probe the server. Returns true if the server is reachable.
 */
export async function probeSync(): Promise<boolean> {
  try {
    await api.get('/sync/status');
    return true;
  } catch {
    return false;
  }
}
