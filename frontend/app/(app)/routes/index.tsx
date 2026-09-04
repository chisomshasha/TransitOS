import React, { useState } from 'react';
import { FlatList, Pressable, RefreshControl, Text, View } from 'react-native';
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
    <View className="flex-1 bg-[#F8F7F4]">
      <View className="px-4 pt-2 pb-3 bg-white border-b border-neutral-200">
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
        <View className="flex-1 items-center justify-center">
          <Spinner label="Loading routes…" />
        </View>
      ) : items.length === 0 ? (
        <View>
          <EmptyState
            title={q ? 'No routes found' : 'No routes yet'}
            description={q ? 'Try a different search.' : 'Create a route to start scheduling trips.'}
          />
          {canCreate && !q ? (
            <View className="px-4 pb-6">
              <Pressable
                onPress={() => setCreateOpen(true)}
                className="bg-[#0B3D91] rounded-lg h-11 flex-row items-center justify-center"
                accessibilityRole="button"
                accessibilityLabel="Create first route"
              >
                <Text className="text-white font-semibold">+ Create your first route</Text>
              </Pressable>
            </View>
          ) : null}
        </View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(r) => r.id}
          contentContainerStyle={{ padding: 16 }}
          ItemSeparatorComponent={() => <View className="h-3" />}
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
      <Card className="p-3">
        <View className="flex-row items-center">
          <View className="w-10 h-10 rounded-lg bg-success-50 items-center justify-center mr-3">
            <RouteIcon size={18} color="#047857" />
          </View>
          <View className="flex-1">
            <Text className="text-sm font-semibold text-neutral-900">{item.name}</Text>
            <View className="flex-row items-center mt-0.5">
              <Text className="text-xs text-neutral-700">{item.origin_city}</Text>
              <ArrowRight size={12} color="#94A3B8" />
              <Text className="text-xs text-neutral-700">{item.destination_city}</Text>
            </View>
            <View className="flex-row items-center mt-1.5 flex-wrap">
              <Badge
                label={item.type}
                tone={item.type === 'interstate' ? 'info' : 'neutral'}
                size="sm"
              />
              <View className="ml-1.5">
                <Badge
                  label={item.is_active ? 'active' : 'inactive'}
                  tone={item.is_active ? 'success' : 'neutral'}
                  size="sm"
                />
              </View>
              <Text className="text-xs text-neutral-400 ml-2">
                {item.distance_km} km · {item.estimated_duration_hours}h
              </Text>
              {hasStops ? (
                <View className="ml-1.5">
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
