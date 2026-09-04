import React, { useState } from 'react';
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { Bus } from 'lucide-react-native';
import { useRouter } from 'expo-router';
import { useTrips } from '@/lib/queries';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { SearchBar } from '@/components/ui/SearchBar';
import { EmptyState } from '@/components/ui/EmptyState';
import { PageHeader } from '@/components/ui/PageHeader';
import { CreateTripModal } from '@/components/admin/CreateTripModal';
import { useAuth } from '@/lib/auth-context';
import { canAccess } from '@/lib/rbac';
import { TRIP_STATUS_LABELS, type Role } from '@/lib/types';

const CREATOR_ROLES: Role[] = [
  'super_admin', 'owner', 'general_manager',
  'branch_manager', 'fleet_manager', 'operations_manager',
];

const STATUS_TONE: Record<string, 'neutral' | 'info' | 'primary' | 'success' | 'warning' | 'danger'> = {
  planned: 'neutral', boarding: 'info', departed: 'primary',
  completed: 'success', cancelled: 'danger',
};

export default function TripsScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const [q, setQ] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const { data, isLoading, isFetching, refetch } = useTrips({
    page: 1, page_size: 50, ...(q ? { q } : {}),
  });
  const items = data?.items ?? [];
  const canCreate = canAccess(user?.role, CREATOR_ROLES);

  return (
    <View style={s.root}>
      <View style={s.headerWrap}>
        <PageHeader
          title="Trips"
          subtitle={`${data?.total ?? 0} total`}
          primaryActionLabel={canCreate ? 'New trip' : undefined}
          onPrimaryAction={canCreate ? () => setCreateOpen(true) : undefined}
        />
        <SearchBar value={q} onChange={setQ} placeholder="Search trips" />
      </View>
      {isLoading ? (
        <View style={s.loading}><Spinner label="Loading trips…" /></View>
      ) : items.length === 0 ? (
        <View>
          <EmptyState
            title={q ? 'No trips found' : 'No trips yet'}
            description={q ? 'Try a different search.' : 'Create a trip to start operations.'}
          />
        </View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(t) => t.id}
          contentContainerStyle={{ padding: 16 }}
          ItemSeparatorComponent={() => <View style={{ height: 12 }} />}
          refreshControl={<RefreshControl refreshing={isFetching && !isLoading} onRefresh={refetch} />}
          renderItem={({ item }) => {
            const dep = new Date(item.scheduled_departure);
            return (
              <Pressable onPress={() => router.push(`/trips/${item.id}` as never)} accessibilityRole="button">
                <Card padding="sm">
                  <View style={s.row}>
                    <View style={s.iconBox}><Bus size={18} color="#0E7490" /></View>
                    <View style={s.body}>
                      <Text style={s.name}>
                        {dep.toLocaleDateString()} · {dep.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </Text>
                      <Text style={s.sub}>
                        {item.passenger_count != null ? `${item.passenger_count} pax` : 'No manifest yet'}
                      </Text>
                      <View style={s.badges}>
                        <Badge
                          label={TRIP_STATUS_LABELS[item.status] ?? item.status}
                          tone={STATUS_TONE[item.status] ?? 'neutral'}
                          size="sm"
                        />
                      </View>
                    </View>
                  </View>
                </Card>
              </Pressable>
            );
          }}
        />
      )}
      {canCreate ? (
        <CreateTripModal
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
  row: { flexDirection: 'row', alignItems: 'center' },
  iconBox: { width: 40, height: 40, borderRadius: 8, backgroundColor: '#ECFEFF', alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  body: { flex: 1 },
  name: { fontSize: 14, fontWeight: '600', color: '#171717' },
  sub: { fontSize: 12, color: '#737373', marginTop: 2 },
  badges: { flexDirection: 'row', alignItems: 'center', marginTop: 6 },
});
