import React, { useState } from 'react';
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { ArrowRight, Map as MapIcon, Route as RouteIcon } from 'lucide-react-native';
import { useRouter } from 'expo-router';

import { useRoutes } from '@/lib/queries';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { SearchBar } from '@/components/ui/SearchBar';
import { EmptyState } from '@/components/ui/EmptyState';
import { PageHeader } from '@/components/ui/PageHeader';
import { CreateRouteModal } from '@/components/admin/CreateRouteModal';
import { useAuth } from '@/lib/auth-context';
import { canAccess } from '@/lib/rbac';
import type { Route, Role } from '@/lib/types';

const ROUTE_CREATOR_ROLES: Role[] = [
  'super_admin',
  'owner',
  'general_manager',
  'branch_manager',
  'fleet_manager',
  'operations_manager',
];

export default function RoutesScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const [q, setQ] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const { data, isLoading, isFetching, refetch } = useRoutes({
    page: 1,
    page_size: 50,
    ...(q ? { q } : {}),
  });
  const items = data?.items ?? [];
  const canCreate = canAccess(user?.role, ROUTE_CREATOR_ROLES);

  return (
    <View style={s.root}>
      <View style={s.headerWrap}>
        <PageHeader
          title="Routes"
          subtitle={`${data?.total ?? 0} total`}
          primaryActionLabel={canCreate ? 'Add route' : undefined}
          onPrimaryAction={canCreate ? () => setCreateOpen(true) : undefined}
        />
        <SearchBar
          value={q}
          onChange={setQ}
          placeholder="Search by name or cities"
        />
      </View>

      {isLoading ? (
        <View style={s.loading}><Spinner label="Loading routes…" /></View>
      ) : items.length === 0 ? (
        <View>
          <EmptyState
            title={q ? 'No routes found' : 'No routes yet'}
            description={q ? 'Try a different search.' : 'Create a route to start scheduling trips.'}
          />
          {canCreate && !q ? (
            <View style={s.ctaWrap}>
              <Pressable
                onPress={() => setCreateOpen(true)}
                style={s.cta}
                accessibilityRole="button"
                accessibilityLabel="Create first route"
              >
                <Text style={s.ctaText}>+ Create your first route</Text>
              </Pressable>
            </View>
          ) : null}
        </View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(r) => r.id}
          contentContainerStyle={{ padding: 16 }}
          ItemSeparatorComponent={() => <View style={s.separator} />}
          refreshControl={
            <RefreshControl refreshing={isFetching && !isLoading} onRefresh={refetch} />
          }
          renderItem={({ item }) => (
            <RouteRow
              item={item}
              onPress={() => router.push(`/routes/${item.id}` as never)}
            />
          )}
        />
      )}

      {canCreate ? (
        <CreateRouteModal
          open={createOpen}
          onClose={() => setCreateOpen(false)}
          onSaved={() => {
            setCreateOpen(false);
            void refetch();
          }}
        />
      ) : null}
    </View>
  );
}

function RouteRow({ item, onPress }: { item: Route; onPress: () => void }) {
  const hasStops = item.intermediate_stops && item.intermediate_stops.length > 0;
  return (
    <Pressable onPress={onPress} accessibilityRole="button">
      <Card padding="sm">
        <View style={s.row}>
          <View style={s.iconBox}><RouteIcon size={18} color="#047857" /></View>
          <View style={s.body}>
            <Text style={s.name}>{item.name}</Text>
            <View style={s.cityRow}>
              <Text style={s.city}>{item.origin_city}</Text>
              <ArrowRight size={12} color="#A3A3A3" />
              <Text style={s.city}>{item.destination_city}</Text>
            </View>
            <View style={s.badges}>
              <Badge
                label={item.type}
                tone={item.type === 'interstate' ? 'info' : 'neutral'}
                size="sm"
              />
              <View style={s.badgeWrap}>
                <Badge
                  label={item.is_active ? 'active' : 'inactive'}
                  tone={item.is_active ? 'success' : 'neutral'}
                  size="sm"
                />
              </View>
              <Text style={s.meta}>
                {item.distance_km} km · {item.estimated_duration_hours}h
              </Text>
              {hasStops ? (
                <View style={s.badgeWrap}>
                  <Badge
                    label={`${item.intermediate_stops.length} stop${item.intermediate_stops.length === 1 ? '' : 's'}`}
                    tone="primary"
                    size="sm"
                  />
                </View>
              ) : null}
            </View>
          </View>
        </View>
      </Card>
    </Pressable>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F8F7F4' },
  headerWrap: { paddingHorizontal: 16, paddingTop: 8, paddingBottom: 12, backgroundColor: '#FFFFFF', borderBottomWidth: 1, borderBottomColor: '#E5E5E5' },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  ctaWrap: { paddingHorizontal: 16, paddingBottom: 24 },
  cta: { backgroundColor: '#0B3D91', borderRadius: 8, height: 44, flexDirection: 'row', alignItems: 'center', justifyContent: 'center' },
  ctaText: { color: '#FFFFFF', fontWeight: '600' },
  separator: { height: 12 },
  row: { flexDirection: 'row', alignItems: 'center' },
  iconBox: { width: 40, height: 40, borderRadius: 8, backgroundColor: '#ECFDF5', alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  body: { flex: 1 },
  name: { fontSize: 14, fontWeight: '600', color: '#171717' },
  cityRow: { flexDirection: 'row', alignItems: 'center', marginTop: 2 },
  city: { fontSize: 12, color: '#737373' },
  badges: { flexDirection: 'row', alignItems: 'center', marginTop: 6, flexWrap: 'wrap' },
  badgeWrap: { marginLeft: 6 },
  meta: { fontSize: 12, color: '#A3A3A3', marginLeft: 8 },
});
