import React, { useMemo, useState } from 'react';
import {
  FlatList,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Stack } from 'expo-router';
import {
  Activity,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  FileText,
  Filter,
  KeyRound,
  LogIn,
  LogOut,
  Pencil,
  Plus,
  RefreshCw,
  ShieldAlert,
  Trash2,
  UserCog,
  UserPlus,
  UserX,
} from 'lucide-react-native';
import { useAuditLog, useAuditLogSummary, type AuditLogEntry } from '@/lib/queries-p3';
import { Chip, BarCard, type SevTone } from '@/components/ui/kit';
import { SearchBar } from '@/components/ui/SearchBar';
import { Spinner } from '@/components/ui/Spinner';
import { Badge } from '@/components/ui/Badge';
import { formatDateTime } from '@/lib/format';
import { brand } from '@/lib/theme';

const ACTION_META: Record<
  string,
  { label: string; tone: SevTone; Icon: React.ComponentType<{ size?: number; color?: string }> }
> = {
  create: { label: 'Created', tone: 'ok', Icon: Plus },
  update: { label: 'Updated', tone: 'info', Icon: Pencil },
  delete: { label: 'Deleted', tone: 'danger', Icon: Trash2 },
  activate: { label: 'Activated', tone: 'ok', Icon: RefreshCw },
  deactivate: { label: 'Deactivated', tone: 'warn', Icon: UserX },
  login: { label: 'Logged in', tone: 'ok', Icon: LogIn },
  login_failed: { label: 'Login failed', tone: 'danger', Icon: ShieldAlert },
  logout: { label: 'Logged out', tone: 'neutral', Icon: LogOut },
  password_reset: { label: 'Password reset', tone: 'warn', Icon: KeyRound },
  role_change: { label: 'Role changed', tone: 'warn', Icon: UserCog },
  change_password: { label: 'Password changed', tone: 'warn', Icon: KeyRound },
};

const ACTION_FILTERS: Array<{ id: string; label: string }> = [
  { id: 'all', label: 'All' },
  { id: 'login', label: 'Login' },
  { id: 'login_failed', label: 'Login failed' },
  { id: 'logout', label: 'Logout' },
  { id: 'create', label: 'Create' },
  { id: 'update', label: 'Update' },
  { id: 'delete', label: 'Delete' },
  { id: 'role_change', label: 'Role change' },
  { id: 'password_reset', label: 'Password reset' },
];

export default function AuditLogScreen() {
  const [action, setAction] = useState('all');
  const [actorEmail, setActorEmail] = useState('');
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [page, setPage] = useState(1);

  const params = useMemo(
    () => ({
      page,
      page_size: 50,
      ...(action !== 'all' ? { action } : {}),
      ...(actorEmail.trim() ? { actor_email: actorEmail.trim() } : {}),
    }),
    [page, action, actorEmail],
  );

  const { data, isLoading, isFetching, refetch } = useAuditLog(params);
  const summary = useAuditLogSummary();
  const items = data?.items ?? [];

  const toggleExpand = (id: string) => {
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const resetFilters = () => {
    setAction('all');
    setActorEmail('');
    setPage(1);
  };

  return (
    <>
      <Stack.Screen
        options={{
          title: 'Audit log',
          headerRight: () => (
            <Pressable onPress={resetFilters} hitSlop={10} style={s.headerBtn}>
              <Filter size={16} color="#FFFFFF" />
            </Pressable>
          ),
        }}
      />
      <ScrollView style={s.root} contentContainerStyle={{ padding: 16 }}>
        <View style={s.summaryRow}>
          <SummaryStat label="Total" value={summary.data?.total ?? 0} />
          <SummaryStat label="Logins" value={summary.data?.by_action?.login ?? 0} />
          <SummaryStat label="Failed" value={summary.data?.by_action?.login_failed ?? 0} tone="danger" />
          <SummaryStat label="Changes" value={(summary.data?.by_action?.update ?? 0) + (summary.data?.by_action?.create ?? 0) + (summary.data?.by_action?.delete ?? 0)} tone="info" />
        </View>

        <View style={s.filterSection}>
          <Text style={s.filterLabel}>ACTION</Text>
          <View style={s.chipRow}>
            {ACTION_FILTERS.map((f) => (
              <Chip
                key={f.id}
                label={`${f.label}${summary.data?.by_action?.[f.id] ? ` · ${summary.data.by_action[f.id]}` : ''}`}
                active={action === f.id}
                onPress={() => { setAction(f.id); setPage(1); }}
              />
            ))}
          </View>
        </View>

        <View style={s.filterSection}>
          <Text style={s.filterLabel}>ACTOR</Text>
          <SearchBar
            value={actorEmail}
            onChange={(v) => { setActorEmail(v); setPage(1); }}
            placeholder="Search actor email"
          />
        </View>

        {isLoading ? (
          <View style={s.loading}><Spinner label="Loading audit log…" /></View>
        ) : items.length === 0 ? (
          <View style={s.empty}>
            <FileText size={32} color="#94A3B8" />
            <Text style={s.emptyTitle}>No audit entries</Text>
            <Text style={s.emptyBody}>
              {action !== 'all' || actorEmail
                ? 'Try clearing filters to see more entries.'
                : 'Audit entries will appear here as users perform actions.'}
            </Text>
          </View>
        ) : (
          <>
            <FlatList
              data={items}
              keyExtractor={(e) => e.id}
              scrollEnabled={false}
              ItemSeparatorComponent={() => <View style={{ height: 8 }} />}
              refreshControl={<RefreshControl refreshing={isFetching && !isLoading} onRefresh={refetch} />}
              renderItem={({ item }) => (
                <AuditRow entry={item} expanded={!!expanded[item.id]} onToggle={() => toggleExpand(item.id)} />
              )}
            />
            <View style={s.pagination}>
              <Pressable
                onPress={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                style={[s.pageBtn, page === 1 && s.pageBtnDisabled]}
              >
                <Text style={s.pageBtnText}>← Prev</Text>
              </Pressable>
              <Text style={s.pageInfo}>Page {page}{data?.totalPages ? ` of ${data.totalPages}` : ''}</Text>
              <Pressable
                onPress={() => setPage((p) => p + 1)}
                disabled={!data?.hasMore}
                style={[s.pageBtn, !data?.hasMore && s.pageBtnDisabled]}
              >
                <Text style={s.pageBtnText}>Next →</Text>
              </Pressable>
            </View>
          </>
        )}
      </ScrollView>
    </>
  );
}

function SummaryStat({ label, value, tone = 'neutral' }: { label: string; value: number; tone?: SevTone }) {
  const colorMap: Record<SevTone, string> = {
    ok: '#047857', warn: '#B45309', danger: '#B91C1C', info: '#1D4ED8', neutral: '#475569',
  };
  return (
    <View style={s.statCard}>
      <Text style={s.statLabel}>{label.toUpperCase()}</Text>
      <Text style={[s.statValue, { color: colorMap[tone] }]}>{value.toLocaleString()}</Text>
    </View>
  );
}

function AuditRow({ entry, expanded, onToggle }: { entry: AuditLogEntry; expanded: boolean; onToggle: () => void }) {
  const meta = ACTION_META[entry.action] ?? { label: entry.action, tone: 'neutral' as SevTone, Icon: Activity };
  const Icon = meta.Icon;
  const entityType = entry.entity_type ?? '—';
  const entityId = entry.entity_id ? ` · ${entry.entity_id.slice(0, 8)}…` : '';

  return (
    <BarCard tone={meta.tone}>
      <Pressable onPress={onToggle} style={s.rowHeader}>
        <View style={[s.iconChip, { backgroundColor: '#F1F5F9' }]}>
          <Icon size={18} color={brand.navy} />
        </View>
        <View style={{ flex: 1 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap' }}>
            <Badge label={meta.label} tone={meta.tone === 'ok' ? 'success' : meta.tone === 'danger' ? 'danger' : meta.tone === 'warn' ? 'warning' : 'info'} size="sm" />
            <Text style={s.entityLabel}>
              {' '}{entityType}{entityId}
            </Text>
          </View>
          <Text style={s.actor}>
            {entry.actor_email ?? 'system'}
            {entry.actor_role ? ` · ${entry.actor_role.replace('_', ' ')}` : ''}
          </Text>
          <Text style={s.ts}>{formatDateTime(entry.ts)}</Text>
        </View>
        {expanded ? <ChevronDown size={18} color="#94A3B8" /> : <ChevronRight size={18} color="#94A3B8" />}
      </Pressable>

      {expanded ? (
        <View style={s.details}>
          {entry.before ? (
            <DiffBlock title="Before" data={entry.before} />
          ) : null}
          {entry.after ? (
            <DiffBlock title="After" data={entry.after} />
          ) : null}
          {entry.reason ? (
            <View style={s.reasonRow}>
              <Text style={s.reasonLabel}>Reason</Text>
              <Text style={s.reasonText}>{entry.reason}</Text>
            </View>
          ) : null}
          {entry.ip || entry.user_agent ? (
            <View style={s.metaRow}>
              {entry.ip ? <Text style={s.metaText}>IP: {entry.ip}</Text> : null}
              {entry.user_agent ? <Text style={s.metaText} numberOfLines={1}>UA: {entry.user_agent}</Text> : null}
            </View>
          ) : null}
        </View>
      ) : null}
    </BarCard>
  );
}

function DiffBlock({ title, data }: { title: string; data: Record<string, unknown> }) {
  return (
    <View style={s.diffBlock}>
      <Text style={s.diffTitle}>{title}</Text>
      <Text style={s.diffJson}>{JSON.stringify(data, null, 2)}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F4F4F2' },
  headerBtn: { width: 36, height: 36, borderRadius: 10, backgroundColor: 'rgba(255,255,255,0.15)', alignItems: 'center', justifyContent: 'center', marginRight: 4 },
  summaryRow: { flexDirection: 'row', marginBottom: 14, marginHorizontal: -4 },
  statCard: { flex: 1, backgroundColor: '#F8FAFC', borderRadius: 12, borderWidth: 1, borderColor: '#E2E8F0', padding: 10, marginHorizontal: 4, alignItems: 'center' },
  statLabel: { fontSize: 10, fontWeight: '700', color: '#64748B', letterSpacing: 0.5 },
  statValue: { fontSize: 20, fontWeight: '800', marginTop: 2 },
  filterSection: { marginBottom: 14 },
  filterLabel: { fontSize: 11, fontWeight: '700', color: '#64748B', letterSpacing: 0.6, marginBottom: 6, textTransform: 'uppercase' },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap' },
  loading: { paddingVertical: 40, alignItems: 'center' },
  empty: { backgroundColor: '#F8FAFC', borderRadius: 14, borderWidth: 1, borderColor: '#E2E8F0', padding: 28, alignItems: 'center' },
  emptyTitle: { fontSize: 15, fontWeight: '700', color: '#0F172A', marginTop: 10 },
  emptyBody: { fontSize: 13, color: '#64748B', marginTop: 6, textAlign: 'center', lineHeight: 19 },
  rowHeader: { flexDirection: 'row', alignItems: 'flex-start' },
  iconChip: { width: 40, height: 40, borderRadius: 10, alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  entityLabel: { fontSize: 13, color: '#475569', fontWeight: '600' },
  actor: { fontSize: 13, color: '#0F172A', fontWeight: '600', marginTop: 4 },
  ts: { fontSize: 11, color: '#94A3B8', marginTop: 2 },
  details: { marginTop: 12, paddingTop: 12, borderTopWidth: 1, borderTopColor: '#E2E8F0' },
  diffBlock: { backgroundColor: '#0F172A', borderRadius: 8, padding: 10, marginBottom: 8 },
  diffTitle: { color: '#FFCC00', fontSize: 11, fontWeight: '700', letterSpacing: 0.5, marginBottom: 4 },
  diffJson: { fontFamily: 'Menlo, monospace', color: '#E2E8F0', fontSize: 11, lineHeight: 16 },
  reasonRow: { flexDirection: 'row', marginBottom: 6 },
  reasonLabel: { fontSize: 11, fontWeight: '700', color: '#64748B', width: 70 },
  reasonText: { fontSize: 12, color: '#0F172A', flex: 1 },
  metaRow: { marginTop: 4 },
  metaText: { fontSize: 11, color: '#94A3B8' },
  pagination: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 18, paddingVertical: 12 },
  pageBtn: { backgroundColor: '#FFFFFF', borderWidth: 1, borderColor: '#E2E8F0', borderRadius: 10, paddingHorizontal: 14, paddingVertical: 8 },
  pageBtnDisabled: { opacity: 0.4 },
  pageBtnText: { color: brand.navy, fontWeight: '600', fontSize: 13 },
  pageInfo: { fontSize: 13, color: '#64748B', fontWeight: '600' },
});
