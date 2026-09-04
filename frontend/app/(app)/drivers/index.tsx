import React, { useState } from 'react';
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { UserCog } from 'lucide-react-native';
import { useRouter } from 'expo-router';
import { useDrivers } from '@/lib/queries';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { SearchBar } from '@/components/ui/SearchBar';
import { EmptyState } from '@/components/ui/EmptyState';
import { PageHeader } from '@/components/ui/PageHeader';
import { CreateDriverModal } from '@/components/admin/CreateDriverModal';
import { useAuth } from '@/lib/auth-context';
import { canAccess } from '@/lib/rbac';
import { BarCard, Chip, type SevTone } from '@/components/ui/kit';
import type { Role } from '@/lib/types';

const CREATOR_ROLES: Role[] = [
  'super_admin', 'owner', 'general_manager',
  'branch_manager', 'fleet_manager', 'operations_manager',
];

const FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'expiring', label: 'Expiring <30d' },
  { id: 'expired', label: 'Expired' },
];

export default function DriversScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const [q, setQ] = useState('');
  const [filter, setFilter] = useState('all');
  const [createOpen, setCreateOpen] = useState(false);
  const { data, isLoading, isFetching, refetch } = useDrivers({
    page: 1, page_size: 50, ...(q ? { q } : {}),
  });
  const items = data?.items ?? [];
  const canCreate = canAccess(user?.role, CREATOR_ROLES);
  const now = Date.now();

  const filtered = items.filter((d) => {
    if (filter === 'all') return true;
    if (!d.license_expiry) return false;
    const days = Math.ceil((new Date(d.license_expiry).getTime() - now) / 86400000);
    if (filter === 'expired') return days < 0;
    if (filter === 'expiring') return days >= 0 && days <= 30;
    return true;
  });

  return (
    <View style={s.root}>
      <View style={s.headerWrap}>
        <PageHeader
          title="Drivers"
          subtitle={`${data?.total ?? 0} total`}
          primaryActionLabel={canCreate ? 'Add driver' : undefined}
          onPrimaryAction={canCreate ? () => setCreateOpen(true) : undefined}
        />
        <SearchBar value={q} onChange={setQ} placeholder="Search drivers" />
        <View style={s.chipRow}>
          {FILTERS.map((f) => (
            <Chip key={f.id} label={f.label} active={filter === f.id} onPress={() => setFilter(f.id)} />
          ))}
        </View>
      </View>
      {isLoading ? (
        <View style={s.loading}><Spinner label="Loading drivers…" /></View>
      ) : filtered.length === 0 ? (
        <View>
          <EmptyState
            title={q ? 'No drivers found' : 'No drivers yet'}
            description={q ? 'Try a different search.' : 'Add your first driver to start operations.'}
          />
          {canCreate && !q ? (
            <View style={s.ctaWrap}>
              <Pressable onPress={() => setCreateOpen(true)} style={s.cta}>
                <Text style={s.ctaText}>+ Add your first driver</Text>
              </Pressable>
            </View>
          ) : null}
        </View>
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={(d) => d.id}
          contentContainerStyle={{ padding: 16 }}
          ItemSeparatorComponent={() => <View style={{ height: 12 }} />}
          refreshControl={<RefreshControl refreshing={isFetching && !isLoading} onRefresh={refetch} />}
          renderItem={({ item }) => {
            const daysLeft = item.license_expiry
              ? Math.ceil((new Date(item.license_expiry).getTime() - now) / 86400000)
              : null;
            const tone: SevTone =
              daysLeft === null ? 'neutral' : daysLeft < 0 ? 'danger' : daysLeft <= 30 ? 'warn' : 'ok';
            return (
              <Pressable onPress={() => router.push(`/drivers/${item.id}` as never)} accessibilityRole="button">
                <BarCard tone={tone}>
                  <View style={s.row}>
                    <View style={s.iconBox}><UserCog size={18} color="#0E7490" /></View>
                    <View style={s.body}>
                      <Text style={s.name}>{item.full_name ?? 'Unnamed driver'}</Text>
                      <Text style={s.sub}>{item.license_no}</Text>
                      <View style={s.badges}>
                        <Badge
                          label={item.status === 'active' ? 'active' : item.status}
                          tone={item.status === 'active' ? 'success' : 'warning'}
                          size="sm"
                        />
                        <Text style={s.licenseText}>
                          {daysLeft === null
                            ? 'No expiry set'
                            : daysLeft < 0
                            ? `EXPIRED ${Math.abs(daysLeft)}d ago`
                            : daysLeft === 0
                            ? 'Expires today'
                            : `License expires in ${daysLeft}d`}
                        </Text>
                      </View>
                    </View>
                  </View>
                </BarCard>
              </Pressable>
            );
          }}
        />
      )}
      {canCreate ? (
        <CreateDriverModal
          open={createOpen}
          onClose={() => setCreateOpen(false)}
          onSaved={() => { setCreateOpen(false); void refetch(); }}
        />
      ) : null}
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F4F4F2' },
  headerWrap: { paddingHorizontal: 16, paddingTop: 8, paddingBottom: 12, backgroundColor: '#FFFFFF', borderBottomWidth: 1, borderBottomColor: '#E5E5E5' },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', marginTop: 8 },
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
  licenseText: { fontSize: 12, color: '#B45309', fontWeight: '600', marginLeft: 8 },
});
