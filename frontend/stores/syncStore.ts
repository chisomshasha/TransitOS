/**
 * Offline sync store — Zustand.
 *
 * Tracks:
 *   - online: whether NetInfo thinks we have connectivity
 *   - lastSyncAt: ISO timestamp of the last successful /sync/pull
 *   - pendingMutations: queue of operations captured while offline
 *   - isSyncing: true while a push is in flight
 *   - lastError: most recent sync failure message
 *
 * Components subscribe via useSyncStore(); mutations are captured
 * via the helper in lib/offline.ts.
 */
import { create } from 'zustand';

export type SyncOp = {
  id: string;
  op: 'create' | 'update' | 'delete';
  entityType: string;
  entityId?: string;
  body?: Record<string, unknown>;
  capturedAt: string;
  /** Human-readable label shown in the Sync screen (e.g. "Log fuel for BUS-123") */
  label?: string;
};

export type SyncState = {
  online: boolean;
  lastSyncAt: string | null;
  pendingMutations: SyncOp[];
  isSyncing: boolean;
  lastError: string | null;
};

export type SyncActions = {
  setOnline: (online: boolean) => void;
  setLastSyncAt: (ts: string) => void;
  enqueue: (op: Omit<SyncOp, 'id' | 'capturedAt'>) => string;
  dequeue: (id: string) => void;
  clearQueue: () => void;
  setSyncing: (v: boolean) => void;
  setError: (msg: string | null) => void;
  reset: () => void;
};

const INITIAL: SyncState = {
  online: true,
  lastSyncAt: null,
  pendingMutations: [],
  isSyncing: false,
  lastError: null,
};

export const useSyncStore = create<SyncState & SyncActions>((set) => ({
  ...INITIAL,

  setOnline: (online) => set({ online }),

  setLastSyncAt: (ts) => set({ lastSyncAt: ts }),

  enqueue: (op) => {
    const id = `op_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    set((s) => ({
      pendingMutations: [
        ...s.pendingMutations,
        { ...op, id, capturedAt: new Date().toISOString() },
      ],
    }));
    return id;
  },

  dequeue: (id) =>
    set((s) => ({
      pendingMutations: s.pendingMutations.filter((o) => o.id !== id),
    })),

  clearQueue: () => set({ pendingMutations: [] }),

  setSyncing: (v) => set({ isSyncing: v }),

  setError: (msg) => set({ lastError: msg }),

  reset: () => set(INITIAL),
}));
