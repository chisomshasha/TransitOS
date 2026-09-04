import React, { useState } from 'react';
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { Stack, useRouter } from 'expo-router';
import { Plus, ShieldAlert } from 'lucide-react-native';
import { useIncidentSummary, useIncidents } from '@/lib/queries-p4';
import { BarCard, Chip, type SevTone } from '@/components/ui/kit';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { EmptyState } from '@/components/ui/EmptyState';
import { brand } from '@/lib/theme';

const SEV_TONE: Record<string, SevTone> = {
  severe: 'danger',
  moderate: 'warn',
  minor: 'info',
};

const FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'open', label: 'Open' },
  { id: 'acknowledged', label: 'Acknowledged' },
  { id: 'resolved', label: 'Resolved' },
];

export default function IncidentsScreen() {
  const router = useRouter();
  const [filter, setFilter] = useState('all');
  const summaryQ = useIncidentSummary();
  const incidentsQ = useIncidents(filter === 'all' ? {} : { status: filter });
  const items = incidentsQ.data?.items ?? [];

  return (
    <>
      <Stack.Screen
        options={{
          title: 'Incidents',
          headerRight: () => (
            <Pressable
              onPress={() => router.push('/report-incident' as never)}
              style={s.headerBtn}
              accessibilityRole="button"
              accessibilityLabel="Report incident"
            >
              <Plus size={18} color="#FFFFFF" />
            </Pressable>
          ),
        }}
      />
      <View style={s.root}>
        <View style={s.counterRow}>
          <Counter label="SEVERE" value={summaryQ.data?.severe ?? 0} color="#B91C1C" />
          <Counter label="MOD." value={summaryQ.data?.moderate ?? 0} color="#B45309" />
          <Counter label="MINOR" value={summaryQ.data?.minor ?? 0} color="#1D4ED8" />
          <Counter label="CLOSED" value={summaryQ.data?.closed ?? 0} color="#047857" />
        </View>

        <View style={s.chipRow}>
          {FILTERS.map((f) => (
            <Chip key={f.id} label={f.label} active={filter === f.id} onPress={() => setFilter(f.id)} />
          ))}
        </View>

        {incidentsQ.isLoading ? (
          <View style={s.loading}><Spinner label="Loading incidents…" /></View>
        ) : items.length === 0 ? (
          <EmptyState title="No incidents" description="Report an incident using the + button." />
        ) : (
          <FlatList
            data={items}
            keyExtractor={(i) => i.id}
            contentContainerStyle={{ padding: 16 }}
            ItemSeparatorComponent={() => <View style={{ height: 12 }} />}
            refreshControl={
              <RefreshControl refreshing={incidentsQ.isFetching} onRefresh={() => incidentsQ.refetch()} />
            }
            renderItem={({ item }) => (
              <BarCard tone={SEV_TONE[item.severity] ?? 'neutral'}>
                <View style={s.badges}>
                  <Badge label={item.severity.toUpperCase()} tone={item.severity === 'severe' ? 'danger' : item.severity === 'moderate' ? 'warning' : 'info'} size="sm" />
                  <Badge label={item.status.toUpperCase()} tone={item.status === 'open' ? 'warning' : item.status === 'resolved' ? 'success' : 'neutral'} size="sm" />
                </View>
                <Text style={s.title}>{item.category.replace('_', ' ')}</Text>
                <Text style={s.desc} numberOfLines={3}>{item.description}</Text>
                <Text style={s.meta}>
                  {new Date(item.created_at).toLocaleString()}
                </Text>
              </BarCard>
            )}
          />
        )}
      </View>
    </>
  );
}

function Counter({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <View style={s.counterCard}>
      <Text style={[s.counterLabel, { color }]}>{label}</Text>
      <Text style={s.counterValue}>{value}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F4F4F2' },
  headerBtn: { width: 36, height: 36, borderRadius: 10, backgroundColor: 'rgba(255,255,255,0.15)', alignItems: 'center', justifyContent: 'center', marginRight: 4 },
  counterRow: { flexDirection: 'row', padding: 16, paddingBottom: 8, gap: 8 },
  counterCard: { flex: 1, backgroundColor: '#F8FAFC', borderRadius: 12, borderWidth: 1, borderColor: '#E2E8F0', padding: 10, alignItems: 'center' },
  counterLabel: { fontSize: 11, fontWeight: '700', letterSpacing: 0.5 },
  counterValue: { fontSize: 22, fontWeight: '800', color: '#0F172A', marginTop: 2 },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', paddingHorizontal: 16, paddingBottom: 8 },
  loading: { paddingVertical: 40, alignItems: 'center' },
  badges: { flexDirection: 'row', marginBottom: 8, gap: 6 },
  title: { fontSize: 16, fontWeight: '700', color: '#0F172A', textTransform: 'capitalize' },
  desc: { fontSize: 13, color: '#475569', marginTop: 4, lineHeight: 19 },
  meta: { fontSize: 11, color: '#94A3B8', marginTop: 8 },
});
