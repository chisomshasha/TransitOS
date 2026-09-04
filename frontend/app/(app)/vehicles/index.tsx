import React, { useState } from 'react';
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { Bus, Users } from 'lucide-react-native';
import { useRouter } from 'expo-router';
import { useVehicles } from '@/lib/queries';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { SearchBar } from '@/components/ui/SearchBar';
import { EmptyState } from '@/components/ui/EmptyState';
import { PageHeader } from '@/components/ui/PageHeader';
import { CreateVehicleModal } from '@/components/admin/CreateVehicleModal';
import { useAuth } from '@/lib/auth-context';
import { canAccess } from '@/lib/rbac';
import { VEHICLE_STATUS_LABELS, type Role } from '@/lib/types';

const CREATOR_ROLES: Role[] = [
  'super_admin', 'owner', 'general_manager',
  'branch_manager', 'fleet_manager', 'operations_manager',
];

const STATUS_TONE: Record<string, 'success' | 'info' | 'warning' | 'neutral'> = {
  available: 'success', on_trip: 'info', maintenance: 'warning', inactive: 'neutral',
};

export default function VehiclesScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const [q, setQ] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const { data, isLoading, isFetching, refetch } = useVehicles({
    page: 1, page_size: 50, ...(q ? { q } : {}),
  });
  const items = data?.items ?? [];
  const canCreate = canAccess(user?.role, CREATOR_ROLES);

  return (
    <View style={s.root}>
      <View style={s.headerWrap}>
        <PageHeader
          title="Vehicles"
          subtitle={`${data?.total ?? 0} total`}
          primaryActionLabel={canCreate ? 'Add vehicle' : undefined}
          onPrimaryAction={canCreate ? () => setCreateOpen(true) : undefined}
        />
        <SearchBar value={q} onChange={setQ} placeholder="Search by plate or model" />
      </View>
      {isLoading ? (
        <View style={s.loading}><Spinner label="Loading vehicles…" /></View>
      ) : items.length === 0 ? (
        <View>
          <EmptyState
            title={q ? 'No vehicles found' : 'No vehicles yet'}
            description={q ? 'Try a different search.' : 'Add your first vehicle to start operations.'}
          />
          {canCreate && !q ? (
            <View style={s.ctaWrap}>
              <Pressable onPress={() => setCreateOpen(true)} style={s.cta}>
                <Text style={s.ctaText}>+ Add your first vehicle</Text>
              </Pressable>
            </View>
          ) : null}
        </View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(v) => v.id}
          contentContainerStyle={{ padding: 16 }}
          ItemSeparatorComponent={() => <View style={{ height: 12 }} />}
          refreshControl={<RefreshControl refreshing={isFetching && !isLoading} onRefresh={refetch} />}
          renderItem={({ item }) => (
            <Pressable onPress={() => router.push(`/vehicles/${item.id}` as never)} accessibilityRole="button">
              <Card padding="sm">
                <View style={s.row}>
                  <View style={s.iconBox}><Bus size={18} color="#0E7490" /></View>
                  <View style={s.body}>
                    <Text style={s.name}>{item.plate_number}</Text>
                    <Text style={s.sub}>{item.model}</Text>
                    <View style={s.badges}>
                      <Badge
                        label={VEHICLE_STATUS_LABELS[item.status] ?? item.status}
                        tone={STATUS_TONE[item.status] ?? 'neutral'}
                        size="sm"
                      />
                      <View style={s.metaWrap}>
                        <Users size={12} color="#A3A3A3" />
                        <Text style={s.meta}>{item.capacity_seats} seats</Text>
                      </View>
                    </View>
                  </View>
                </View>
              </Card>
            </Pressable>
          )}
        />
      )}
      {canCreate ? (
        <CreateVehicleModal
          open={createOpen}
          onClose={() => setCreateOpen(false)}
          onSaved={() => { setCreateOpen(false); void refetch(); }}
        />
      ) : null}
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F8F7F4' },
  headerWrap: { paddingHorizontal: 16, paddingTop: 8, paddingBottom: 12, backgroundColor: '#FFFFFF', borderBottomWidth: 1, borderBottomColor: '#E5E5E5' },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  ctaWrap: { paddingHorizontal: 16, paddingBottom: 24 },
  cta: { backgroundColor: '#0B3D91', borderRadius: 8, height: 44, flexDirection: 'row', alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: '#FFFFFF', fontWeight: '600' },
  row: { flexDirection: 'row', alignItems: 'center' },
  iconBox: { width: 40, height: 40, borderRadius: 8, backgroundColor: '#ECFEFF', alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  body: { flex: 1 },
  name: { fontSize: 14, fontWeight: '600', color: '#171717' },
  sub: { fontSize: 12, color: '#737373', marginTop: 2 },
  badges: { flexDirection: 'row', alignItems: 'center', marginTop: 6, flexWrap: 'wrap' },
  metaWrap: { flexDirection: 'row', alignItems: 'center', marginLeft: 8 },
  meta: { fontSize: 12, color: '#A3A3A3', marginLeft: 4 },
});
