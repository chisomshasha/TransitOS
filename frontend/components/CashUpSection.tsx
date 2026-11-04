import React, { useMemo, useState } from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';
import { Wallet } from 'lucide-react-native';
import { useCashUps, useCreateCashUp, useSubmitCashUp, useUpdateCashUp } from '@/lib/queries';
import { useAuth } from '@/lib/auth-context';
import { canAccess } from '@/lib/rbac';
import { useToast } from '@/components/ui/Toast';
import { Button } from '@/components/ui/Button';
import { Badge, type BadgeTone } from '@/components/ui/Badge';
import { formatNGN } from '@/lib/format';
import { CASH_UP_MUTATE_ROLES, CASH_UP_REQUIRES_TRIP_STATUS } from '@/lib/money-loop';
import type { CashUp, Trip } from '@/lib/types';

export interface CashUpSectionProps {
  trip: Trip;
}

const DENOMS = [1000, 500, 200, 100, 50] as const;

const CASHUP_TONE: Record<CashUp['status'], BadgeTone> = {
  draft: 'neutral',
  submitted: 'warning',
  approved: 'success',
  rejected: 'danger',
};

export function CashUpSection({ trip }: CashUpSectionProps) {
  const { user } = useAuth();
  const toast = useToast();
  const list = useCashUps({ trip_id: trip.id });
  const items = list.data?.items ?? [];
  const latest = items[0];

  const canDeclare = canAccess(user?.role, CASH_UP_MUTATE_ROLES);
  // The denomination boxes are only editable when the declaration can
  // actually be saved: a cash-up that is still a draft (or was rejected
  // and sent back), or no cash-up at all on a trip that is closed. On
  // any other trip the server would refuse the save, so the boxes are
  // shown greyed out rather than inviting a count that cannot be kept.
  const editable =
    canDeclare &&
    (latest
      ? latest.status === 'draft' || latest.status === 'rejected'
      : trip.status === CASH_UP_REQUIRES_TRIP_STATUS);

  // Denomination counting is purely a client-side convenience for
  // arriving at a cash total — the backend only stores a payment-method
  // breakdown (method/amount), not per-denomination counts, so we don't
  // try to reverse-populate these inputs from an existing cash-up.
  const [counts, setCounts] = useState<Record<number, string>>({});
  const [coins, setCoins] = useState('');

  const counted = useMemo(() => {
    let total = 0;
    DENOMS.forEach((d) => {
      const n = parseInt(counts[d] ?? '', 10) || 0;
      total += n * d;
    });
    total += parseFloat(coins || '0') || 0;
    return total;
  }, [counts, coins]);

  const expected = trip.total_revenue ?? 0;
  const variance = counted - expected;

  // Once a cash-up has been submitted the server owns the figures — it
  // recomputes the expected total and the variance from the manifest at
  // submission time, and the cash-up can no longer be edited. The
  // denomination boxes are empty by then, so the declared amount is
  // what has to be shown.
  const serverOwnsFigures = latest ? latest.status !== 'draft' && latest.status !== 'rejected' : false;
  const shownExpected = serverOwnsFigures ? latest!.expected_total : expected;
  const shownCounted = serverOwnsFigures ? latest!.declared_total : counted;
  const shownVariance = serverOwnsFigures ? latest!.variance : variance;

  return (
    <View style={s.card} testID="cash-up-section">
      <View style={s.header}>
        <Wallet size={18} color="#0E7490" />
        <Text style={s.title}>Cash-up</Text>
        {latest ? <Badge label={latest.status} tone={CASHUP_TONE[latest.status]} size="sm" /> : null}
      </View>
      <Text style={s.description}>
        Conductor declares takings by denomination. System compares against manifest revenue.
      </Text>

      {latest?.status === 'rejected' && latest.rejection_reason ? (
        <View style={s.rejected}>
          <Text style={s.rejectedTitle}>Rejected — adjust and submit again</Text>
          <Text style={s.rejectedText}>{latest.rejection_reason}</Text>
        </View>
      ) : null}

      {latest?.status === 'submitted' ? (
        <View style={s.pending}>
          <Text style={s.pendingText}>
            Submitted for approval. An accountant has to approve it before the trip can be
            marked as cashed up.
          </Text>
        </View>
      ) : null}

      {latest?.status === 'approved' ? (
        <View style={s.approved}>
          <Text style={s.approvedText}>
            Approved. The trip has been marked as cashed up.
          </Text>
        </View>
      ) : null}

      {!latest && trip.status !== CASH_UP_REQUIRES_TRIP_STATUS ? (
        <View style={s.pending}>
          <Text style={s.pendingText}>
            Cash-up can only be recorded once the trip is closed. Move the trip to
            &apos;Closed&apos; first.
          </Text>
        </View>
      ) : null}

      <View style={s.grid}>
        {DENOMS.map((d) => (
          <DenomInput
            key={d}
            label={`₦${d.toLocaleString()}`}
            value={counts[d] ?? ''}
            onChange={(v) => setCounts((p) => ({ ...p, [d]: v }))}
            editable={editable}
          />
        ))}
        <DenomInput
          label="Coins (₦)"
          value={coins}
          onChange={setCoins}
          editable={editable}
        />
      </View>

      <View style={s.summary}>
        <Row label="Expected (system)" value={formatNGN(shownExpected)} />
        <Row label="Counted (physical)" value={formatNGN(shownCounted)} />
        <View style={s.row}>
          <Text style={s.rowLabelBold}>Variance</Text>
          <Text
            style={[
              s.rowValueBold,
              { color: shownVariance >= 0 ? '#047857' : '#B91C1C' },
            ]}
          >
            {shownVariance >= 0 ? '+' : ''}
            {formatNGN(shownVariance)}
          </Text>
        </View>
        {latest && !serverOwnsFigures ? (
          <View style={s.row}>
            <Text style={s.rowLabel}>Declared</Text>
            <Text style={s.rowValue}>{formatNGN(latest.declared_total)}</Text>
          </View>
        ) : null}
      </View>

      {!canDeclare ? (
        <Text style={s.readOnly}>
          Only a conductor, accountant or manager can record a cash-up.
        </Text>
      ) : latest ? (
        <CashUpActions trip={trip} cashUp={latest} counted={counted} editable={editable} />
      ) : trip.status === CASH_UP_REQUIRES_TRIP_STATUS ? (
        <CreateCashUpButton trip={trip} counted={counted} />
      ) : null}
    </View>
  );
}

/**
 * The three actions a cash-up can take, each in its own component so
 * that the mutation hook is always created with a real id — never with
 * an empty one while the list is still loading.
 */
function CashUpActions({
  trip,
  cashUp,
  counted,
  editable,
}: {
  trip: Trip;
  cashUp: CashUp;
  counted: number;
  editable: boolean;
}) {
  const toast = useToast();
  const update = useUpdateCashUp(cashUp.id);
  const submit = useSubmitCashUp(cashUp.id);

  const onUpdate = async () => {
    try {
      await update.mutateAsync({
        breakdown: [{ method: 'cash', amount: counted }],
        declared_total: counted,
      });
      toast.success('Cash-up updated');
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not update the cash-up');
    }
  };

  const onSubmit = async () => {
    try {
      await submit.mutateAsync(undefined);
      toast.success('Cash-up submitted for approval');
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not submit the cash-up');
    }
  };

  if (!editable) {
    // Submitted or approved — the figures are locked until a rejection
    // sends it back to the conductor.
    return null;
  }

  return (
    <View style={s.buttonWrap}>
      <Button
        label={cashUp.status === 'rejected' ? 'Update cash-up' : 'Save cash-up'}
        onPress={onUpdate}
        loading={update.isPending}
        fullWidth
        testID="cash-up-save"
      />
      <View style={{ height: 8 }} />
      <SubmitCashUpButton onSubmit={onSubmit} loading={submit.isPending} />
    </View>
  );
}

function SubmitCashUpButton({ onSubmit, loading }: { onSubmit: () => void; loading: boolean }) {
  return (
    <Button
      label="Submit for approval"
      onPress={onSubmit}
      loading={loading}
      fullWidth
      testID="cash-up-submit"
    />
  );
}

function CreateCashUpButton({ trip, counted }: { trip: Trip; counted: number }) {
  const toast = useToast();
  const create = useCreateCashUp();

  const onCreate = async () => {
    try {
      await create.mutateAsync({
        trip_id: trip.id,
        conductor_id: trip.conductor_id,
        branch_id: trip.branch_id,
        breakdown: [{ method: 'cash', amount: counted }],
        declared_total: counted,
      });
      toast.success('Cash-up saved as a draft');
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not save the cash-up');
    }
  };

  return (
    <View style={s.buttonWrap}>
      <Button label="Save cash-up" onPress={onCreate} loading={create.isPending} fullWidth />
      <Text style={s.helper}>
        A cash-up is saved as a draft first. Use &apos;Submit for approval&apos; when the
        count is final.
      </Text>
    </View>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={s.row}>
      <Text style={s.rowLabel}>{label}</Text>
      <Text style={s.rowValue}>{value}</Text>
    </View>
  );
}

function DenomInput({
  label,
  value,
  onChange,
  editable,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  editable: boolean;
}) {
  return (
    <View style={s.denomWrap}>
      <Text style={s.denomLabel}>{label}</Text>
      <TextInput
        style={[s.denomInput, !editable && s.denomInputLocked]}
        value={value}
        onChangeText={onChange}
        keyboardType="numeric"
        placeholder="0"
        placeholderTextColor="#94A3B8"
        editable={editable}
        accessibilityLabel={label}
      />
    </View>
  );
}

const s = StyleSheet.create({
  card: { backgroundColor: '#FFFFFF', borderRadius: 12, borderWidth: 1, borderColor: '#E5E7EB', padding: 16 },
  header: { flexDirection: 'row', alignItems: 'center' },
  title: { flex: 1, fontSize: 16, fontWeight: '600', color: '#1E293B', marginLeft: 8 },
  description: { fontSize: 12, color: '#64748B', marginTop: 2 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', marginHorizontal: -6, marginTop: 12 },
  denomWrap: { width: '50%', paddingHorizontal: 6, marginBottom: 12 },
  denomLabel: { fontSize: 12, fontWeight: '600', color: '#475569', marginBottom: 4 },
  denomInput: { height: 44, paddingHorizontal: 12, borderRadius: 12, borderWidth: 1, borderColor: '#E2E8F0', backgroundColor: '#FFFFFF', fontSize: 16, color: '#0F172A' },
  denomInputLocked: { backgroundColor: '#F1F5F9', color: '#94A3B8' },
  summary: { backgroundColor: '#F8FAFC', borderRadius: 12, padding: 12, marginTop: 4 },
  row: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
  rowLabel: { fontSize: 14, color: '#475569' },
  rowValue: { fontSize: 14, fontWeight: '600', color: '#1E293B' },
  rowLabelBold: { fontSize: 14, fontWeight: '600', color: '#1E293B' },
  rowValueBold: { fontSize: 14, fontWeight: '700' },
  buttonWrap: { marginTop: 12 },
  helper: { fontSize: 11, color: '#64748B', marginTop: 8, lineHeight: 16 },
  readOnly: { fontSize: 12, color: '#64748B', marginTop: 10, lineHeight: 18 },
  pending: { backgroundColor: '#FFFBEB', borderRadius: 10, padding: 10, marginTop: 10, borderWidth: 1, borderColor: '#FDE68A' },
  pendingText: { fontSize: 12, color: '#92400E', lineHeight: 17 },
  rejected: { backgroundColor: '#FEF2F2', borderRadius: 10, padding: 10, marginTop: 10, borderWidth: 1, borderColor: '#FECACA' },
  rejectedTitle: { fontSize: 12, fontWeight: '700', color: '#B91C1C', marginBottom: 2 },
  rejectedText: { fontSize: 12, color: '#991B1B', lineHeight: 17 },
  approved: { backgroundColor: '#ECFDF5', borderRadius: 10, padding: 10, marginTop: 10, borderWidth: 1, borderColor: '#A7F3D0' },
  approvedText: { fontSize: 12, color: '#047857', lineHeight: 17 },
});
