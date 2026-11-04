import React, { useState } from 'react';
import {
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { Stack, useLocalSearchParams } from 'expo-router';
import { CheckCircle2, Send, Wallet, XCircle } from 'lucide-react-native';
import {
  isSettlementEditable,
  SETTLEMENT_STATUS_LABELS,
  useSettlement,
  useSettlementAction,
  useUpdateSettlement,
} from '@/lib/queries-settlements';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { Button } from '@/components/ui/Button';
import { Field } from '@/components/ui/Field';
import { Modal } from '@/components/ui/Modal';
import { useToast } from '@/components/ui/Toast';
import { useAuth } from '@/lib/auth-context';
import { canAccess } from '@/lib/rbac';
import { formatNGN } from '@/lib/format';
import type { Role } from '@/lib/types';

const REVIEW_ROLES: Role[] = ['super_admin', 'owner', 'general_manager', 'chief_accountant'];
const EDIT_ROLES: Role[] = ['super_admin', 'owner', 'general_manager', 'chief_accountant', 'branch_accountant'];

const STATUS_TONE: Record<string, 'neutral' | 'info' | 'success' | 'warning' | 'danger'> = {
  draft: 'neutral',
  submitted: 'info',
  approved: 'success',
  paid: 'success',
  rejected: 'danger',
};

export default function SettlementDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const toast = useToast();
  const { user } = useAuth();

  const settlementQ = useSettlement(id ?? '');
  const update = useUpdateSettlement(id ?? '');
  const action = useSettlementAction(id ?? '');

  const [rateOpen, setRateOpen] = useState(false);
  const [driverRate, setDriverRate] = useState('');
  const [conductorRate, setConductorRate] = useState('');
  const [notes, setNotes] = useState('');
  const [rejectOpen, setRejectOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [payOpen, setPayOpen] = useState(false);
  const [payRef, setPayRef] = useState('');

  const settlement = settlementQ.data;

  const runAction = async (
    kind: 'submit' | 'approve' | 'reject' | 'pay',
    body?: Record<string, unknown>
  ) => {
    try {
      await action.mutateAsync({ action: kind, body });
      toast.success(
        kind === 'submit'
          ? 'Settlement submitted for review'
          : kind === 'approve'
          ? 'Settlement approved'
          : kind === 'reject'
          ? 'Settlement sent back'
          : 'Settlement marked as paid'
      );
      setRejectOpen(false);
      setPayOpen(false);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not update the settlement');
    }
  };

  const onConfirmReject = () => {
    Alert.alert(
      'Send this settlement back?',
      'It becomes editable again and the reason is recorded in the audit log.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Send back',
          style: 'destructive',
          onPress: () => runAction('reject', { reason: rejectReason.trim() || undefined }),
        },
      ],
    );
  };

  if (settlementQ.isLoading) {
    return (
      <>
        <Stack.Screen options={{ title: 'Settlement' }} />
        <View style={s.loading}><Spinner label="Loading settlement…" /></View>
      </>
    );
  }

  if (!settlement) {
    return (
      <>
        <Stack.Screen options={{ title: 'Settlement' }} />
        <View style={s.loading}><Text style={s.errorText}>Settlement not found</Text></View>
      </>
    );
  }

  const editable = isSettlementEditable(settlement.status);
  const canReview = canAccess(user?.role, REVIEW_ROLES);
  const canEdit = canAccess(user?.role, EDIT_ROLES);

  return (
    <>
      <Stack.Screen options={{ title: 'Settlement' }} />
      <ScrollView style={s.root} contentContainerStyle={{ padding: 16, paddingBottom: 60 }}>
        <Card>
          <View style={s.hero}>
            <View style={s.iconBox}><Wallet size={20} color="#0B3D91" /></View>
            <View style={{ flex: 1 }}>
              <Text style={s.heroTitle}>{settlement.branch_name ?? settlement.branch_id}</Text>
              <Text style={s.heroSub}>
                {new Date(settlement.period_start).toLocaleDateString()} –{' '}
                {new Date(settlement.period_end).toLocaleDateString()}
              </Text>
            </View>
            <Badge
              label={SETTLEMENT_STATUS_LABELS[settlement.status] ?? settlement.status}
              tone={STATUS_TONE[settlement.status] ?? 'neutral'}
            />
          </View>
          <View style={s.netBox}>
            <Text style={s.netLabel}>NET PAYABLE</Text>
            <Text style={s.netValue}>{formatNGN(settlement.net_payable)}</Text>
          </View>
        </Card>

        <View style={{ height: 12 }} />
        <Card>
          <Row label="Gross revenue" value={formatNGN(settlement.gross_revenue)} />
          <Row label="Trip expenses" value={`- ${formatNGN(settlement.trip_expenses)}`} />
          <Row label="Standalone expenses" value={`- ${formatNGN(settlement.standalone_expenses)}`} />
          <Row label="Driver payroll" value={`- ${formatNGN(settlement.driver_payroll)}`} />
          <Row label="Conductor payroll" value={`- ${formatNGN(settlement.conductor_payroll)}`} />
          <View style={s.divider} />
          <Row label="Trips settled" value={String(settlement.trip_count)} />
          <Row label="Driver rate / trip" value={formatNGN(settlement.driver_rate)} />
          <Row label="Conductor rate / trip" value={formatNGN(settlement.conductor_rate)} />
          {settlement.submitted_at ? <Row label="Submitted" value={new Date(settlement.submitted_at).toLocaleString()} /> : null}
          {settlement.approved_at ? <Row label="Approved" value={new Date(settlement.approved_at).toLocaleString()} /> : null}
          {settlement.paid_at ? <Row label="Paid" value={new Date(settlement.paid_at).toLocaleString()} /> : null}
          {settlement.payment_reference ? <Row label="Reference" value={settlement.payment_reference} /> : null}
          {settlement.rejection_reason ? <Row label="Reason" value={settlement.rejection_reason} /> : null}
          {settlement.notes ? <Row label="Notes" value={settlement.notes} /> : null}
        </Card>

        <View style={{ height: 12 }} />
        <Text style={s.sectionTitle}>Trips in this settlement ({settlement.lines.length})</Text>
        {settlement.lines.length === 0 ? (
          <Card>
            <Text style={s.emptyLine}>
              No completed trips fell inside this period, so the settlement is empty.
            </Text>
          </Card>
        ) : (
          settlement.lines.map((line) => (
            <Card key={line.trip_id} padding="sm">
              <View style={s.row}>
                <View style={s.body}>
                  <Text style={s.lineTitle}>{line.route_name ?? line.trip_id.slice(0, 10)}</Text>
                  <Text style={s.sub}>
                    {line.trip_date ? new Date(line.trip_date).toLocaleDateString() : '—'}
                    {line.driver_name ? ` · ${line.driver_name}` : ''}
                  </Text>
                  {line.conductor_name ? (
                    <Text style={s.sub}>Conductor: {line.conductor_name}</Text>
                  ) : null}
                </View>
                <View style={s.right}>
                  <Text style={s.lineAmount}>{formatNGN(line.gross_revenue)}</Text>
                  {line.trip_expenses > 0 ? (
                    <Text style={s.sub}>- {formatNGN(line.trip_expenses)} expenses</Text>
                  ) : null}
                  {line.driver_pay + line.conductor_pay > 0 ? (
                    <Text style={s.sub}>
                      payroll {formatNGN(line.driver_pay + line.conductor_pay)}
                    </Text>
                  ) : null}
                </View>
              </View>
            </Card>
          ))
        )}

        {editable && canEdit ? (
          <>
            <View style={{ height: 16 }} />
            <Button
              label="Edit pay rates"
              variant="outline"
              fullWidth
              onPress={() => {
                setDriverRate(String(settlement.driver_rate ?? 0));
                setConductorRate(String(settlement.conductor_rate ?? 0));
                setNotes(settlement.notes ?? '');
                setRateOpen(true);
              }}
            />
          </>
        ) : null}

        {settlement.status === 'draft' || settlement.status === 'rejected' ? (
          <>
            <View style={{ height: 8 }} />
            <Button
              label="Submit for review"
              icon={<Send size={16} color="#FFFFFF" />}
              fullWidth
              loading={action.isPending}
              onPress={() => runAction('submit')}
            />
          </>
        ) : null}

        {settlement.status === 'submitted' && canReview ? (
          <>
            <View style={{ height: 8 }} />
            <Button
              label="Approve"
              icon={<CheckCircle2 size={16} color="#FFFFFF" />}
              fullWidth
              loading={action.isPending}
              onPress={() => runAction('approve')}
            />
            <View style={{ height: 8 }} />
            <Button
              label="Send back"
              icon={<XCircle size={16} color="#B91C1C" />}
              variant="outline"
              fullWidth
              onPress={() => setRejectOpen(true)}
            />
          </>
        ) : null}

        {settlement.status === 'approved' && canReview ? (
          <>
            <View style={{ height: 8 }} />
            <Button
              label="Mark as paid"
              icon={<Wallet size={16} color="#FFFFFF" />}
              fullWidth
              loading={action.isPending}
              onPress={() => setPayOpen(true)}
            />
          </>
        ) : null}

        {!editable ? (
          <Text style={s.lockNote}>
            This settlement is {SETTLEMENT_STATUS_LABELS[settlement.status]?.toLowerCase()} and can no
            longer be changed.
          </Text>
        ) : null}
      </ScrollView>

      <Modal visible={rateOpen} onClose={() => setRateOpen(false)} title="Edit pay rates" variant="sheet">
        <Field label="Driver pay per trip (₦)">
          <TextInput style={s.input} value={driverRate} onChangeText={setDriverRate} keyboardType="decimal-pad" placeholder="0" placeholderTextColor="#94A3B8" />
        </Field>
        <Field label="Conductor pay per trip (₦)">
          <TextInput style={s.input} value={conductorRate} onChangeText={setConductorRate} keyboardType="decimal-pad" placeholder="0" placeholderTextColor="#94A3B8" />
        </Field>
        <Field label="Notes">
          <TextInput style={s.input} value={notes} onChangeText={setNotes} placeholder="optional" placeholderTextColor="#94A3B8" />
        </Field>
        <View style={{ height: 12 }} />
        <Button
          label="Save"
          fullWidth
          loading={update.isPending}
          onPress={async () => {
            try {
              await update.mutateAsync({
                driver_rate: parseFloat(driverRate) || 0,
                conductor_rate: parseFloat(conductorRate) || 0,
                notes: notes.trim() || null,
              });
              toast.success('Pay rates updated');
              setRateOpen(false);
            } catch (e: any) {
              toast.error(e?.response?.data?.detail ?? 'Could not update the rates');
            }
          }}
        />
        <View style={{ height: 8 }} />
        <Button label="Cancel" onPress={() => setRateOpen(false)} variant="ghost" fullWidth />
      </Modal>

      <Modal visible={rejectOpen} onClose={() => setRejectOpen(false)} title="Send back" variant="sheet">
        <Field label="Reason" helperText="Why does this need to change?">
          <TextInput
            style={s.input}
            value={rejectReason}
            onChangeText={setRejectReason}
            placeholder="optional"
            placeholderTextColor="#94A3B8"
            multiline
          />
        </Field>
        <View style={{ height: 12 }} />
        <Button label="Send back" variant="danger" fullWidth onPress={onConfirmReject} />
        <View style={{ height: 8 }} />
        <Button label="Cancel" onPress={() => setRejectOpen(false)} variant="ghost" fullWidth />
      </Modal>

      <Modal visible={payOpen} onClose={() => setPayOpen(false)} title="Mark as paid" variant="sheet">
        <Field label="Payment reference" helperText="Transfer reference, cheque number…">
          <TextInput
            style={s.input}
            value={payRef}
            onChangeText={setPayRef}
            placeholder="optional"
            placeholderTextColor="#94A3B8"
            autoCapitalize="characters"
          />
        </Field>
        <View style={{ height: 12 }} />
        <Button
          label="Confirm payment"
          fullWidth
          loading={action.isPending}
          onPress={() => runAction('pay', { payment_reference: payRef.trim() || undefined })}
        />
        <View style={{ height: 8 }} />
        <Button label="Cancel" onPress={() => setPayOpen(false)} variant="ghost" fullWidth />
      </Modal>
    </>
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

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F4F4F2' },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  errorText: { fontSize: 16, color: '#B91C1C' },
  hero: { flexDirection: 'row', alignItems: 'center' },
  iconBox: { width: 44, height: 44, borderRadius: 12, backgroundColor: '#DBEAFE', alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  heroTitle: { fontSize: 17, fontWeight: '800', color: '#0F172A' },
  heroSub: { fontSize: 12, color: '#64748B', marginTop: 2 },
  netBox: { marginTop: 14, paddingTop: 12, borderTopWidth: 1, borderTopColor: '#E2E8F0' },
  netLabel: { fontSize: 10.5, fontWeight: '700', color: '#94A3B8', letterSpacing: 0.6 },
  netValue: { fontSize: 26, fontWeight: '800', color: '#047857', marginTop: 2 },
  row: { flexDirection: 'row', alignItems: 'flex-start', paddingVertical: 6 },
  rowLabel: { fontSize: 13, color: '#64748B', width: 140 },
  rowValue: { fontSize: 13, fontWeight: '600', color: '#0F172A', flex: 1, textAlign: 'right' },
  divider: { height: 1, backgroundColor: '#E2E8F0', marginVertical: 8 },
  sectionTitle: { fontSize: 12, fontWeight: '700', color: '#64748B', letterSpacing: 0.6, textTransform: 'uppercase', marginBottom: 8 },
  emptyLine: { fontSize: 13, color: '#64748B', lineHeight: 19 },
  body: { flex: 1 },
  right: { alignItems: 'flex-end' },
  lineTitle: { fontSize: 14, fontWeight: '700', color: '#171717' },
  lineAmount: { fontSize: 14, fontWeight: '800', color: '#0F172A' },
  sub: { fontSize: 12, color: '#737373', marginTop: 2 },
  lockNote: { fontSize: 12, color: '#94A3B8', textAlign: 'center', marginTop: 16, fontStyle: 'italic' },
  input: { minHeight: 48, paddingHorizontal: 12, paddingVertical: 11, borderRadius: 12, borderWidth: 1, borderColor: '#E2E8F0', backgroundColor: '#FFFFFF', fontSize: 16, color: '#0F172A', textAlignVertical: 'top' },
});
