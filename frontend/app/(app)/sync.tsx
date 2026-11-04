import React, { useEffect, useState } from 'react';
import { Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Stack } from 'expo-router';
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  CloudOff,
  RefreshCw,
  Trash2,
  Wifi,
  WifiOff,
} from 'lucide-react-native';
import { useSyncStore } from '@/stores/syncStore';
import { runSyncPull, runSyncPush, probeSync } from '@/lib/sync';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { useToast } from '@/components/ui/Toast';
import { formatDateTime } from '@/lib/format';
import { brand } from '@/lib/theme';

export default function SyncScreen() {
  const toast = useToast();
  const online = useSyncStore((s) => s.online);
  const lastSyncAt = useSyncStore((s) => s.lastSyncAt);
  const pending = useSyncStore((s) => s.pendingMutations);
  const isSyncing = useSyncStore((s) => s.isSyncing);
  const lastError = useSyncStore((s) => s.lastError);
  const clearQueue = useSyncStore((s) => s.clearQueue);
  const dequeue = useSyncStore((s) => s.dequeue);

  const [pulling, setPulling] = useState(false);
  const [probing, setProbing] = useState(false);
  const [serverReachable, setServerReachable] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    probeSync().then((ok) => {
      if (!cancelled) setServerReachable(ok);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const onPull = async () => {
    if (!online) return toast.error('You are offline');
    setPulling(true);
    try {
      const { pulled } = await runSyncPull();
      toast.success(`Pulled ${pulled} updated record${pulled === 1 ? '' : 's'}`);
      setServerReachable(true);
    } catch (e: any) {
      toast.error(e?.message ?? 'Pull failed');
      setServerReachable(false);
    } finally {
      setPulling(false);
    }
  };

  const onPush = async () => {
    if (!online) return toast.error('You are offline — queue will send when back online');
    if (pending.length === 0) return toast.info('Nothing to sync');
    try {
      const { applied, rejected } = await runSyncPush();
      if (rejected === 0) {
        toast.success(`Synced ${applied} operation${applied === 1 ? '' : 's'}`);
      } else {
        toast.error(`Applied ${applied}, ${rejected} failed (see below)`);
      }
    } catch (e: any) {
      toast.error(e?.message ?? 'Sync failed');
    }
  };

  const onProbe = async () => {
    setProbing(true);
    const ok = await probeSync();
    setServerReachable(ok);
    toast.info(ok ? 'Server is reachable' : 'Server not reachable');
    setProbing(false);
  };

  const onClear = () => {
    if (pending.length === 0) return;
    clearQueue();
    toast.info(`Cleared ${pending.length} pending operation${pending.length === 1 ? '' : 's'}`);
  };

  return (
    <>
      <Stack.Screen options={{ title: 'Sync' }} />
      <ScrollView
        style={s.root}
        contentContainerStyle={{ padding: 16, paddingBottom: 60 }}
        refreshControl={<RefreshControl refreshing={isSyncing} onRefresh={onPull} />}
      >
        {/* Status card */}
        <View style={s.statusCard}>
          <View style={s.statusRow}>
            <View style={[s.statusDot, { backgroundColor: online ? '#047857' : '#B91C1C' }]} />
            <Text style={s.statusTitle}>{online ? 'Online' : 'Offline'}</Text>
            {online ? (
              <Wifi size={16} color="#047857" style={{ marginLeft: 8 }} />
            ) : (
              <WifiOff size={16} color="#B91C1C" style={{ marginLeft: 8 }} />
            )}
          </View>
          <View style={s.metaRow}>
            <Clock size={12} color={brand.muted} />
            <Text style={s.metaText}>
              Last sync: {lastSyncAt ? formatDateTime(lastSyncAt) : 'Never'}
            </Text>
          </View>
          {serverReachable !== null ? (
            <View style={s.metaRow}>
              {serverReachable ? (
                <CheckCircle2 size={12} color="#047857" />
              ) : (
                <AlertTriangle size={12} color="#B91C1C" />
              )}
              <Text
                style={[
                  s.metaText,
                  { color: serverReachable ? '#047857' : '#B91C1C' },
                ]}
              >
                Server {serverReachable ? 'reachable' : 'not reachable'}
              </Text>
            </View>
          ) : null}
          {lastError ? (
            <View style={[s.metaRow, { marginTop: 6 }]}>
              <AlertTriangle size={12} color="#B45309" />
              <Text style={[s.metaText, { color: '#B45309', flex: 1 }]}>{lastError}</Text>
            </View>
          ) : null}
        </View>

        {/* Actions */}
        <View style={s.actionsRow}>
          <Pressable style={[s.actionBtn, { flex: 1 }]} onPress={onPull}>
            <RefreshCw size={16} color={brand.navy} />
            <Text style={s.actionBtnText}>{pulling ? 'Pulling…' : 'Pull changes'}</Text>
          </Pressable>
          <Pressable style={[s.actionBtn, { flex: 1 }]} onPress={onProbe}>
            <CloudOff size={16} color={brand.navy} />
            <Text style={s.actionBtnText}>{probing ? 'Probing…' : 'Test server'}</Text>
          </Pressable>
        </View>

        {/* Queue */}
        <View style={s.sectionHead}>
          <Text style={s.sectionTitle}>
            Pending operations ({pending.length})
          </Text>
          {pending.length > 0 ? (
            <Pressable onPress={onClear} style={s.clearBtn}>
              <Trash2 size={12} color="#B91C1C" />
              <Text style={s.clearBtnText}>Clear all</Text>
            </Pressable>
          ) : null}
        </View>

        {pending.length === 0 ? (
          <View style={s.emptyCard}>
            <CheckCircle2 size={28} color="#047857" />
            <Text style={s.emptyTitle}>Queue is empty</Text>
            <Text style={s.emptyBody}>
              Any changes you make while offline will appear here.
            </Text>
          </View>
        ) : (
          <>
            {pending.map((op) => (
              <View key={op.id} style={s.queueRow}>
                <View style={{ flex: 1 }}>
                  <Text style={s.queueLabel}>
                    {op.label ?? `${op.op} ${op.entityType}`}
                  </Text>
                  <Text style={s.queueMeta}>
                    {op.op.toUpperCase()} · {formatDateTime(op.capturedAt)}
                  </Text>
                </View>
                <Pressable onPress={() => dequeue(op.id)} hitSlop={8}>
                  <Trash2 size={14} color="#B91C1C" />
                </Pressable>
              </View>
            ))}
            <View style={{ height: 10 }} />
            <Button
              label={`Sync ${pending.length} pending now`}
              onPress={onPush}
              loading={isSyncing}
              fullWidth
            />
          </>
        )}
      </ScrollView>
    </>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: brand.bg },
  statusCard: {
    backgroundColor: '#fff',
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: brand.border,
    marginBottom: 16,
  },
  statusRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 10 },
  statusDot: { width: 10, height: 10, borderRadius: 5, marginRight: 8 },
  statusTitle: { fontSize: 17, fontWeight: '700', color: brand.slate, flex: 1 },
  metaRow: { flexDirection: 'row', alignItems: 'center', marginTop: 4 },
  metaText: { fontSize: 12, color: brand.muted, marginLeft: 6 },
  actionsRow: { flexDirection: 'row', gap: 10, marginBottom: 18 },
  actionBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#fff',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: brand.navy,
    paddingVertical: 12,
    gap: 6,
  },
  actionBtnText: { color: brand.navy, fontWeight: '700', fontSize: 13 },
  sectionHead: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: brand.slate },
  clearBtn: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  clearBtnText: { fontSize: 12, fontWeight: '600', color: '#B91C1C' },
  emptyCard: {
    backgroundColor: '#fff',
    borderRadius: 14,
    padding: 24,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: brand.border,
  },
  emptyTitle: { fontSize: 15, fontWeight: '700', color: brand.slate, marginTop: 10 },
  emptyBody: { fontSize: 13, color: brand.muted, marginTop: 4, textAlign: 'center' },
  queueRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: brand.border,
    padding: 12,
    marginBottom: 8,
  },
  queueLabel: { fontSize: 14, fontWeight: '600', color: brand.slate },
  queueMeta: { fontSize: 11, color: brand.muted, marginTop: 2, textTransform: 'capitalize' },
});
