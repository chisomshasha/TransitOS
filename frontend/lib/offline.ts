/**
 * Offline-aware mutation wrapper.
 *
 * Usage:
 *   const createFuel = useCreateFuelLog();
 *   const wrapped = offlineAware(createFuel.mutateAsync, {
 *     entityType: 'fuel_log',
 *     label: 'Log fuel stop',
 *   });
 *   await wrapped(body);  // queues if offline, fires if online
 *
 * When online, the call goes straight through to the underlying mutation.
 * When offline (or when the call fails with a network error), the
 * operation is appended to syncStore.pendingMutations for later push.
 */
import NetInfo from '@react-native-community/netinfo';
import { useSyncStore, type SyncOp } from '@/stores/syncStore';

export interface OfflineAwareOptions {
  entityType: SyncOp['entityType'];
  op?: SyncOp['op'];
  label?: string;
  /** If true, always enqueue (skip the online check). Used for demo. */
  forceEnqueue?: boolean;
}

/**
 * Wrap a react-query mutation function so it falls back to the offline
 * queue when the network is unavailable.
 */
export function offlineAware<TData, TBody>(
  mutator: (body: TBody) => Promise<TData>,
  opts: OfflineAwareOptions,
): (body: TBody) => Promise<TData | { __queued: true; id: string }> {
  const op = opts.op ?? 'create';
  return async (body) => {
    const state = useSyncStore.getState();

    if (opts.forceEnqueue || !state.online) {
      const id = state.enqueue({
        op,
        entityType: opts.entityType,
        body: body as Record<string, unknown>,
        label: opts.label,
      });
      return { __queued: true, id } as any;
    }

    try {
      return await mutator(body);
    } catch (err: any) {
      // Network-level failures → queue. Server-side 4xx/5xx propagate.
      const msg: string = err?.message ?? '';
      const isNetwork =
        !err?.response &&
        (msg.includes('Network') ||
          msg.includes('timeout') ||
          msg.includes('ECONNABORTED') ||
          msg.includes('offline'));
      if (isNetwork) {
        const id = state.enqueue({
          op,
          entityType: opts.entityType,
          body: body as Record<string, unknown>,
          label: opts.label,
        });
        return { __queued: true, id } as any;
      }
      throw err;
    }
  };
}

/**
 * Initialise the online/offline listener. Call once at app boot
 * (from _layout.tsx). Also performs an initial connectivity check.
 */
export function initNetworkListener(): () => void {
  const update = (isOnline: boolean | null) => {
    useSyncStore.getState().setOnline(isOnline !== false);
  };

  // Initial probe
  NetInfo.fetch().then((state) => update(state.isConnected));

  // Subscription
  const unsub = NetInfo.addEventListener((state) => update(state.isConnected));
  return () => unsub();
}
