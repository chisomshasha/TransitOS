import React, { useState } from 'react';
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { User } from 'lucide-react-native';
import { useRouter } from 'expo-router';
import { useBranches, useUsers } from '@/lib/queries';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { SearchBar } from '@/components/ui/SearchBar';
import { EmptyState } from '@/components/ui/EmptyState';
import { PageHeader } from '@/components/ui/PageHeader';
import { CreateUserModal } from '@/components/admin/CreateUserModal';
import { useAuth } from '@/lib/auth-context';
import { canAccess } from '@/lib/rbac';
import { ROLE_LABELS, type Role } from '@/lib/types';

const USER_CREATOR_ROLES: Role[] = [
  'super_admin', 'owner', 'general_manager', 'branch_manager',
];

const ROLE_TONE: Record<string, 'primary' | 'info' | 'warning' | 'neutral' | 'success'> = {
  super_admin: 'danger' as any,
  owner: 'danger' as any,
  general_manager: 'warning',
  branch_manager: 'info',
  fleet_manager: 'primary',
  operations_manager: 'primary',
  driver: 'success',
  conductor: 'success',
  crew: 'neutral',
  accountant: 'info',
  auditor: 'neutral',
};

export default function UsersScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const [q, setQ] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const { data, isLoading, isFetching, refetch } = useUsers({
    page: 1, page_size: 50, ...(q ? { q } : {}),
  });
  const branchesQ = useBranches({ page: 1, page_size: 200 });
  const items = data?.items ?? [];
  const canCreate = canAccess(user?.role, USER_CREATOR_ROLES);

  return (
    <View style={s.root}>
      <View style={s.headerWrap}>
        <PageHeader
          title="Users"
          subtitle={`${data?.total ?? 0} total`}
          primaryActionLabel={canCreate ? 'Invite user' : undefined}
          onPrimaryAction={canCreate ? () => setCreateOpen(true) : undefined}
        />
        <SearchBar value={q} onChange={setQ} placeholder="Search users" />
      </View>
      {isLoading ? (
        <View style={s.loading}><Spinner label="Loading users…" /></View>
      ) : items.length === 0 ? (
        <View>
          <EmptyState
            title={q ? 'No users found' : 'No users yet'}
            description={q ? 'Try a different search.' : 'Invite your first user.'}
          />
          {canCreate && !q ? (
            <View style={s.ctaWrap}>
              <Pressable onPress={() => setCreateOpen(true)} style={s.cta}>
                <Text style={s.ctaText}>+ Invite your first user</Text>
              </Pressable>
            </View>
          ) : null}
        </View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(u) => u.id}
          contentContainerStyle={{ padding: 16 }}
          ItemSeparatorComponent={() => <View style={{ height: 12 }} />}
          refreshControl={<RefreshControl refreshing={isFetching && !isLoading} onRefresh={refetch} />}
          renderItem={({ item }) => {
            const branchName = branchesQ.data?.items.find((b) => b.id === item.branch_id)?.name ?? '—';
            return (
              <Pressable onPress={() => router.push(`/users/${item.id}` as never)} accessibilityRole="button">
                <Card padding="sm">
                  <View style={s.row}>
                    <View style={s.iconBox}><User size={18} color="#0E7490" /></View>
                    <View style={s.body}>
                      <Text style={s.name}>{item.full_name}</Text>
                      <Text style={s.email}>{item.email}</Text>
                      <View style={s.badges}>
                        <Badge
                          label={ROLE_LABELS[item.role] ?? item.role}
                          tone={(ROLE_TONE[item.role] ?? 'neutral') as any}
                          size="sm"
                        />
                        <View style={{ marginLeft: 6 }}>
                          <Badge label={branchName} tone="neutral" size="sm" />
                        </View>
                        <View style={{ marginLeft: 6 }}>
                          <Badge
                            label={item.is_active ? 'active' : 'inactive'}
                            tone={item.is_active ? 'success' : 'neutral'}
                            size="sm"
                          />
                        </View>
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
        <CreateUserModal
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
  iconBox: { width: 40, height: 40, borderRadius: 20, backgroundColor: '#ECFEFF', alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  body: { flex: 1 },
  name: { fontSize: 14, fontWeight: '600', color: '#171717' },
  email: { fontSize: 12, color: '#737373', marginTop: 2 },
  badges: { flexDirection: 'row', alignItems: 'center', marginTop: 6, flexWrap: 'wrap' },
});
