import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Stack, useRouter } from 'expo-router';
import { Bus, Radio, WifiOff } from 'lucide-react-native';
import { useTrips } from '@/lib/queries';
import { useTripEvents, useTripPolling, type LiveConnection } from '@/lib/live';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { EmptyState } from '@/components/ui/EmptyState';
import { TRIP_STATUS_LABELS } from '@/lib/types';

const STATUS_TONE: Record<string, 'neutral' | 'info' | 'primary' | 'success' | 'warning' | 'danger'> = {
  planned: 'neutral',
  boarding: 'info',
  departed: 'primary',
  arrived: 'info',
  closed: 'warning',
  cashed_up: 'success',
  cancelled: 'danger',
};

const CONNECTION_LABEL: Record<LiveConnection, string> = {
  connecting: 'Connecting…',
  live: 'Live',
  polling: 'Polling',
  offline: 'Offline',
};

export default function LiveTripsScreen() {
  const router = useRouter();
  const tripsQ = useTrips({ page: 1, page_size: 100 });
  const [pulse, setPulse] = useState<Record<string, number>>({});

  // A trip that just changed gets a brief highlight so the eye catches
  // it without the list jumping around.
  //
  // Events arrive in bursts (a trip moving from boarding to departed
  // fires two), so the refetch is debounced — otherwise a busy branch
  // would trigger a request per event.
  const refetchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const scheduleRefetch = useCallback(() => {
    if (refetchTimer.current) clearTimeout(refetchTimer.current);
    refetchTimer.current = setTimeout(() => {
      refetchTimer.current = null;
      void tripsQ.refetch();
    }, 400);
  }, [tripsQ]);

  useEffect(
    () => () => {
      if (refetchTimer.current) clearTimeout(refetchTimer.current);
    },
    []
  );

  const onEvent = useCallback(
    (event: { type: string; data: { trip_id?: string; status?: string } }) => {
      if (!event.data?.trip_id) return;
      setPulse((prev) => ({ ...prev, [event.data.trip_id as string]: Date.now() }));
      scheduleRefetch();
    },
    [scheduleRefetch]
  );

  const { connection } = useTripEvents(onEvent);
  useTripPolling(() => void tripsQ.refetch(), 15_000, connection !== 'live');

  const items = useMemo(() => {
    const list = tripsQ.data?.items ?? [];
    // Active trips first — that is what a dispatcher cares about.
    const rank = (status: string) =>
      status === 'departed' ? 0 :
      status === 'boarding' ? 1 :
      status === 'arrived' ? 2 :
      status === 'closed' ? 3 :
      status === 'cashed_up' ? 4 :
      status === 'planned' ? 5 : 6;
    return [...list].sort((a, b) => rank(a.status) - rank(b.status));
  }, [tripsQ.data?.items]);

  const isLive = connection === 'live';

  return (
    <>
      <Stack.Screen
        options={{
          title: 'Live trips',
          headerRight: () => (
            <View style={s.connBadge}>
              <Radio size={13} color={isLive ? '#047857' : '#94A3B8'} />
              <Text style={[s.connText, isLive && { color: '#047857' }]}>
                {CONNECTION_LABEL[connection]}
              </Text>
            </View>
          ),
        }}
      />
      <View style={s.root}>
        {!isLive ? (
          <View style={s.notice}>
            <WifiOff size={14} color="#B45309" />
            <Text style={s.noticeText}>
              {connection === 'connecting'
                ? 'Connecting to the live feed…'
                : 'Live updates unavailable — showing periodic refresh instead.'}
            </Text>
          </View>
        ) : null}

        {tripsQ.isLoading ? (
          <View style={s.loading}><Spinner label="Loading trips…" /></View>
        ) : items.length === 0 ? (
          <EmptyState
            icon={<Bus size={28} color="#94A3B8" />}
            title="No trips yet"
            description="Scheduled trips appear here as soon as they are created."
          />
        ) : (
          <FlatList
            data={items}
            keyExtractor={(t) => t.id}
            contentContainerStyle={{ padding: 16 }}
            ItemSeparatorComponent={() => <View style={{ height: 10 }} />}
            refreshControl={
              <RefreshControl
                refreshing={tripsQ.isRefetching}
                onRefresh={() => tripsQ.refetch()}
              />
            }
            renderItem={({ item }) => {
              const changedAt = pulse[item.id] ?? 0;
              const fresh = Date.now() - changedAt < 4000;
              return (
                <Pressable
                  onPress={() => router.push(`/trips/${item.id}` as never)}
                  accessibilityRole="button"
                >
                  <Card padding="sm" variant={fresh ? 'elevated' : 'default'}>
                    <View style={s.row}>
                      <View style={s.body}>
                        <Text style={s.name}>
                          Trip {item.id.slice(0, 8).toUpperCase()}
                        </Text>
                        <Text style={s.sub}>
                          {new Date(item.scheduled_departure).toLocaleString()}
                        </Text>
                        {item.route_id ? (
                          <Text style={s.sub} numberOfLines={1}>
                            Route {item.route_id.slice(0, 8)}
                          </Text>
                        ) : null}
                      </View>
                      <Badge
                        label={TRIP_STATUS_LABELS[item.status] ?? item.status}
                        tone={STATUS_TONE[item.status] ?? 'neutral'}
                      />
                    </View>
                  </Card>
                </Pressable>
              );
            }}
          />
        )}
      </View>
    </>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F4F4F2' },
  loading: { paddingVertical: 40, alignItems: 'center' },
  notice: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#FEF3C7',
    paddingHorizontal: 16,
    paddingVertical: 9,
  },
  noticeText: { flex: 1, fontSize: 12, color: '#B45309', fontWeight: '500' },
  connBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, marginRight: 8 },
  connText: { fontSize: 12, fontWeight: '700', color: '#94A3B8' },
  row: { flexDirection: 'row', alignItems: 'center' },
  body: { flex: 1 },
  name: { fontSize: 14, fontWeight: '700', color: '#171717' },
  sub: { fontSize: 12, color: '#737373', marginTop: 2 },
});
