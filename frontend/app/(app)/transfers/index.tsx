import React, { useState } from 'react';
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { Stack, useRouter } from 'expo-router';
import { ArrowRightLeft, Bus, Plus } from 'lucide-react-native';
import { useVehicleTransfers } from '@/lib/queries-p5';
import { useBranches, useVehicles } from '@/lib/queries';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { EmptyState } from '@/components/ui/EmptyState';
import { Chip, type SevTone } from '@/components/ui/kit';
import { formatDateTime } from '@/lib/format';
import { CreateTransferModal } from '@/components/admin/CreateTransferModal';
import { brand } from '@/lib/theme';
import { canAccess } from '@/lib/rbac';
import { useAuth } from '@/lib/auth-context';

const STATUS_TONE: Record<string, SevTone> = {
  initiated: 'warn',
  confirmed: 'info',
  returned: 'ok',
  cancelled: 'neutral',
};

const FILTERS: Array<{ id: string; label: string }> = [
  { id: 'all', label: 'All' },
  { id: 'initiated', label: 'Initiated' },
  { id: 'confirmed', label: 'In transit' },
  { id: 'returned', label: 'Returned' },
  { id: 'cancelled', label: 'Cancelled' },
];

const CREATOR_ROLES = [
  'super_admin',
  'owner',
  'general_manager',
  'operations_manager',
  'branch_manager',
  'fleet_manager',
];

export default function TransfersScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const [filter, setFilter] = useState('all');
  const [createOpen, setCreateOpen] = useState(false);

  const { data, isLoading, isFetching, refetch } = useVehicleTransfers(
    filter === 'all' ? {} : { status: filter },
  );
  const branchesQ = useBranches({ page: 1, page_size: 200 });
  const vehiclesQ = useVehicles({ page: 1, page_size: 200 });
  const items = data?.items ?? [];

  const canCreate = canAccess(user?.role, CREATOR_ROLES);
  const branchName = (id: string) => branchesQ.data?.items.find((b) => b.id === id)?.name ?? '—';
  const vehicleReg = (id: string) => vehiclesQ.data?.items.find((v) => v.id === id)?.reg_number ?? '—';

  return (
    <>
      <Stack.Screen
        options={{
          title: 'Vehicle transfers',
          headerRight: canCreate
            ? () => (
                <Pressable onPress={() => setCreateOpen(true)} style={s.headerBtn}>
                  <Plus size={18} color="#FFFFFF" />
                </Pressable>
              )
            : undefined,
        }}
      />
      <View style={s.root}>
        <View style={s.chipRow}>
          {FILTERS.map((f) => (
            <Chip key={f.id} label={f.label} active={filter === f.id} onPress={() => setFilter(f.id)} />
          ))}
        </View>

        {isLoading ? (
          <View style={s.loading}><Spinner label="Loading transfers…" /></View>
        ) : items.length === 0 ? (
          <EmptyState
            title="No transfers"
            description={filter === 'all' ? 'Initiate a cross-branch transfer using the + button.' : `No ${filter} transfers.`}
          />
        ) : (
          <FlatList
            data={items}
            keyExtractor={(t) => t.id}
            contentContainerStyle={{ padding: 16 }}
            ItemSeparatorComponent={() => <View style={{ height: 12 }} />}
            refreshControl={<RefreshControl refreshing={isFetching && !isLoading} onRefresh={refetch} />}
            renderItem={({ item }) => (
              <Pressable style={s.card} onPress={() => router.push(`/transfers/${item.id}` as never)}>
                <View style={s.cardHeader}>
                  <View style={s.iconBox}>
                    <ArrowRightLeft size={18} color={brand.navy} />
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={s.reg}>{vehicleReg(item.vehicle_id)}</Text>
                    <View style={s.routeRow}>
                      <Text style={s.branchName} numberOfLines={1}>{branchName(item.from_branch_id)}</Text>
                      <Text style={s.arrow}>→</Text>
                      <Text style={s.branchName} numberOfLines={1}>{branchName(item.to_branch_id)}</Text>
                    </View>
                  </View>
                  <Badge
                    label={item.status.replace('_', ' ')}
                    tone={
                      item.status === 'returned'
                        ? 'success'
                        : item.status === 'confirmed'
                        ? 'info'
                        : item.status === 'initiated'
                        ? 'warning'
                        : 'neutral'
                    }
                    size="sm"
                  />
                </View>
                {item.reason ? <Text style={s.reason}>{item.reason}</Text> : null}
                <Text style={s.meta}>
                  {item.status === 'initiated'
                    ? `Initiated ${formatDateTime(item.initiated_at)}`
                    : item.status === 'confirmed'
                    ? `Confirmed ${formatDateTime(item.confirmed_at)}`
                    : item.status === 'returned'
                    ? `Returned ${formatDateTime(item.returned_at)}`
                    : `Cancelled ${formatDateTime(item.cancelled_at)}`}
                </Text>
              </Pressable>
            )}
          />
        )}
      </View>
      {canCreate ? (
        <CreateTransferModal
          open={createOpen}
          onClose={() => setCreateOpen(false)}
          onSaved={() => {
            setCreateOpen(false);
            refetch();
          }}
        />
      ) : null}
    </>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F4F4F2' },
  headerBtn: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.15)',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 4,
  },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', padding: 16, paddingBottom: 4 },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  card: {
    backgroundColor: '#F8FAFC',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    padding: 14,
  },
  cardHeader: { flexDirection: 'row', alignItems: 'center' },
  iconBox: {
    width: 42,
    height: 42,
    borderRadius: 12,
    backgroundColor: '#DBEAFE',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  reg: { fontSize: 16, fontWeight: '800', color: '#0F172A' },
  routeRow: { flexDirection: 'row', alignItems: 'center', marginTop: 4 },
  branchName: { fontSize: 13, fontWeight: '600', color: '#475569', flex: 1 },
  arrow: { fontSize: 13, color: '#94A3B8', marginHorizontal: 8 },
  reason: { fontSize: 13, color: '#475569', marginTop: 8, fontStyle: 'italic' },
  meta: { fontSize: 11, color: '#94A3B8', marginTop: 8 },
});
