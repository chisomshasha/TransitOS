import React, { useState } from 'react';
import { Alert, FlatList, Pressable, RefreshControl, StyleSheet, Text, TextInput, View } from 'react-native';
import { useRouter } from 'expo-router';
import { Banknote, ChevronRight, FileDown } from 'lucide-react-native';
import * as Print from 'expo-print';
import * as Sharing from 'expo-sharing';
import * as FileSystem from 'expo-file-system/legacy';
import { useAuth } from '@/lib/auth-context';
import { canAccess } from '@/lib/rbac';
import { useApproveCashUp, useCashUps, useConductor, useRejectCashUp, useTrip } from '@/lib/queries';
import { Card } from '@/components/ui/Card';
import { Badge, type BadgeTone } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { EmptyState } from '@/components/ui/EmptyState';
import { PageHeader } from '@/components/ui/PageHeader';
import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { Field } from '@/components/ui/Field';
import { useToast } from '@/components/ui/Toast';
import { formatNGN } from '@/lib/format';
import { api } from '@/lib/api';
import type { CashUp, CashUpStatus, Role } from '@/lib/types';

const STATUS_FILTERS: Array<{ key: CashUpStatus | 'all'; label: string }> = [
  { key: 'all', label: 'All' },
  { key: 'submitted', label: 'Awaiting approval' },
  { key: 'approved', label: 'Approved' },
  { key: 'rejected', label: 'Rejected' },
  { key: 'draft', label: 'Draft' },
];

const STATUS_TONE: Record<CashUpStatus, BadgeTone> = {
  draft: 'neutral', submitted: 'warning', approved: 'success', rejected: 'danger',
};

const CASHUP_APPROVE_ROLES: Role[] = [
  'super_admin', 'owner', 'general_manager', 'chief_accountant', 'branch_accountant',
];

export default function CashUpsScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const toast = useToast();
  const [statusFilter, setStatusFilter] = useState<CashUpStatus | 'all'>('submitted');
  const [reviewing, setReviewing] = useState<CashUp | null>(null);
  const params: Record<string, unknown> = { page: 1, page_size: 100 };
  if (statusFilter !== 'all') params.status = statusFilter;
  const { data, isLoading, isFetching, refetch } = useCashUps(params);
  const items = data?.items ?? [];
  const canApprove = canAccess(user?.role, CASHUP_APPROVE_ROLES);

  const onExportPdf = async (c: CashUp) => {
    try {
      const resp = await api.get(`/cash-ups/${c.id}/pdf`, { responseType: 'arraybuffer' });
      const bytes = new Uint8Array(resp.data as ArrayBuffer);
      let binary = '';
      for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
      const base64 = btoa(binary);
      const fileUri = `${FileSystem.cacheDirectory}cashup-${c.id.slice(0, 8)}.pdf`;
      await FileSystem.writeAsStringAsync(fileUri, base64, { encoding: FileSystem.EncodingType.Base64 });
      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(fileUri, { mimeType: 'application/pdf' });
      } else {
        await Print.printAsync({ uri: fileUri });
      }
    } catch (e: any) {
      toast.error('Could not export PDF');
    }
  };

  return (
    <View style={s.root}>
      <View style={s.headerWrap}>
        <PageHeader title="Cash-ups" subtitle={`${data?.total ?? 0} total`} />
        <View style={s.chipRow}>
          {STATUS_FILTERS.map((f) => (
            <Pressable
              key={f.key}
              onPress={() => setStatusFilter(f.key)}
              style={[s.chip, statusFilter === f.key && s.chipActive]}
            >
              <Text style={[s.chipText, statusFilter === f.key && s.chipTextActive]}>{f.label}</Text>
            </Pressable>
          ))}
        </View>
      </View>
      {isLoading ? (
        <View style={s.loading}><Spinner label="Loading cash-ups…" /></View>
      ) : items.length === 0 ? (
        <EmptyState
          title="Nothing here"
          description={
            statusFilter === 'submitted'
              ? 'No cash-ups are waiting for approval right now.'
              : 'No cash-ups match this filter.'
          }
        />
      ) : (
        <FlatList
          data={items}
          keyExtractor={(c) => c.id}
          contentContainerStyle={{ padding: 16 }}
          ItemSeparatorComponent={() => <View style={{ height: 12 }} />}
          refreshControl={<RefreshControl refreshing={isFetching && !isLoading} onRefresh={refetch} />}
          renderItem={({ item }) => (
            <CashUpRow
              item={item}
              onPress={() =>
                canApprove && item.status === 'submitted'
                  ? setReviewing(item)
                  : router.push(`/trips/${item.trip_id}` as never)
              }
              onExport={() => onExportPdf(item)}
            />
          )}
        />
      )}
      <ReviewModal cashUp={reviewing} onClose={() => setReviewing(null)} onDone={refetch} />
    </View>
  );
}

function CashUpRow({ item, onPress, onExport }: { item: CashUp; onPress: () => void; onExport: () => void }) {
  const { data: trip } = useTrip(item.trip_id);
  const { data: conductor } = useConductor(item.conductor_id);
  const varColor = item.variance < 0 ? '#B91C1C' : item.variance > 0 ? '#B45309' : '#047857';
  const varBg = item.variance < 0 ? '#FEF2F2' : item.variance > 0 ? '#FFFBEB' : '#ECFDF5';

  return (
    <Pressable onPress={onPress} accessibilityRole="button">
      <View style={s.card}>
        <View style={s.row1}>
          <View style={s.iconBox}><Banknote size={18} color="#047857" /></View>
          <View style={{ flex: 1 }}>
            <Text style={s.name} numberOfLines={1}>{conductor?.full_name ?? 'Conductor'}</Text>
            <Text style={s.sub}>
              {trip
                ? new Date(trip.scheduled_departure).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
                : 'Loading trip…'}
            </Text>
          </View>
          <Badge label={item.status} tone={STATUS_TONE[item.status]} size="sm" />
        </View>

        <View style={s.row2}>
          <View style={{ flex: 1 }}>
            <Text style={s.kpiLabel}>Expected</Text>
            <Text style={s.kpiValue}>{formatNGN(item.expected_total)}</Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text style={s.kpiLabel}>Declared</Text>
            <Text style={[s.kpiValue, { color: '#0B3D91', fontWeight: '700' }]}>{formatNGN(item.declared_total)}</Text>
          </View>
          {item.status !== 'draft' ? (
            <View style={[s.varBox, { backgroundColor: varBg }]}>
              <Text style={[s.varLabel, { color: varColor }]}>Variance</Text>
              <Text style={[s.varValue, { color: varColor }]}>
                {item.variance >= 0 ? '+' : ''}{formatNGN(item.variance)}
              </Text>
            </View>
          ) : null}
        </View>

        <Pressable style={s.exportRow} onPress={onExport}>
          <FileDown size={14} color="#0B3D91" />
          <Text style={s.exportText}>Export PDF</Text>
        </Pressable>

        <View style={s.chevWrap}><ChevronRight size={16} color="#CBD5E1" /></View>
      </View>
    </Pressable>
  );
}

function ReviewModal({ cashUp, onClose, onDone }: { cashUp: CashUp | null; onClose: () => void; onDone: () => void }) {
  const approve = useApproveCashUp(cashUp?.id ?? '');
  const reject = useRejectCashUp(cashUp?.id ?? '');
  const toast = useToast();
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState('');
  if (!cashUp) return null;

  const onApprove = async () => {
    try {
      await approve.mutateAsync({});
      toast.success('Cash-up approved');
      setRejecting(false);
      onClose();
      onDone();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not approve');
    }
  };

  const onReject = async () => {
    if (reason.trim().length < 2) return toast.error('Give a reason for the conductor');
    try {
      await reject.mutateAsync(reason.trim());
      toast.success('Cash-up rejected');
      setRejecting(false);
      setReason('');
      onClose();
      onDone();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not reject');
    }
  };

  return (
    <Modal visible={!!cashUp} onClose={onClose} title="Review cash-up" variant="sheet">
      <View style={s.reviewBox}>
        <View style={s.reviewRow}>
          <Text style={s.reviewLabel}>Declared</Text>
          <Text style={s.reviewValue}>{formatNGN(cashUp.declared_total)}</Text>
        </View>
        <View style={s.reviewRow}>
          <Text style={s.reviewLabelSub}>Expected</Text>
          <Text style={s.reviewValueSub}>{formatNGN(cashUp.expected_total)}</Text>
        </View>
        <View style={s.reviewRow}>
          <Text style={s.reviewLabelSub}>Variance</Text>
          <Text style={[s.reviewValueSub, { color: cashUp.variance < 0 ? '#B91C1C' : cashUp.variance > 0 ? '#B45309' : '#047857', fontWeight: '700' }]}>
            {cashUp.variance >= 0 ? '+' : ''}{formatNGN(cashUp.variance)}
          </Text>
        </View>
      </View>

      {cashUp.breakdown.length > 0 ? (
        <View style={{ marginBottom: 12 }}>
          <Text style={s.sectionLabel}>Breakdown</Text>
          {cashUp.breakdown.map((b, i) => (
            <View key={i} style={s.bdRow}>
              <Text style={s.bdMethod}>{b.method}</Text>
              <Text style={s.bdAmount}>{formatNGN(b.amount)}</Text>
            </View>
          ))}
        </View>
      ) : null}

      {cashUp.notes ? (
        <View style={{ marginBottom: 12 }}>
          <Text style={s.sectionLabel}>Notes</Text>
          <Text style={s.notesText}>{cashUp.notes}</Text>
        </View>
      ) : null}

      {rejecting ? (
        <>
          <Field label="Reason for rejection" required>
            <TextInput
              style={s.reasonInput}
              value={reason}
              onChangeText={setReason}
              placeholder="e.g. Declared amount doesn't match the manifest"
              multiline
            />
          </Field>
          <Button label="Confirm rejection" variant="danger" fullWidth onPress={onReject} loading={reject.isPending} />
          <View style={{ height: 8 }} />
          <Button label="Cancel" variant="ghost" fullWidth onPress={() => setRejecting(false)} />
        </>
      ) : (
        <>
          <Button label="Approve" onPress={onApprove} loading={approve.isPending} fullWidth />
          <View style={{ height: 8 }} />
          <Button label="Reject" variant="danger" fullWidth onPress={() => setRejecting(true)} />
        </>
      )}
    </Modal>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F8F7F4' },
  headerWrap: { paddingHorizontal: 16, paddingTop: 8, paddingBottom: 12, backgroundColor: '#FFFFFF', borderBottomWidth: 1, borderBottomColor: '#E5E5E5' },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', marginTop: 8 },
  chip: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 9999, marginRight: 6, marginBottom: 6, backgroundColor: '#FFFFFF', borderWidth: 1, borderColor: '#E2E8F0' },
  chipActive: { backgroundColor: '#0B3D91', borderColor: '#0B3D91' },
  chipText: { fontSize: 12, fontWeight: '500', color: '#334155' },
  chipTextActive: { color: '#FFFFFF' },
  card: { backgroundColor: '#fff', borderRadius: 14, borderWidth: 1, borderColor: '#E2E8F0', padding: 14, overflow: 'hidden' },
  row1: { flexDirection: 'row', alignItems: 'center', marginBottom: 10 },
  iconBox: { width: 40, height: 40, borderRadius: 10, backgroundColor: '#ECFDF5', alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  name: { fontSize: 15, fontWeight: '700', color: '#0F172A' },
  sub: { fontSize: 12, color: '#64748B', marginTop: 2 },
  row2: { flexDirection: 'row', marginTop: 4 },
  kpiLabel: { fontSize: 11, color: '#64748B' },
  kpiValue: { fontSize: 14, fontWeight: '600', color: '#0F172A', marginTop: 2 },
  varBox: { flex: 1, borderRadius: 10, padding: 8, alignItems: 'center' },
  varLabel: { fontSize: 10, fontWeight: '600' },
  varValue: { fontSize: 13, fontWeight: '800', marginTop: 2 },
  exportRow: { flexDirection: 'row', alignItems: 'center', marginTop: 12, paddingVertical: 8, borderTopWidth: 1, borderTopColor: '#F1F5F9' },
  exportText: { fontSize: 13, fontWeight: '700', color: '#0B3D91', marginLeft: 6 },
  chevWrap: { position: 'absolute', right: 10, bottom: 10 },
  reviewBox: { backgroundColor: '#EFF6FF', borderRadius: 12, padding: 14, marginBottom: 14, borderWidth: 1, borderColor: '#BFDBFE' },
  reviewRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 4 },
  reviewLabel: { fontSize: 14, fontWeight: '600', color: '#0B3D91' },
  reviewValue: { fontSize: 18, fontWeight: '700', color: '#0B3D91' },
  reviewLabelSub: { fontSize: 13, color: '#64748B' },
  reviewValueSub: { fontSize: 13, fontWeight: '600', color: '#334155' },
  sectionLabel: { fontSize: 11, fontWeight: '700', color: '#64748B', textTransform: 'uppercase', letterSpacing: 0.6, marginBottom: 6 },
  bdRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4 },
  bdMethod: { fontSize: 13, color: '#334155', textTransform: 'capitalize' },
  bdAmount: { fontSize: 13, fontWeight: '600', color: '#0F172A' },
  notesText: { fontSize: 13, color: '#334155' },
  reasonInput: { height: 80, paddingHorizontal: 12, paddingVertical: 10, borderRadius: 10, borderWidth: 1, borderColor: '#E2E8F0', backgroundColor: '#FFFFFF', fontSize: 14, color: '#0F172A', marginBottom: 12 },
});
