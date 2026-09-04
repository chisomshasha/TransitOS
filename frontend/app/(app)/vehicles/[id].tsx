import React, { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View, TextInput, Alert } from 'react-native';
import { useRoute, useRouter } from 'expo-router';
import { Building2, Bus, CalendarDays, FileText, Fuel, Plus, QRCode, Share, Users, Wrench } from 'lucide-react-native';
import * as Print from 'expo-print';
import * as Sharing from 'expo-sharing';
import QRCode from 'react-native-qrcode-svg';
import { useBranches, useVehicles } from '@/lib/queries';
import { useVehicleDocuments, useCreateVehicleDocument, useDeleteVehicleDocument } from '@/lib/queries-p2';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { Modal } from '@/components/ui/Modal';
import { Field } from '@/components/ui/Field';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { useToast } from '@/components/ui/Toast';
import { BarCard, Chip, type SevTone } from '@/components/ui/kit';
import { brand } from '@/lib/theme';
import type { VehicleStatus } from '@/lib/types';

const STATUS_TONE: Record<string, 'success' | 'info' | 'warning' | 'neutral'> = {
  available: 'success',
  on_trip: 'info',
  maintenance: 'warning',
  inactive: 'neutral',
  grounded: 'neutral',
};

const DOC_TYPES = [
  { label: 'Insurance', value: 'insurance' },
  { label: 'Roadworthiness', value: 'roadworthiness' },
  { label: 'Hackney Permit', value: 'hackney_permit' },
  { label: 'Route Permit', value: 'route_permit' },
  { label: 'Other', value: 'other' },
];

const ALERT_DAYS = [7, 14, 30, 60, 90];

export default function VehicleDetailScreen() {
  const route = useRoute();
  const router = useRouter();
  const toast = useToast();
  const id = (route.params as { id: string })?.id;
  const { data, isLoading } = useVehicles({ page: 1, page_size: 200 });
  const branchesQ = useBranches({ page: 1, page_size: 200 });
  const docsQ = useVehicleDocuments(id);
  const createDoc = useCreateVehicleDocument();
  const deleteDoc = useDeleteVehicleDocument();
  const v = (data?.items ?? []).find((x) => x.id === id);

  const [addDocOpen, setAddDocOpen] = useState(false);
  const [qrOpen, setQrOpen] = useState(false);
  const [docType, setDocType] = useState('');
  const [issuer, setIssuer] = useState('');
  const [refNumber, setRefNumber] = useState('');
  const [expiresAt, setExpiresAt] = useState('');
  const [alertDays, setAlertDays] = useState(30);

  if (isLoading) return <View style={s.loading}><Spinner label="Loading vehicle…" /></View>;
  if (!v) return <View style={s.loading}><Text style={s.errorText}>Vehicle not found</Text></View>;

  const branchName = branchesQ.data?.items.find((b) => b.id === v.branch_id)?.name ?? '—';
  const fuelPct = typeof (v as any).current_fuel_level === 'number' ? (v as any).current_fuel_level : 0;
  const odo = typeof (v as any).current_odometer_km === 'number' ? (v as any).current_odometer_km : 0;
  const docs = docsQ.data?.items ?? [];
  const now = Date.now();

  const resetDoc = () => { setDocType(''); setIssuer(''); setRefNumber(''); setExpiresAt(''); setAlertDays(30); };
  const closeDoc = () => { resetDoc(); setAddDocOpen(false); };

  const onSubmitDoc = async () => {
    if (!docType) return toast.error('Document type is required');
    if (!refNumber.trim()) return toast.error('Reference number is required');
    if (!expiresAt.trim()) return toast.error('Expiry date is required');
    const exp = new Date(expiresAt.trim());
    if (isNaN(exp.getTime())) return toast.error('Invalid date format');
    try {
      await createDoc.mutateAsync({
        vehicleId: id,
        data: {
          doc_type: docType,
          issuer: issuer.trim() || null,
          ref_number: refNumber.trim(),
          expires_at: exp.toISOString(),
          alert_days: alertDays,
        },
      });
      toast.success('Document added');
      resetDoc();
      setAddDocOpen(false);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not add document');
    }
  };

  const onDeleteDoc = (docId: string) => {
    Alert.alert('Delete document?', 'This cannot be undone.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          try {
            await deleteDoc.mutateAsync({ vehicleId: id, docId });
            toast.success('Document deleted');
          } catch {
            toast.error('Could not delete document');
          }
        },
      },
    ]);
  };

  const onShareQR = async () => {
    try {
      const uri = `${v.reg_number}`;
      const html = `<div style="text-align:center;padding:40px;"><h1>${v.reg_number}</h1><img src="data:image/svg+xml;base64," alt="QR" /></div>`;
      await Sharing.shareAsync(uri);
    } catch {
      toast.error('Could not share QR');
    }
  };

  const onPrintQR = async () => {
    try {
      await Print.printAsync({ html: `<div style="text-align:center;padding:40px;"><h1>${v.reg_number}</h1><p>Scan to view vehicle details</p></div>` });
    } catch {
      toast.error('Could not print QR');
    }
  };

  return (
    <ScrollView style={s.root} contentContainerStyle={{ padding: 16 }}>
      <Card>
        <View style={s.header}>
          <View style={s.avatar}><Bus size={24} color="#0E7490" /></View>
          <View style={{ flex: 1 }}>
            <Text style={s.name}>{v.reg_number}</Text>
            <Text style={s.sub}>{(v as any).type ?? '—'}</Text>
          </View>
          <Badge
            label={(v as any).status}
            tone={STATUS_TONE[v.status] ?? 'neutral'}
          />
        </View>
        <View style={s.divider} />
        <InfoRow icon={<Users size={14} color="#64748B" />} label="Seats" value={String(v.capacity_seats)} />
        <InfoRow icon={<Building2 size={14} color="#64748B" />} label="Branch" value={branchName} />
        <View style={s.odoRow}>
          <View style={s.odoBox}>
            <Text style={s.odoLabel}>ODOMETER</Text>
            <Text style={s.odoValue}>{odo.toLocaleString()} km</Text>
          </View>
          <View style={s.odoBox}>
            <Text style={s.odoLabel}>FUEL</Text>
            <View style={s.fuelBarWrap}>
              <View style={[s.fuelBar, { width: `${fuelPct}%`, backgroundColor: fuelPct < 20 ? '#DC2626' : '#10B981' }]} />
            </View>
            <Text style={s.fuelText}>{fuelPct}%</Text>
          </View>
        </View>
      </Card>

      <View style={{ height: 14 }} />
      <Card>
        <View style={s.sectionHead}>
          <Text style={s.sectionTitle}>Documents</Text>
          <Pressable onPress={() => setAddDocOpen(true)} style={s.addBtn}>
            <Plus size={16} color={brand.navy} />
            <Text style={s.addText}>Add</Text>
          </Pressable>
        </View>
        {docs.length === 0 ? (
          <Text style={s.emptyText}>No documents yet. Add insurance, permits, or roadworthiness.</Text>
        ) : (
          docs.map((d) => {
            const daysLeft = Math.ceil((new Date(d.expires_at).getTime() - now) / 86400000);
            const tone: SevTone = daysLeft < 0 ? 'danger' : daysLeft <= 30 ? 'warn' : 'ok';
            const label = DOC_TYPES.find((t) => t.value === d.doc_type)?.label ?? d.doc_type;
            return (
              <BarCard key={d.id} tone={tone}>
                <View style={s.docRow}>
                  <View style={{ flex: 1 }}>
                    <Text style={s.docTitle}>{label}</Text>
                    <Text style={s.docSub}>Ref {d.ref_number}</Text>
                    <Text style={s.docExpiry}>
                      {daysLeft < 0 ? `EXPIRED ${Math.abs(daysLeft)}d ago` : daysLeft === 0 ? 'Expires today' : `Expires in ${daysLeft}d`}
                    </Text>
                  </View>
                  <Pressable onPress={() => onDeleteDoc(d.id)} hitSlop={10}>
                    <Text style={s.docDelete}>Delete</Text>
                  </Pressable>
                </View>
              </BarCard>
            );
          })
        )}
      </Card>

      <View style={{ height: 14 }} />
      <View style={s.actionGrid}>
        <Pressable style={s.actionCard} onPress={() => setQrOpen(true)}>
          <QRCode size={22} color={brand.navy} />
          <Text style={s.actionLabel}>Show QR</Text>
        </Pressable>
        <Pressable style={s.actionCard} onPress={() => router.push('/maintenance' as never)}>
          <Wrench size={22} color={brand.navy} />
          <Text style={s.actionLabel}>Maintenance</Text>
        </Pressable>
        <Pressable style={s.actionCard} onPress={() => router.push('/fuel' as never)}>
          <Fuel size={22} color={brand.navy} />
          <Text style={s.actionLabel}>Fuel logs</Text>
        </Pressable>
      </View>

      <Modal visible={addDocOpen} onClose={closeDoc} title="Add document" variant="sheet">
        <Field label="Document type" required>
          <Select value={docType} onChange={setDocType} options={DOC_TYPES} placeholder="Select type" />
        </Field>
        <Field label="Issuer">
          <TextInput style={s.input} value={issuer} onChangeText={setIssuer} placeholder="e.g. AXA Mansard" placeholderTextColor="#94A3B8" />
        </Field>
        <Field label="Reference number" required>
          <TextInput style={s.input} value={refNumber} onChangeText={setRefNumber} placeholder="Policy or cert number" placeholderTextColor="#94A3B8" />
        </Field>
        <Field label="Expiry date (YYYY-MM-DD)" required>
          <TextInput style={s.input} value={expiresAt} onChangeText={setExpiresAt} placeholder="2027-12-31" placeholderTextColor="#94A3B8" />
        </Field>
        <Field label="Alert me (days before expiry)">
          <View style={s.chipRow}>
            {ALERT_DAYS.map((d) => (
              <Chip key={d} label={`${d}d`} active={alertDays === d} onPress={() => setAlertDays(d)} />
            ))}
          </View>
        </Field>
        <View style={{ height: 12 }} />
        <Button label="Add document" onPress={onSubmitDoc} loading={createDoc.isPending} fullWidth />
        <View style={{ height: 8 }} />
        <Button label="Cancel" onPress={closeDoc} variant="ghost" fullWidth />
      </Modal>

      <Modal visible={qrOpen} onClose={() => setQrOpen(false)} title={`QR · ${v.reg_number}`}>
        <View style={s.qrWrap}>
          <QRCode value={v.reg_number} size={200} />
          <Text style={s.qrLabel}>Scan to view vehicle details</Text>
        </View>
        <View style={{ height: 12 }} />
        <View style={s.qrActions}>
          <Pressable style={s.qrBtn} onPress={onShareQR}>
            <Share size={16} color={brand.navy} />
            <Text style={s.qrBtnText}>Share</Text>
          </Pressable>
          <Pressable style={s.qrBtn} onPress={onPrintQR}>
            <FileText size={16} color={brand.navy} />
            <Text style={s.qrBtnText}>Print</Text>
          </Pressable>
        </View>
      </Modal>
    </ScrollView>
  );
}

function InfoRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <View style={s.infoRow}>
      {icon}
      <Text style={s.infoLabel}>{label}</Text>
      <Text style={s.infoValue}>{value}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F4F4F2' },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  errorText: { fontSize: 16, color: '#B91C1C' },
  header: { flexDirection: 'row', alignItems: 'center' },
  avatar: { width: 48, height: 48, borderRadius: 8, backgroundColor: '#ECFEFF', alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  name: { fontSize: 18, fontWeight: '700', color: '#171717' },
  sub: { fontSize: 13, color: '#737373', marginTop: 2 },
  divider: { height: 1, backgroundColor: '#E5E7EB', marginVertical: 16 },
  infoRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 6 },
  infoLabel: { fontSize: 13, color: '#64748B', width: 110, marginLeft: 8 },
  infoValue: { fontSize: 13, fontWeight: '500', color: '#171717', flex: 1 },
  odoRow: { flexDirection: 'row', marginTop: 12 },
  odoBox: { flex: 1, marginRight: 8 },
  odoLabel: { fontSize: 11, color: '#64748B', fontWeight: '600', marginBottom: 4 },
  odoValue: { fontSize: 18, fontWeight: '700', color: '#0F172A' },
  fuelBarWrap: { height: 8, backgroundColor: '#E2E8F0', borderRadius: 4, marginTop: 6 },
  fuelBar: { height: 8, borderRadius: 4 },
  fuelText: { fontSize: 13, color: '#475569', marginTop: 4 },
  sectionHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  sectionTitle: { fontSize: 17, fontWeight: '700', color: '#0F172A' },
  addBtn: { flexDirection: 'row', alignItems: 'center' },
  addText: { fontSize: 13, fontWeight: '600', color: brand.navy, marginLeft: 4 },
  emptyText: { color: '#64748B', fontSize: 13, lineHeight: 19 },
  docRow: { flexDirection: 'row', alignItems: 'center' },
  docTitle: { fontSize: 15, fontWeight: '700', color: '#0F172A' },
  docSub: { fontSize: 12, color: '#64748B', marginTop: 2 },
  docExpiry: { fontSize: 12, fontWeight: '600', color: '#B45309', marginTop: 4 },
  docDelete: { fontSize: 13, color: '#B91C1C', fontWeight: '600' },
  actionGrid: { flexDirection: 'row', justifyContent: 'space-around' },
  actionCard: { alignItems: 'center', padding: 14 },
  actionLabel: { fontSize: 12, color: brand.navy, fontWeight: '600', marginTop: 6 },
  input: { height: 48, paddingHorizontal: 12, borderRadius: 12, borderWidth: 1, borderColor: '#E2E8F0', backgroundColor: '#FFFFFF', fontSize: 16, color: '#0F172A' },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap' },
  qrWrap: { alignItems: 'center', padding: 20 },
  qrLabel: { fontSize: 13, color: '#64748B', marginTop: 12 },
  qrActions: { flexDirection: 'row', justifyContent: 'space-around' },
  qrBtn: { flexDirection: 'row', alignItems: 'center', padding: 12 },
  qrBtnText: { fontSize: 14, fontWeight: '600', color: brand.navy, marginLeft: 6 },
});
