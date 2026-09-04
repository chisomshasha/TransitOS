import React, { useMemo, useState } from 'react';
import { Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import {
  AlertTriangle, BarChart3, Bus, Fuel, Gauge, Receipt, TrendingUp, Truck, Users, Wallet,
} from 'lucide-react-native';
import {
  useOperationsSummary, useProfitLoss, useCashFlow, useTopRoutes,
  useDriverPerformance, useVehicleUtilization, useIncidentsSummary,
  useFuelSummary,
} from '@/lib/queries';
import { PageHeader } from '@/components/ui/PageHeader';
import { Spinner } from '@/components/ui/Spinner';
import { Chip } from '@/components/ui/kit';
import { formatNGN } from '@/lib/format';
import { brand } from '@/lib/theme';

const RANGES = [
  { label: '7 days', days: 7 },
  { label: '30 days', days: 30 },
  { label: '90 days', days: 90 },
];

const CATEGORIES = [
  { id: 'operations', label: 'Operations' },
  { id: 'financials', label: 'Financials' },
  { id: 'fleet', label: 'Fleet' },
  { id: 'safety', label: 'Safety' },
];

export default function ReportsScreen() {
  const [days, setDays] = useState(30);
  const [category, setCategory] = useState('operations');
  const params = useMemo(() => {
    const to = new Date();
    const from = new Date(to.getTime() - days * 24 * 60 * 60 * 1000);
    return { from: from.toISOString(), to: to.toISOString() };
  }, [days]);

  const summary = useOperationsSummary(params);
  const pl = useProfitLoss(params);
  const cashFlow = useCashFlow({ ...params, bucket: 'week' });
  const topRoutes = useTopRoutes({ ...params, limit: 5 });
  const driverPerf = useDriverPerformance({ ...params, limit: 5 });
  const vehicleUtil = useVehicleUtilization(params);
  const incidents = useIncidentsSummary(params);
  const fuel = useFuelSummary(params);

  const refreshing = [summary, pl, cashFlow, topRoutes, driverPerf, vehicleUtil, incidents, fuel]
    .some((q) => q.isFetching);
  const onRefresh = () => {
    [summary, pl, cashFlow, topRoutes, driverPerf, vehicleUtil, incidents, fuel]
      .forEach((q) => q.refetch());
  };

  const totals = summary.data?.totals;
  const revenue = totals?.revenue ?? 0;
  const variance = totals?.variance ?? 0;
  const tripsCount = totals?.trips ?? 0;
  const expenses = totals?.expenses ?? 0;

  return (
    <View style={s.root}>
      <View style={s.headerWrap}>
        <PageHeader title="Reports" subtitle="Financial & operational insights" />
        <View style={s.chipRow}>
          {RANGES.map((r) => {
            const active = r.days === days;
            return (
              <Pressable
                key={r.days}
                onPress={() => setDays(r.days)}
                style={[s.rangeChip, active && s.rangeChipActive]}
              >
                <Text style={[s.rangeChipText, active && s.rangeChipTextActive]}>{r.label}</Text>
              </Pressable>
            );
          })}
        </View>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginTop: 10 }}>
          {CATEGORIES.map((c) => (
            <Chip
              key={c.id}
              label={c.label}
              active={category === c.id}
              onPress={() => setCategory(c.id)}
            />
          ))}
        </ScrollView>
      </View>

      {summary.isLoading ? (
        <View style={s.loading}><Spinner label="Crunching numbers…" /></View>
      ) : (
        <ScrollView
          contentContainerStyle={{ padding: 16, paddingBottom: 80 }}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        >
          {category === 'operations' ? (
            <>
              <SectionTitle>At a glance</SectionTitle>
              <View style={s.grid}>
                <StatCard icon={<TrendingUp size={18} color="#047857" />} iconBg="#ECFDF5" label="Revenue" value={formatNGN(revenue)} sub={`Last ${days} days`} />
                <StatCard icon={<Bus size={18} color={brand.navy} />} iconBg="#FFFBEB" label="Trips" value={String(tripsCount)} sub={`Last ${days} days`} />
                <StatCard
                  icon={<Wallet size={18} color={variance >= 0 ? '#047857' : '#B91C1C'} />}
                  iconBg={variance >= 0 ? '#ECFDF5' : '#FEF2F2'}
                  label="Cash variance"
                  value={formatNGN(variance)}
                  sub={variance >= 0 ? 'Within tolerance' : 'Needs review'}
                  valueColor={variance >= 0 ? '#047857' : '#B91C1C'}
                />
                <StatCard icon={<Receipt size={18} color="#B45309" />} iconBg="#FFFBEB" label="Expenses" value={formatNGN(expenses)} sub={`Last ${days} days`} />
              </View>

              <SectionTitle>Top routes</SectionTitle>
              <TopRoutesCard routes={topRoutes.data?.routes ?? []} />

              <SectionTitle>Driver leaderboard</SectionTitle>
              <DriversCard drivers={driverPerf.data?.drivers ?? []} />
            </>
          ) : null}

          {category === 'financials' ? (
            <>
              <SectionTitle>Profit & Loss</SectionTitle>
              <PLCard data={pl.data} />

              <SectionTitle>Cash flow (weekly)</SectionTitle>
              <CashFlowCard data={cashFlow.data} />

              <SectionTitle>Fuel spend</SectionTitle>
              <FuelCard data={fuel.data} />
            </>
          ) : null}

          {category === 'fleet' ? (
            <>
              <SectionTitle>Vehicle utilization</SectionTitle>
              <UtilizationCard vehicles={vehicleUtil.data?.vehicles ?? []} />

              <SectionTitle>Fuel spend</SectionTitle>
              <FuelCard data={fuel.data} />
            </>
          ) : null}

          {category === 'safety' ? (
            <>
              <SectionTitle>Incidents summary</SectionTitle>
              <IncidentsCard data={incidents.data} />
            </>
          ) : null}
        </ScrollView>
      )}
    </View>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <Text style={s.sectionTitle}>{children}</Text>;
}

function StatCard({ icon, iconBg, label, value, sub, valueColor }: {
  icon: React.ReactNode; iconBg: string; label: string; value: string; sub: string; valueColor?: string;
}) {
  return (
    <View style={s.cardWrap}>
      <View style={s.card}>
        <View style={[s.iconBox, { backgroundColor: iconBg }]}>{icon}</View>
        <Text style={s.cardLabel}>{label}</Text>
        <Text style={[s.cardValue, valueColor ? { color: valueColor } : null]} numberOfLines={1}>{value}</Text>
        <Text style={s.cardSub}>{sub}</Text>
      </View>
    </View>
  );
}

function TopRoutesCard({ routes }: { routes: Array<{ route_id: string; name: string; origin_city?: string | null; destination_city?: string | null; trips: number; revenue: number; passengers: number }> }) {
  if (routes.length === 0) {
    return <View style={s.emptyCard}><Text style={s.emptyText}>No route data in this window</Text></View>;
  }
  const maxRev = Math.max(...routes.map((r) => r.revenue), 1);
  return (
    <View style={s.listCard}>
      {routes.map((r, i) => (
        <View key={r.route_id} style={s.listRow}>
          <Text style={s.listRank}>{i + 1}</Text>
          <View style={{ flex: 1 }}>
            <Text style={s.listName} numberOfLines={1}>{r.name}</Text>
            <Text style={s.listSub}>{r.trips} trips · {r.passengers} pax</Text>
            <View style={s.barWrap}>
              <View style={[s.bar, { width: `${(r.revenue / maxRev) * 100}%` }]} />
            </View>
          </View>
          <Text style={s.listAmount}>{formatNGN(r.revenue)}</Text>
        </View>
      ))}
    </View>
  );
}

function DriversCard({ drivers }: { drivers: Array<{ driver_id: string; name: string; trips: number; completion_pct: number; revenue: number }> }) {
  if (drivers.length === 0) {
    return <View style={s.emptyCard}><Text style={s.emptyText}>No driver activity in this window</Text></View>;
  }
  return (
    <View style={s.listCard}>
      {drivers.map((d, i) => (
        <View key={d.driver_id} style={s.listRow}>
          <Text style={s.listRank}>{i + 1}</Text>
          <View style={{ flex: 1 }}>
            <Text style={s.listName} numberOfLines={1}>{d.name}</Text>
            <Text style={s.listSub}>{d.trips} trips · {d.completion_pct.toFixed(0)}% completed</Text>
          </View>
          <Text style={s.listAmount}>{formatNGN(d.revenue)}</Text>
        </View>
      ))}
    </View>
  );
}

function PLCard({ data }: { data?: { revenue: number; expenses_breakdown: Record<string, number>; total_expenses: number; net: number } }) {
  if (!data) return <View style={s.emptyCard}><Text style={s.emptyText}>Loading…</Text></View>;
  const netColor = data.net >= 0 ? '#047857' : '#B91C1C';
  return (
    <View style={s.listCard}>
      <View style={s.plRow}>
        <Text style={s.plLabel}>Revenue</Text>
        <Text style={s.plValue}>{formatNGN(data.revenue)}</Text>
      </View>
      <View style={s.plRow}>
        <Text style={s.plLabel}>  Trip expenses</Text>
        <Text style={s.plValue}>{formatNGN(data.expenses_breakdown.trip_expenses)}</Text>
      </View>
      <View style={s.plRow}>
        <Text style={s.plLabel}>  Fuel</Text>
        <Text style={s.plValue}>{formatNGN(data.expenses_breakdown.fuel)}</Text>
      </View>
      <View style={s.plRow}>
        <Text style={s.plLabel}>  Maintenance</Text>
        <Text style={s.plValue}>{formatNGN(data.expenses_breakdown.maintenance)}</Text>
      </View>
      <View style={s.plRow}>
        <Text style={s.plLabel}>  Standalone expenses</Text>
        <Text style={s.plValue}>{formatNGN(data.expenses_breakdown.standalone)}</Text>
      </View>
      <View style={[s.plRow, s.plTotal]}>
        <Text style={s.plLabel}>Total expenses</Text>
        <Text style={s.plValue}>{formatNGN(data.total_expenses)}</Text>
      </View>
      <View style={[s.plRow, s.plTotal, { borderTopWidth: 1, borderTopColor: brand.border }]}>
        <Text style={[s.plLabel, { fontWeight: '800' }]}>NET PROFIT</Text>
        <Text style={[s.plValue, { color: netColor, fontWeight: '800' }]}>{formatNGN(data.net)}</Text>
      </View>
    </View>
  );
}

function CashFlowCard({ data }: { data?: { series: Array<{ label: string; revenue: number; expenses: number; net: number }> } }) {
  if (!data || data.series.length === 0) {
    return <View style={s.emptyCard}><Text style={s.emptyText}>No cash-flow data</Text></View>;
  }
  const maxVal = Math.max(...data.series.flatMap((row) => [row.revenue, row.expenses]), 1);
  return (
    <View style={s.listCard}>
      {data.series.map((row) => (
        <View key={row.label} style={s.cfRow}>
          <Text style={s.cfLabel}>{row.label}</Text>
          <View style={{ flex: 1, marginHorizontal: 10 }}>
            <View style={[s.cfBar, { width: `${(row.revenue / maxVal) * 100}%`, backgroundColor: '#047857', marginBottom: 3 }]} />
            <View style={[s.cfBar, { width: `${(row.expenses / maxVal) * 100}%`, backgroundColor: '#B91C1C' }]} />
          </View>
          <Text style={[s.cfNet, { color: row.net >= 0 ? '#047857' : '#B91C1C' }]}>
            {formatNGN(row.net)}
          </Text>
        </View>
      ))}
    </View>
  );
}

function FuelCard({ data }: { data?: { total_liters: number; total_cost: number; samples: number; avg_cost_per_liter: number | null } }) {
  if (!data) return <View style={s.emptyCard}><Text style={s.emptyText}>No fuel data</Text></View>;
  return (
    <View style={s.grid}>
      <StatCard icon={<Fuel size={18} color="#B45309" />} iconBg="#FFFBEB" label="Total liters" value={`${data.total_liters.toFixed(0)} L`} sub={`${data.samples} samples`} />
      <StatCard icon={<Wallet size={18} color="#B45309" />} iconBg="#FFFBEB" label="Total cost" value={formatNGN(data.total_cost)} sub={data.avg_cost_per_liter ? `₦${data.avg_cost_per_liter.toFixed(0)}/L` : '—'} />
    </View>
  );
}

function UtilizationCard({ vehicles }: { vehicles: Array<{ vehicle_id: string; reg_number?: string | null; trips: number; revenue: number; downtime_days: number; utilization_pct: number }> }) {
  if (vehicles.length === 0) {
    return <View style={s.emptyCard}><Text style={s.emptyText}>No vehicle data</Text></View>;
  }
  return (
    <View style={s.listCard}>
      {vehicles.slice(0, 8).map((v) => {
        const utilColor = v.utilization_pct >= 80 ? '#047857' : v.utilization_pct >= 50 ? '#B45309' : '#B91C1C';
        return (
          <View key={v.vehicle_id} style={s.listRow}>
            <View style={s.listIconBg}><Truck size={16} color={brand.navy} /></View>
            <View style={{ flex: 1 }}>
              <Text style={s.listName} numberOfLines={1}>{v.reg_number ?? '—'}</Text>
              <Text style={s.listSub}>{v.trips} trips · {v.downtime_days}d downtime</Text>
              <View style={s.barWrap}>
                <View style={[s.bar, { width: `${v.utilization_pct}%`, backgroundColor: utilColor }]} />
              </View>
            </View>
            <Text style={[s.listAmount, { color: utilColor }]}>{v.utilization_pct.toFixed(0)}%</Text>
          </View>
        );
      })}
    </View>
  );
}

function IncidentsCard({ data }: { data?: { total: number; by_severity: Record<string, number>; by_status: Record<string, number> } }) {
  if (!data) return <View style={s.emptyCard}><Text style={s.emptyText}>No incident data</Text></View>;
  return (
    <View style={s.listCard}>
      <View style={s.plRow}>
        <Text style={s.plLabel}>Total incidents</Text>
        <Text style={s.plValue}>{data.total}</Text>
      </View>
      <View style={s.plRow}>
        <Text style={s.plLabel}>Severe</Text>
        <Text style={[s.plValue, { color: '#B91C1C' }]}>{data.by_severity.severe ?? 0}</Text>
      </View>
      <View style={s.plRow}>
        <Text style={s.plLabel}>Moderate</Text>
        <Text style={[s.plValue, { color: '#B45309' }]}>{data.by_severity.moderate ?? 0}</Text>
      </View>
      <View style={s.plRow}>
        <Text style={s.plLabel}>Minor</Text>
        <Text style={s.plValue}>{data.by_severity.minor ?? 0}</Text>
      </View>
      <View style={[s.plRow, s.plTotal]}>
        <Text style={s.plLabel}>Open</Text>
        <Text style={s.plValue}>{data.by_status.open ?? 0}</Text>
      </View>
      <View style={s.plRow}>
        <Text style={s.plLabel}>Resolved</Text>
        <Text style={s.plValue}>{data.by_status.resolved ?? 0}</Text>
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F8F7F4' },
  headerWrap: { paddingHorizontal: 16, paddingTop: 8, paddingBottom: 12, backgroundColor: '#FFFFFF', borderBottomWidth: 1, borderBottomColor: '#E5E5E5' },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  chipRow: { flexDirection: 'row', marginTop: 8 },
  rangeChip: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 9999, marginRight: 6, backgroundColor: '#F1F5F9' },
  rangeChipActive: { backgroundColor: brand.navy },
  rangeChipText: { fontSize: 12, fontWeight: '500', color: '#334155' },
  rangeChipTextActive: { color: '#FFFFFF' },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: brand.slate, marginTop: 18, marginBottom: 10 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', marginHorizontal: -6 },
  cardWrap: { width: '50%', padding: 6 },
  card: { backgroundColor: '#FFFFFF', borderRadius: 14, padding: 14, borderWidth: 1, borderColor: '#E5E7EB', minHeight: 110 },
  iconBox: { width: 32, height: 32, borderRadius: 10, alignItems: 'center', justifyContent: 'center', marginBottom: 8 },
  cardLabel: { fontSize: 11, color: '#64748B', fontWeight: '500' },
  cardValue: { fontSize: 18, fontWeight: '700', color: '#0F172A', marginTop: 2 },
  cardSub: { fontSize: 10, color: '#64748B', marginTop: 2 },
  listCard: { backgroundColor: '#FFFFFF', borderRadius: 14, padding: 14, borderWidth: 1, borderColor: '#E5E7EB' },
  listRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#F1F5F9' },
  listRank: { width: 24, fontSize: 14, fontWeight: '700', color: brand.muted },
  listIconBg: { width: 32, height: 32, borderRadius: 8, backgroundColor: '#EFF6FF', alignItems: 'center', justifyContent: 'center', marginRight: 10 },
  listName: { fontSize: 14, fontWeight: '600', color: brand.slate },
  listSub: { fontSize: 11, color: brand.muted, marginTop: 2 },
  listAmount: { fontSize: 14, fontWeight: '700', color: brand.navy },
  barWrap: { height: 4, backgroundColor: '#F1F5F9', borderRadius: 2, marginTop: 6, overflow: 'hidden' },
  bar: { height: 4, borderRadius: 2, backgroundColor: brand.navy },
  plRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8 },
  plTotal: { borderTopWidth: 1, borderTopColor: '#F1F5F9', marginTop: 4, paddingTop: 10 },
  plLabel: { fontSize: 13, color: brand.muted },
  plValue: { fontSize: 13, fontWeight: '600', color: brand.slate },
  cfRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: '#F1F5F9' },
  cfLabel: { width: 64, fontSize: 11, color: brand.muted },
  cfBar: { height: 4, borderRadius: 2 },
  cfNet: { width: 80, textAlign: 'right', fontSize: 12, fontWeight: '700' },
  emptyCard: { backgroundColor: '#FFFFFF', borderRadius: 14, padding: 20, alignItems: 'center', borderWidth: 1, borderColor: '#E5E7EB' },
  emptyText: { fontSize: 13, color: brand.muted },
});
