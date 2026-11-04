import React, { useState } from 'react';
import {
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { Stack, useRouter } from 'expo-router';
import { Wallet } from 'lucide-react-native';
import {
  useGenerateSettlement,
  useSettlements,
  useSettlementSummary,
  SETTLEMENT_STATUS_LABELS,
  type Settlement,
  type SettlementStatus,
} from '@/lib/queries-settlements';
import { useBranches } from '@/lib/queries';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { EmptyState } from '@/components/ui/EmptyState';
import { PageHeader } from '@/components/ui/PageHeader';
import { Modal } from '@/components/ui/Modal';
import { Field } from '@/components/ui/Field';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { useToast } from '@/components/ui/Toast';
import { useAuth } from '@/lib/auth-context';
import { canAccess } from '@/lib/rbac';
import { formatNGN } from '@/lib/format';
import type { Role } from '@/lib/types';

const GENERATE_ROLES: Role[] = [
  'super_admin', 'owner', 'general_manager', 'chief_accountant', 'branch_accountant',
];

const STATUS_TONE: Record<string, 'neutral' | 'info' | 'success' | 'warning' | 'danger'> = {
  draft: 'neutral',
  submitted: 'info',
  approved: 'success',
  paid: 'success',
  rejected: 'danger',
};

function defaultPeriod(): { start: string; end: string } {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), 1);
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  return { start: start.toISOString().slice(0, 10), end: end.toISOString().slice(0, 10) };
}

export default function SettlementsScreen() {
  const router = useRouter();
  const toast = useToast();
  const { user } = useAuth();

  const [statusFilter, setStatusFilter] = useState<'all' | SettlementStatus>('all');
  const settlementsQ = useSettlements(
    statusFilter === 'all' ? { page: 1, page_size: 100 } : { page: 1, page_size: 100, status: statusFilter }
  );
  const summaryQ = useSettlementSummary();
  const branchesQ = useBranches({ page: 1, page_size: 100 });

  const [open, setOpen] = useState(false);
  const [branchId, setBranchId] = useState<string | null>(null);
  const period = defaultPeriod();
  const [periodStart, setPeriodStart] = useState(period.start);
  const [periodEnd, setPeriodEnd] = useState(period.end);
  const [driverRate, setDriverRate] = useState('');
  const [conductorRate, setConductorRate] = useState('');

  const generate = useGenerateSettlement();

  const canGenerate = canAccess(user?.role, GENERATE_ROLES);
  const items = settlementsQ.data?.items ?? [];
  const branchOptions = (branchesQ.data?.items ?? []).map((b) => ({ label: b.name, value: b.id }));

  const onGenerate = async () => {
    if (!branchId) return toast.error('Branch is required');
    if (!periodStart || !periodEnd) return toast.error('Period is required');
    if (new Date(periodEnd) < new Date(periodStart)) {
      return toast.error('The end date must be after the start date');
    }
    try {
      await generate.mutateAsync({
        branch_id: branchId,
        period_start: new Date(`${periodStart}T00:00:00`).toISOString(),
        period_end: new Date(`${periodEnd}T23:59:59`).toISOString(),
        driver_rate: parseFloat(driverRate) || 0,
        conductor_rate: parseFloat(conductorRate) || 0,
      });
      toast.success('Settlement generated');
      setOpen(false);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not generate the settlement');
    }
  };

  const totals = summaryQ.data?.totals;

  return (
    <>
      <Stack.Screen options={{ title: 'Settlements' }} />
      <View style={s.root}>
        <View style={s.headerWrap}>
          <PageHeader
            title="Settlements"
            subtitle={
              totals
                ? `${formatNGN(totals.net_payable)} across ${summaryQ.data?.by_status?.draft?.count ?? 0} draft(s)`
                : undefined
            }
            primaryActionLabel={canGenerate ? 'Generate' : undefined}
            onPrimaryAction={canGenerate ? () => setOpen(true) : undefined}
          />
        </View>

        <View style={s.chipRow}>
          {(['all', 'draft', 'submitted', 'approved', 'paid', 'rejected'] as const).map((st) => (
            <Pressable
              key={st}
              onPress={() => setStatusFilter(st)}
              style={[s.chip, statusFilter === st && s.chipActive]}
              accessibilityRole="button"
            >
              <Text style={[s.chipText, statusFilter === st && s.chipTextActive]}>
                {st === 'all' ? 'All' : SETTLEMENT_STATUS_LABELS[st]}
              </Text>
            </Pressable>
          ))}
        </View>

        {totals ? (
          <View style={s.summaryRow}>
            <SummaryTile label="REVENUE" value={formatNGN(totals.gross_revenue)} tone="#0F172A" />
            <SummaryTile label="EXPENSES" value={formatNGN(totals.trip_expenses + totals.standalone_expenses)} tone="#B91C1C" />
            <SummaryTile label="PAYROLL" value={formatNGN(totals.driver_payroll + totals.conductor_payroll)} tone="#B45309" />
            <SummaryTile label="NET" value={formatNGN(totals.net_payable)} tone="#047857" />
          </View>
        ) : null}

        {settlementsQ.isLoading ? (
          <View style={s.loading}><Spinner label="Loading settlements…" /></View>
        ) : items.length === 0 ? (
          <EmptyState
            icon={<Wallet size={28} color="#94A3B8" />}
            title="No settlements yet"
            description="Generate a settlement to close off a branch's revenue, expenses and crew payroll for a period."
          />
        ) : (
          <FlatList
            data={items}
            keyExtractor={(s2) => s2.id}
            contentContainerStyle={{ padding: 16, paddingTop: 0 }}
            ItemSeparatorComponent={() => <View style={{ height: 12 }} />}
            refreshControl={
              <RefreshControl
                refreshing={settlementsQ.isRefetching}
                onRefresh={() => {
                  void settlementsQ.refetch();
                  void summaryQ.refetch();
                }}
              />
            }
            renderItem={({ item }) => (
              <Pressable
                onPress={() => router.push(`/settlements/${item.id}` as never)}
                accessibilityRole="button"
              >
                <Card padding="sm">
                  <View style={s.row}>
                    <View style={s.body}>
                      <Text style={s.name}>{item.branch_name ?? item.branch_id}</Text>
                      <Text style={s.sub}>
                        {new Date(item.period_start).toLocaleDateString()} –{' '}
                        {new Date(item.period_end).toLocaleDateString()} · {item.trip_count} trips
                      </Text>
                    </View>
                    <View style={s.right}>
                      <Badge
                        label={SETTLEMENT_STATUS_LABELS[item.status] ?? item.status}
                        tone={STATUS_TONE[item.status] ?? 'neutral'}
                        size="sm"
                      />
                      <Text style={s.amount}>{formatNGN(item.net_payable)}</Text>
                    </View>
                  </View>
                </Card>
              </Pressable>
            )}
          />
        )}
      </View>

      <Modal visible={open} onClose={() => setOpen(false)} title="Generate settlement" variant="sheet">
        <Field label="Branch" required>
          <Select value={branchId} onChange={setBranchId} options={branchOptions} placeholder="Select branch" />
        </Field>
        <Field label="Period start" required helperText="YYYY-MM-DD">
          <TextInput style={s.input} value={periodStart} onChangeText={setPeriodStart} placeholder="2026-01-01" placeholderTextColor="#94A3B8" autoCapitalize="none" />
        </Field>
        <Field label="Period end" required helperText="YYYY-MM-DD">
          <TextInput style={s.input} value={periodEnd} onChangeText={setPeriodEnd} placeholder="2026-01-31" placeholderTextColor="#94A3B8" autoCapitalize="none" />
        </Field>
        <Field label="Driver pay per trip (₦)">
          <TextInput style={s.input} value={driverRate} onChangeText={setDriverRate} keyboardType="decimal-pad" placeholder="0" placeholderTextColor="#94A3B8" />
        </Field>
        <Field label="Conductor pay per trip (₦)">
          <TextInput style={s.input} value={conductorRate} onChangeText={setConductorRate} keyboardType="decimal-pad" placeholder="0" placeholderTextColor="#94A3B8" />
        </Field>
        <View style={{ height: 12 }} />
        <Button label="Generate" onPress={onGenerate} loading={generate.isPending} fullWidth />
        <View style={{ height: 8 }} />
        <Button label="Cancel" onPress={() => setOpen(false)} variant="ghost" fullWidth />
      </Modal>
    </>
  );
}

function SummaryTile({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <View style={s.tile}>
      <Text style={s.tileLabel}>{label}</Text>
      <Text style={[s.tileValue, { color: tone }]} numberOfLines={1}>{value}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F4F4F2' },
  headerWrap: { paddingHorizontal: 16, paddingTop: 8, paddingBottom: 12, backgroundColor: '#FFFFFF', borderBottomWidth: 1, borderBottomColor: '#E5E5E5' },
  loading: { paddingVertical: 40, alignItems: 'center' },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, paddingHorizontal: 16, paddingVertical: 10 },
  chip: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 999, backgroundColor: '#FFFFFF', borderWidth: 1, borderColor: '#E2E8F0' },
  chipActive: { backgroundColor: '#0B3D91', borderColor: '#0B3D91' },
  chipText: { fontSize: 12, fontWeight: '600', color: '#64748B' },
  chipTextActive: { color: '#FFFFFF' },
  summaryRow: { flexDirection: 'row', gap: 8, paddingHorizontal: 16, paddingBottom: 12 },
  tile: { flex: 1, backgroundColor: '#FFFFFF', borderRadius: 12, borderWidth: 1, borderColor: '#E2E8F0', padding: 10 },
  tileLabel: { fontSize: 9.5, fontWeight: '700', color: '#94A3B8', letterSpacing: 0.5 },
  tileValue: { fontSize: 13, fontWeight: '800', marginTop: 2 },
  row: { flexDirection: 'row', alignItems: 'center' },
  body: { flex: 1 },
  right: { alignItems: 'flex-end' },
  name: { fontSize: 14, fontWeight: '700', color: '#171717' },
  sub: { fontSize: 12, color: '#737373', marginTop: 2 },
  amount: { fontSize: 15, fontWeight: '800', color: '#047857', marginTop: 4 },
  input: { height: 48, paddingHorizontal: 12, borderRadius: 12, borderWidth: 1, borderColor: '#E2E8F0', backgroundColor: '#FFFFFF', fontSize: 16, color: '#0F172A' },
});
