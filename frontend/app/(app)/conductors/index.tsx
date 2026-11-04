import React, { useState } from 'react';
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { MapPin } from 'lucide-react-native';
import { useRouter } from 'expo-router';
import { useConductors } from '@/lib/queries';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { SearchBar } from '@/components/ui/SearchBar';
import { EmptyState } from '@/components/ui/EmptyState';
import { PageHeader } from '@/components/ui/PageHeader';
import { CreateConductorModal } from '@/components/admin/CreateConductorModal';
import { useAuth } from '@/lib/auth-context';
import { canAccess } from '@/lib/rbac';
import type { Role } from '@/lib/types';

const CREATOR_ROLES: Role[] = [
  'super_admin', 'owner', 'general_manager',
  'branch_manager', 'fleet_manager', 'operations_manager',
];

export default function ConductorsScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const [q, setQ] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const { data, isLoading, isFetching, refetch } = useConductors({
    page: 1, page_size: 50, ...(q ? { q } : {}),
  });
  const items = data?.items ?? [];
  const canCreate = canAccess(user?.role, CREATOR_ROLES);

  return (
    <View style={s.root}>
      <View style={s.headerWrap}>
        <PageHeader
          title="Conductors"
          subtitle={`${data?.total ?? 0} total`}
          primaryActionLabel={canCreate ? 'Add conductor' : undefined}
          onPrimaryAction={canCreate ? () => setCreateOpen(true) : undefined}
        />
        <SearchBar value={q} onChange={setQ} placeholder="Search conductors" />
      </View>
      {isLoading ? (
        <View style={s.loading}><Spinner label="Loading conductors…" /></View>
      ) : items.length === 0 ? (
        <View>
          <EmptyState
            title={q ? 'No conductors found' : 'No conductors yet'}
            description={q ? 'Try a different search.' : 'Add your first conductor to start operations.'}
          />
          {canCreate && !q ? (
            <View style={s.ctaWrap}>
              <Pressable onPress={() => setCreateOpen(true)} style={s.cta}>
                <Text style={s.ctaText}>+ Add your first conductor</Text>
              </Pressable>
            </View>
          ) : null}
        </View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(c) => c.id}
          contentContainerStyle={{ padding: 16 }}
          ItemSeparatorComponent={() => <View style={{ height: 12 }} />}
          refreshControl={<RefreshControl refreshing={isFetching && !isLoading} onRefresh={refetch} />}
          renderItem={({ item }) => (
            <Pressable onPress={() => router.push(`/conductors/${item.id}` as never)} accessibilityRole="button">
              <Card padding="sm">
                <View style={s.row}>
                  <View style={s.iconBox}><MapPin size={18} color="#0E7490" /></View>
                  <View style={s.body}>
                    <Text style={s.name}>{item.full_name ?? 'Unnamed conductor'}</Text>
                    <Text style={s.sub}>Badge {item.badge_no}</Text>
                    <View style={s.badges}>
                      <Badge
                        label={item.status === 'active' ? 'active' : item.status}
                        tone={item.status === 'active' ? 'success' : 'warning'}
                        size="sm"
                      />
                    </View>
                  </View>
                </View>
              </Card>
            </Pressable>
          )}
        />
      )}
      {canCreate ? (
        <CreateConductorModal
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
});
