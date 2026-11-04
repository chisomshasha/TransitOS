import React, { useMemo, useState } from 'react';
import {
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Stack } from 'expo-router';
import { Bell, BellOff, CheckCheck } from 'lucide-react-native';
import { Chip, type SevTone } from '@/components/ui/kit';
import { Badge, type BadgeTone } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { EmptyState } from '@/components/ui/EmptyState';
import {
  useMarkAllRead,
  useMarkRead,
  useNotifications,
  useUnreadCount,
  type NotificationItem,
} from '@/lib/queries-p1';
import { useAuth } from '@/lib/auth-context';
import { brand } from '@/lib/theme';

type FilterId = 'all' | 'unread' | 'maintenance' | 'documents' | 'licenses' | 'trips';

const FILTERS: { id: FilterId; label: string; tone: SevTone }[] = [
  { id: 'all', label: 'All', tone: 'neutral' },
  { id: 'unread', label: 'Unread', tone: 'info' },
  { id: 'maintenance', label: 'Maintenance', tone: 'info' },
  { id: 'documents', label: 'Documents', tone: 'danger' },
  { id: 'licenses', label: 'Licenses', tone: 'warn' },
  { id: 'trips', label: 'Trips', tone: 'neutral' },
];

/**
 * Maps a notification `type` onto the filter chips.
 * The backend alert engine emits these types (see app/services/alerts.py).
 */
function matchesFilter(n: NotificationItem, filter: FilterId): boolean {
  const type = (n.type ?? '').toLowerCase();
  switch (filter) {
    case 'all':
      return true;
    case 'unread':
      return true; // handled server-side via the `unread` query param
    case 'maintenance':
      return type.includes('maintenance');
    case 'documents':
      return type.includes('document');
    case 'licenses':
      return type.includes('license');
    case 'trips':
      return type.includes('trip');
    default:
      return true;
  }
}

function severityTone(severity: NotificationItem['severity']): BadgeTone {
  switch (severity) {
    case 'danger':
      return 'danger';
    case 'warn':
      return 'warning';
    case 'success':
      return 'success';
    case 'info':
      return 'info';
    default:
      return 'neutral';
  }
}

export default function NotificationsScreen() {
  const { user } = useAuth();
  const [filter, setFilter] = useState<FilterId>('all');

  // The `unread` filter is applied server-side; the type filters are
  // applied client-side because the API only supports one `type` value.
  const notificationsQ = useNotifications(
    filter === 'unread' ? { page: 1, page_size: 100, unread: true } : { page: 1, page_size: 100 },
  );
  const unreadQ = useUnreadCount();
  const markAllMut = useMarkAllRead();
  const markReadMut = useMarkRead();

  const items = useMemo(() => {
    const all = notificationsQ.data?.items ?? [];
    if (filter === 'all' || filter === 'unread') return all;
    return all.filter((n) => matchesFilter(n, filter));
  }, [notificationsQ.data?.items, filter]);

  const unreadCount = unreadQ.data ?? 0;
  const isRead = (n: NotificationItem) =>
    Array.isArray(n.read_by) && n.read_by.length > 0;

  const onOpen = (n: NotificationItem) => {
    if (!isRead(n)) markReadMut.mutate(n.id);
  };

  return (
    <>
      <Stack.Screen
        options={{
          title: 'Notifications',
          headerRight: () => (
            <Pressable
              onPress={() => {
                if (unreadCount > 0) markAllMut.mutate();
              }}
              disabled={unreadCount === 0 || markAllMut.isPending}
              accessibilityRole="button"
              accessibilityLabel="Mark all read"
            >
              <Text style={[s.markAll, unreadCount === 0 && s.markAllDisabled]}>
                {unreadCount > 0 ? 'Mark all read' : 'All read'}
              </Text>
            </Pressable>
          ),
        }}
      />
      <ScrollView
        style={s.root}
        contentContainerStyle={{ padding: 16 }}
        refreshControl={
          <RefreshControl
            refreshing={notificationsQ.isRefetching}
            onRefresh={() => {
              void notificationsQ.refetch();
              void unreadQ.refetch();
            }}
            tintColor={brand.navy}
          />
        }
      >
        <View style={s.chipRow}>
          {FILTERS.map((f) => (
            <Chip
              key={f.id}
              label={f.label}
              tone={f.tone}
              active={filter === f.id}
              onPress={() => setFilter(f.id)}
            />
          ))}
        </View>

        {unreadCount > 0 ? (
          <View style={s.unreadBanner}>
            <Bell size={15} color={brand.navy} />
            <Text style={s.unreadText}>
              {unreadCount} unread notification{unreadCount === 1 ? '' : 's'}
            </Text>
          </View>
        ) : null}

        {notificationsQ.isLoading ? (
          <View style={s.loadingBox}>
            <Spinner label="Loading notifications…" />
          </View>
        ) : items.length === 0 ? (
          <EmptyState
            icon={<BellOff size={28} color="#94A3B8" />}
            title={filter === 'all' ? 'No notifications yet' : 'Nothing here'}
            description={
              filter === 'all'
                ? 'Alerts about expiring documents, licences, maintenance and low fuel will appear here. Pull down to refresh.'
                : 'No notifications match this filter.'
            }
          />
        ) : (
          items.map((n) => {
            const read = isRead(n);
            return (
              <Pressable
                key={n.id}
                onPress={() => onOpen(n)}
                style={({ pressed }) => [s.card, !read && s.cardUnread, pressed && s.cardPressed]}
                accessibilityRole="button"
                accessibilityLabel={n.title}
              >
                <View style={s.cardTop}>
                  <Text style={[s.cardTitle, !read && s.cardTitleUnread]} numberOfLines={2}>
                    {n.title}
                  </Text>
                  <Badge label={(n.severity ?? 'info').toUpperCase()} tone={severityTone(n.severity)} size="sm" />
                </View>
                <Text style={s.cardBody}>{n.body}</Text>
                <View style={s.cardFoot}>
                  <Text style={s.cardMeta}>
                    {n.type}
                    {n.created_at ? ` · ${formatWhen(n.created_at)}` : ''}
                  </Text>
                  {read ? (
                    <CheckCheck size={14} color="#94A3B8" />
                  ) : (
                    <View style={s.unreadDot} />
                  )}
                </View>
              </Pressable>
            );
          })
        )}
      </ScrollView>
    </>
  );
}

function formatWhen(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const diffMs = Date.now() - d.getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return d.toLocaleDateString();
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F4F4F2' },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: 12 },
  markAll: { color: '#BFDBFE', fontSize: 13, fontWeight: '700', marginRight: 8 },
  markAllDisabled: { color: '#64748B', opacity: 0.6 },
  unreadBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#DBEAFE',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 9,
    marginBottom: 12,
  },
  unreadText: { fontSize: 13, fontWeight: '600', color: brand.navy, marginLeft: 8 },
  loadingBox: { paddingVertical: 40, alignItems: 'center' },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    padding: 14,
    marginBottom: 10,
  },
  cardUnread: { borderColor: '#93C5FD', backgroundColor: '#F8FBFF' },
  cardPressed: { opacity: 0.85 },
  cardTop: { flexDirection: 'row', alignItems: 'flex-start', marginBottom: 6 },
  cardTitle: { flex: 1, fontSize: 15, fontWeight: '600', color: '#0F172A', marginRight: 8 },
  cardTitleUnread: { fontWeight: '800' },
  cardBody: { fontSize: 13, color: '#475569', lineHeight: 19 },
  cardFoot: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 10,
  },
  cardMeta: { fontSize: 11, color: '#94A3B8', textTransform: 'capitalize' },
  unreadDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#2563EB' },
});
