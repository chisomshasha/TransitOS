/**
 * SyncStatusIndicator — a small chip shown in the app header that
 * reports online/offline state and the size of the offline queue.
 *
 * Tapping it opens the /sync detail screen.
 */
import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useRouter } from 'expo-router';
import { Cloud, CloudOff, RefreshCw, Wifi, WifiOff } from 'lucide-react-native';
import { useSyncStore } from '@/stores/syncStore';
import { brand } from '@/lib/theme';

export function SyncStatusIndicator() {
  const router = useRouter();
  const online = useSyncStore((s) => s.online);
  const pending = useSyncStore((s) => s.pendingMutations.length);
  const isSyncing = useSyncStore((s) => s.isSyncing);
  const lastError = useSyncStore((s) => s.lastError);

  const state: 'online' | 'offline' | 'syncing' | 'error' =
    isSyncing ? 'syncing' : lastError ? 'error' : online ? 'online' : 'offline';

  const colorMap = {
    online: { bg: '#ECFDF5', text: '#047857', border: '#A7F3D0' },
    offline: { bg: '#FEF2F2', text: '#B91C1C', border: '#FECACA' },
    syncing: { bg: '#EFF6FF', text: '#1D4ED8', border: '#BFDBFE' },
    error: { bg: '#FFFBEB', text: '#B45309', border: '#FDE68A' },
  }[state];

  const Icon = state === 'offline' ? WifiOff : state === 'syncing' ? RefreshCw : Wifi;

  return (
    <Pressable
      onPress={() => router.push('/sync' as never)}
      style={[s.chip, { backgroundColor: colorMap.bg, borderColor: colorMap.border }]}
      accessibilityRole="button"
      accessibilityLabel={`Network ${state}${pending ? `, ${pending} pending` : ''}`}
    >
      <Icon size={12} color={colorMap.text} />
      <Text style={[s.label, { color: colorMap.text }]}>
        {state === 'syncing'
          ? 'Syncing…'
          : state === 'offline'
          ? 'Offline'
          : state === 'error'
          ? 'Sync error'
          : 'Online'}
      </Text>
      {pending > 0 ? (
        <View style={[s.badge, { backgroundColor: colorMap.text }]}>
          <Text style={s.badgeText}>{pending}</Text>
        </View>
      ) : null}
    </Pressable>
  );
}

const s = StyleSheet.create({
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 999,
    borderWidth: 1,
    marginRight: 6,
  },
  label: { fontSize: 11, fontWeight: '700', marginLeft: 5 },
  badge: {
    minWidth: 16,
    height: 16,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: 5,
    paddingHorizontal: 4,
  },
  badgeText: { color: '#fff', fontSize: 10, fontWeight: '800' },
});
