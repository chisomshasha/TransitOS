import React, { useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { Stack, useLocalSearchParams } from 'expo-router';
import { ArrowRightLeft, Bus, CalendarDays } from 'lucide-react-native';
import { useAdvanceTransfer, useVehicleTransfer } from '@/lib/queries-p5';
import { useBranches, useVehicles } from '@/lib/queries';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { Button } from '@/components/ui/Button';
import { useToast } from '@/components/ui/Toast';
import { formatDateTime } from '@/lib/format';
import { brand } from '@/lib/theme';
import { canAccess } from '@/lib/rbac';
import { useAuth } from '@/lib/auth-context';

const OPERATOR_ROLES = [
  'super_admin',
  'owner',
  'general_manager',
  'operations_manager',
  'branch_manager',
  'fleet_manager',
];

export default function TransferDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user } = useAuth();
  const toast = useToast();
  const { data, isLoading } = useVehicleTransfer(id ?? '');
  const advance = useAdvanceTransfer(id ?? '');
  const branchesQ = useBranches({ page: 1, page_size: 200 });
  const vehiclesQ = useVehicles({ page: 1, page_size: 200 });
  const [note, setNote] = useState('');
  const [actioning, setActioning] = useState<string | null>(null);

  if (isLoading) {
    return (
      <>
        <Stack.Screen options={{ title: 'Transfer' }} />
        <View style={s.loading}><Spinner label="Loading transfer…" /></View>
      </>
    );
  }
  if (!data) {
    return (
      <>
        <Stack.Screen options={{ title: 'Transfer' }} />
        <View style={s.loading}><Text style={s.errorText}>Transfer not found</Text></View>
      </>
    );
  }

  const vehicle = vehiclesQ.data?.items.find((v) => v.id === data.vehicle_id);
  const fromBranch = branchesQ.data?.items.find((b) => b.id === data.from_branch_id);
  const toBranch = branchesQ.data?.items.find((b) => b.id === data.to_branch_id);
  const canAct = canAccess(user?.role, OPERATOR_ROLES);

  const onAdvance = (action: 'confirm' | 'return' | 'cancel') => {
    const title =
      action === 'confirm'
        ? 'Confirm receipt?'
        : action === 'return'
        ? 'Mark as returned?'
        : 'Cancel this transfer?';
    const body =
      action === 'confirm'
        ? `This moves ${vehicle?.reg_number ?? 'the vehicle'} to ${toBranch?.name}.`
        : action === 'return'
        ? `This returns ${vehicle?.reg_number ?? 'the vehicle'} to ${fromBranch?.name}.`
        : 'The vehicle will be returned to the origin branch if already confirmed.';
    Alert.alert(title, body, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Confirm',
        onPress: async () => {
          setActioning(action);
          try {
            await advance.mutateAsync({ action, notes: note || undefined });
            toast.success(`Transfer ${action}ed`);
            setNote('');
          } catch (e: any) {
            toast.error(e?.response?.data?.detail ?? `Could not ${action}`);
          } finally {
            setActioning(null);
          }
        },
      },
    ]);
  };

  return (
    <>
      <Stack.Screen options={{ title: `Transfer ${data.id.slice(0, 8)}` }} />
      <ScrollView style={s.root} contentContainerStyle={{ padding: 16, paddingBottom: 60 }}>
        <View style={s.hero}>
          <View style={s.iconBox}>
            <Bus size={28} color="#FFFFFF" />
          </View>
          <Text style={s.reg}>{vehicle?.reg_number ?? 'Vehicle'}</Text>
          <Badge
            label={data.status.replace('_', ' ')}
            tone={
              data.status === 'returned'
                ? 'success'
                : data.status === 'confirmed'
                ? 'info'
                : data.status === 'initiated'
                ? 'warning'
                : 'neutral'
            }
          />
        </View>

        <View style={s.routeCard}>
          <Text style={s.routeLabel}>FROM</Text>
          <Text style={s.routeName}>{fromBranch?.name ?? '—'}</Text>
          <Text style={s.routeCity}>{fromBranch?.city ?? ''}</Text>
          <ArrowRightLeft size={24} color={brand.navy} style={{ alignSelf: 'center', marginVertical: 14 }} />
          <Text style={s.routeLabel}>TO</Text>
          <Text style={s.routeName}>{toBranch?.name ?? '—'}</Text>
          <Text style={s.routeCity}>{toBranch?.city ?? ''}</Text>
        </View>

        {data.reason ? (
          <View style={s.sectionCard}>
            <Text style={s.sectionLabel}>Reason</Text>
            <Text style={s.sectionBody}>{data.reason}</Text>
          </View>
        ) : null}

        {data.notes ? (
          <View style={s.sectionCard}>
            <Text style={s.sectionLabel}>Notes</Text>
            <Text style={s.sectionBody}>{data.notes}</Text>
          </View>
        ) : null}

        <View style={s.sectionCard}>
          <Text style={s.sectionLabel}>Timeline</Text>
          <TimelineRow label="Initiated" value={data.initiated_at} />
          <TimelineRow label="Confirmed" value={data.confirmed_at} />
          <TimelineRow label="Returned" value={data.returned_at} />
          <TimelineRow label="Cancelled" value={data.cancelled_at} />
          {data.expected_return_at ? (
            <View style={s.timelineRow}>
              <CalendarDays size={14} color={brand.muted} />
              <Text style={s.timelineLabel}>Expected return</Text>
              <Text style={s.timelineValue}>{formatDateTime(data.expected_return_at)}</Text>
            </View>
          ) : null}
        </View>

        {canAct && data.status !== 'returned' && data.status !== 'cancelled' ? (
          <View style={s.actionsCard}>
            <Text style={s.sectionLabel}>Actions</Text>
            <TextInput
              style={s.noteInput}
              value={note}
              onChangeText={setNote}
              placeholder="Optional note for this action…"
              placeholderTextColor="#94A3B8"
              multiline
            />
            <View style={{ height: 10 }} />
            {data.status === 'initiated' ? (
              <Button
                label="Confirm receipt"
                onPress={() => onAdvance('confirm')}
                loading={advance.isPending && actioning === 'confirm'}
                fullWidth
              />
            ) : null}
            {data.status === 'confirmed' ? (
              <Button
                label="Mark as returned"
                onPress={() => onAdvance('return')}
                loading={advance.isPending && actioning === 'return'}
                fullWidth
              />
            ) : null}
            <View style={{ height: 10 }} />
            <Button
              label="Cancel transfer"
              variant="danger"
              onPress={() => onAdvance('cancel')}
              loading={advance.isPending && actioning === 'cancel'}
              fullWidth
            />
          </View>
        ) : null}
      </ScrollView>
    </>
  );
}

function TimelineRow({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <View style={s.timelineRow}>
      <View style={s.timelineDot} />
      <Text style={s.timelineLabel}>{label}</Text>
      <Text style={s.timelineValue}>{formatDateTime(value)}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F4F4F2' },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  errorText: { fontSize: 16, color: '#B91C1C' },
  hero: {
    backgroundColor: brand.navy,
    borderRadius: 16,
    padding: 20,
    alignItems: 'center',
    marginBottom: 16,
  },
  iconBox: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: 'rgba(255,255,255,0.15)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 10,
  },
  reg: { fontSize: 22, fontWeight: '800', color: '#FFFFFF', marginBottom: 8 },
  routeCard: {
    backgroundColor: '#F8FAFC',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    padding: 16,
    marginBottom: 12,
    alignItems: 'center',
  },
  routeLabel: { fontSize: 11, fontWeight: '700', color: '#64748B', letterSpacing: 0.6 },
  routeName: { fontSize: 18, fontWeight: '700', color: '#0F172A', marginTop: 4, textAlign: 'center' },
  routeCity: { fontSize: 13, color: '#64748B', marginTop: 2 },
  sectionCard: {
    backgroundColor: '#F8FAFC',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    padding: 14,
    marginBottom: 12,
  },
  sectionLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: '#64748B',
    letterSpacing: 0.6,
    marginBottom: 8,
    textTransform: 'uppercase',
  },
  sectionBody: { fontSize: 14, color: '#0F172A', lineHeight: 20 },
  timelineRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
  },
  timelineDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: brand.navy,
    marginRight: 8,
  },
  timelineLabel: { fontSize: 13, color: '#475569', flex: 1 },
  timelineValue: { fontSize: 13, fontWeight: '600', color: '#0F172A' },
  actionsCard: {
    backgroundColor: '#F8FAFC',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    padding: 14,
    marginBottom: 12,
  },
  noteInput: {
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#E2E8F0',
    borderRadius: 10,
    padding: 10,
    minHeight: 70,
    fontSize: 14,
    color: '#0F172A',
    textAlignVertical: 'top',
  },
});
