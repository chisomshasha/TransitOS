import React, { useState } from 'react';
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { Building2, Mail, Phone, MapPin } from 'lucide-react-native';
import { useRouter } from 'expo-router';
import { useBranches } from '@/lib/queries';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { SearchBar } from '@/components/ui/SearchBar';
import { EmptyState } from '@/components/ui/EmptyState';
import { PageHeader } from '@/components/ui/PageHeader';
import { CreateBranchModal } from '@/components/admin/CreateBranchModal';
import { useAuth } from '@/lib/auth-context';
import { canAccess } from '@/lib/rbac';
import type { Role } from '@/lib/types';

const BRANCH_CREATOR_ROLES: Role[] = [
  'super_admin', 'owner', 'general_manager', 'branch_manager',
];

export default function BranchesScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const [q, setQ] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const { data, isLoading, isFetching, refetch } = useBranches({
    page: 1, page_size: 50, ...(q ? { q } : {}),
  });
  const items = data?.items ?? [];
  const canCreate = canAccess(user?.role, BRANCH_CREATOR_ROLES);

  return (
    <View style={s.root}>
      <View style={s.headerWrap}>
        <PageHeader
          title="Branches"
          subtitle={`${data?.total ?? 0} total`}
          primaryActionLabel={canCreate ? 'Add branch' : undefined}
          onPrimaryAction={canCreate ? () => setCreateOpen(true) : undefined}
        />
        <SearchBar value={q} onChange={setQ} placeholder="Search branches" />
      </View>
      {isLoading ? (
        <View style={s.loading}><Spinner label="Loading branches…" /></View>
      ) : items.length === 0 ? (
        <View>
          <EmptyState
            title={q ? 'No branches found' : 'No branches yet'}
            description={q ? 'Try a different search.' : 'Create your first branch to get started.'}
          />
          {canCreate && !q ? (
            <View style={s.ctaWrap}>
              <Pressable onPress={() => setCreateOpen(true)} style={s.cta}>
                <Text style={s.ctaText}>+ Create your first branch</Text>
              </Pressable>
            </View>
          ) : null}
        </View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(b) => b.id}
          contentContainerStyle={{ padding: 16 }}
          ItemSeparatorComponent={() => <View style={{ height: 12 }} />}
          refreshControl={<RefreshControl refreshing={isFetching && !isLoading} onRefresh={refetch} />}
          renderItem={({ item }) => (
            <Pressable onPress={() => router.push(`/branches/${item.id}` as never)} accessibilityRole="button">
              <Card padding="sm">
                <View style={s.row}>
                  <View style={s.iconBox}><Building2 size={18} color="#0E7490" /></View>
                  <View style={s.body}>
                    <Text style={s.name}>{item.name}</Text>
                    <Text style={s.code}>{item.code}</Text>
                    <View style={s.badges}>
                      <Badge label={item.city} tone="neutral" size="sm" />
                      <View style={{ marginLeft: 6 }}>
                        <Badge
                          label={item.is_active ? 'active' : 'inactive'}
                          tone={item.is_active ? 'success' : 'neutral'}
                          size="sm"
                        />
                      </View>
                    </View>
                    {item.address ? (
                      <View style={s.infoRow}>
                        <MapPin size={12} color="#94A3B8" />
                        <Text style={s.infoText} numberOfLines={1}>{item.address}</Text>
                      </View>
                    ) : null}
                    <View style={s.contactRow}>
                      {item.contact_phone ? (
                        <View style={s.contactItem}>
                          <Phone size={12} color="#94A3B8" />
                          <Text style={s.infoText}>{item.contact_phone}</Text>
                        </View>
                      ) : null}
                      {item.contact_email ? (
                        <View style={s.contactItem}>
                          <Mail size={12} color="#94A3B8" />
                          <Text style={s.infoText} numberOfLines={1}>{item.contact_email}</Text>
                        </View>
                      ) : null}
                    </View>
                  </View>
                </View>
              </Card>
            </Pressable>
          )}
        />
      )}
      {canCreate ? (
        <CreateBranchModal
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
  row: { flexDirection: 'row', alignItems: 'flex-start' },
  iconBox: { width: 40, height: 40, borderRadius: 8, backgroundColor: '#ECFEFF', alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  body: { flex: 1 },
  name: { fontSize: 14, fontWeight: '600', color: '#171717' },
  code: { fontSize: 12, color: '#737373', marginTop: 2 },
  badges: { flexDirection: 'row', alignItems: 'center', marginTop: 6 },
  infoRow: { flexDirection: 'row', alignItems: 'center', marginTop: 8 },
  infoText: { fontSize: 12, color: '#64748B', marginLeft: 4, flex: 1 },
  contactRow: { flexDirection: 'row', flexWrap: 'wrap', marginTop: 4 },
  contactItem: { flexDirection: 'row', alignItems: 'center', marginRight: 12, marginTop: 4 },
});
