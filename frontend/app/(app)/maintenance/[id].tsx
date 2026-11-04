import React, { useState } from 'react';
import {
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { Stack, useLocalSearchParams, useRouter } from 'expo-router';
import { Pencil, Trash2, Wrench } from 'lucide-react-native';
import {
  useDeleteMaintenanceRecord,
  useMaintenanceRecord,
  useUpdateMaintenanceRecord,
} from '@/lib/queries-finances';
import { useBranches, useVehicles } from '@/lib/queries';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { Modal } from '@/components/ui/Modal';
import { Field } from '@/components/ui/Field';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { useToast } from '@/components/ui/Toast';
import { useAuth } from '@/lib/auth-context';
import { canAccess } from '@/lib/rbac';
import { formatNGN } from '@/lib/format';
import {
  MAINTENANCE_STATUSES,
  MAINTENANCE_TYPES,
  type MaintenanceStatus,
  type MaintenanceType,
  type Role,
} from '@/lib/types';

const EDIT_ROLES: Role[] = [
  'super_admin', 'owner', 'general_manager', 'branch_manager', 'fleet_manager',
];

const STATUS_TONE: Record<string, 'success' | 'info' | 'warning' | 'neutral' | 'danger'> = {
  scheduled: 'info',
  in_progress: 'warning',
  completed: 'success',
  cancelled: 'neutral',
};

export default function MaintenanceDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const toast = useToast();
  const { user } = useAuth();

  const recordQ = useMaintenanceRecord(id ?? '');
  const update = useUpdateMaintenanceRecord(id ?? '');
  const remove = useDeleteMaintenanceRecord();
  const vehiclesQ = useVehicles({ page: 1, page_size: 200 });
  const branchesQ = useBranches({ page: 1, page_size: 100 });

  const [editOpen, setEditOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [status, setStatus] = useState<MaintenanceStatus>('scheduled');
  const [type, setType] = useState<MaintenanceType>('routine');
  const [costParts, setCostParts] = useState('');
  const [costLabor, setCostLabor] = useState('');
  const [vendor, setVendor] = useState('');
  const [notes, setNotes] = useState('');

  const record = recordQ.data;

  const openEdit = () => {
    if (!record) return;
    setTitle(record.title ?? '');
    setStatus(record.status ?? 'scheduled');
    setType(record.type ?? 'routine');
    setCostParts(String(record.cost_parts ?? 0));
    setCostLabor(String(record.cost_labor ?? 0));
    setVendor(record.vendor_name ?? '');
    setNotes(record.notes ?? '');
    setEditOpen(true);
  };

  const onSave = async () => {
    if (title.trim().length < 2) return toast.error('Give the job a short title');
    const parts = parseFloat(costParts) || 0;
    const labor = parseFloat(costLabor) || 0;
    if (parts < 0 || labor < 0) return toast.error('Costs must be ≥ 0');
    try {
      await update.mutateAsync({
        title: title.trim(),
        status,
        type,
        cost_parts: parts,
        cost_labor: labor,
        cost_total: Math.round((parts + labor) * 100) / 100,
        vendor_name: vendor.trim() || null,
        notes: notes.trim() || null,
      });
      toast.success('Maintenance updated');
      setEditOpen(false);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not update the record');
    }
  };

  const onDelete = () => {
    Alert.alert(
      'Delete maintenance record?',
      'This removes the record and any upcoming-service alerts it produced.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await remove.mutateAsync(id);
              toast.success('Record deleted');
              router.back();
            } catch (e: any) {
              toast.error(e?.response?.data?.detail ?? 'Could not delete the record');
            }
          },
        },
      ],
    );
  };

  if (recordQ.isLoading) {
    return (
      <>
        <Stack.Screen options={{ title: 'Maintenance' }} />
        <View style={s.loading}><Spinner label="Loading record…" /></View>
      </>
    );
  }

  if (!record) {
    return (
      <>
        <Stack.Screen options={{ title: 'Maintenance' }} />
        <View style={s.loading}><Text style={s.errorText}>Record not found</Text></View>
      </>
    );
  }

  const vehicle = vehiclesQ.data?.items.find((v) => v.id === record.vehicle_id);
  const branch = branchesQ.data?.items.find((b) => b.id === record.branch_id);
  const canEdit = canAccess(user?.role, EDIT_ROLES);

  return (
    <>
      <Stack.Screen options={{ title: 'Maintenance' }} />
      <ScrollView style={s.root} contentContainerStyle={{ padding: 16, paddingBottom: 60 }}>
        <Card>
          <View style={s.hero}>
            <View style={s.iconBox}><Wrench size={20} color="#0B3D91" /></View>
            <View style={{ flex: 1 }}>
              <Text style={s.heroTitle}>{record.title}</Text>
              <Text style={s.heroSub}>{vehicle?.reg_number ?? record.vehicle_id} · {record.type}</Text>
            </View>
            <Badge
              label={record.status.replace(/_/g, ' ')}
              tone={STATUS_TONE[record.status] ?? 'neutral'}
            />
          </View>
        </Card>

        <View style={{ height: 12 }} />
        <Card>
          <Row label="Type" value={record.type.replace(/_/g, ' ')} />
          <Row label="Branch" value={branch?.name ?? record.branch_id} />
          {record.scheduled_for ? <Row label="Scheduled" value={new Date(record.scheduled_for).toLocaleString()} /> : null}
          {record.started_at ? <Row label="Started" value={new Date(record.started_at).toLocaleString()} /> : null}
          {record.completed_at ? <Row label="Completed" value={new Date(record.completed_at).toLocaleString()} /> : null}
          {record.odometer_km != null ? <Row label="Odometer" value={`${record.odometer_km} km`} /> : null}
          {record.next_due_km != null ? <Row label="Next due" value={`${record.next_due_km} km`} /> : null}
          {record.next_due_date ? <Row label="Next due date" value={new Date(record.next_due_date).toLocaleDateString()} /> : null}
          {record.vendor_name ? <Row label="Vendor" value={record.vendor_name} /> : null}
          {record.description ? <Row label="Description" value={record.description} /> : null}
          {record.notes ? <Row label="Notes" value={record.notes} /> : null}
        </Card>

        <View style={{ height: 12 }} />
        <Card>
          <Row label="Parts" value={formatNGN(record.cost_parts ?? 0)} />
          <Row label="Labour" value={formatNGN(record.cost_labor ?? 0)} />
          <Row label="Total" value={formatNGN(record.cost_total ?? 0)} />
        </Card>

        {canEdit ? (
          <>
            <View style={{ height: 16 }} />
            <View style={s.actions}>
              <Pressable style={s.action} onPress={openEdit} accessibilityRole="button">
                <Pencil size={16} color="#0B3D91" />
                <Text style={s.actionText}>Edit</Text>
              </Pressable>
              <Pressable style={[s.action, s.actionDanger]} onPress={onDelete} accessibilityRole="button">
                <Trash2 size={16} color="#B91C1C" />
                <Text style={[s.actionText, { color: '#B91C1C' }]}>Delete</Text>
              </Pressable>
            </View>
          </>
        ) : null}
      </ScrollView>

      <Modal visible={editOpen} onClose={() => setEditOpen(false)} title="Edit maintenance" variant="sheet">
        <Field label="Title" required>
          <TextInput style={s.input} value={title} onChangeText={setTitle} placeholder="e.g. Brake service" placeholderTextColor="#94A3B8" />
        </Field>
        <Field label="Status" required>
          <Select
            value={status}
            onChange={setStatus}
            options={MAINTENANCE_STATUSES.map((v) => ({ label: v.replace(/_/g, ' '), value: v }))}
            placeholder="Select status"
          />
        </Field>
        <Field label="Type" required>
          <Select
            value={type}
            onChange={setType}
            options={MAINTENANCE_TYPES.map((v) => ({ label: v.replace(/_/g, ' '), value: v }))}
            placeholder="Select type"
          />
        </Field>
        <Field label="Parts (₦)">
          <TextInput style={s.input} value={costParts} onChangeText={setCostParts} keyboardType="decimal-pad" placeholder="0" placeholderTextColor="#94A3B8" />
        </Field>
        <Field label="Labour (₦)">
          <TextInput style={s.input} value={costLabor} onChangeText={setCostLabor} keyboardType="decimal-pad" placeholder="0" placeholderTextColor="#94A3B8" />
        </Field>
        <Field label="Vendor">
          <TextInput style={s.input} value={vendor} onChangeText={setVendor} placeholder="optional" placeholderTextColor="#94A3B8" />
        </Field>
        <Field label="Notes">
          <TextInput style={s.input} value={notes} onChangeText={setNotes} placeholder="optional" placeholderTextColor="#94A3B8" />
        </Field>
        <View style={{ height: 12 }} />
        <Button label="Save changes" onPress={onSave} loading={update.isPending} fullWidth />
        <View style={{ height: 8 }} />
        <Button label="Cancel" onPress={() => setEditOpen(false)} variant="ghost" fullWidth />
      </Modal>
    </>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={s.row}>
      <Text style={s.rowLabel}>{label}</Text>
      <Text style={s.rowValue} numberOfLines={3}>{value}</Text>
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
  heroSub: { fontSize: 13, color: '#64748B', marginTop: 2 },
  row: { flexDirection: 'row', alignItems: 'flex-start', paddingVertical: 7 },
  rowLabel: { fontSize: 13, color: '#64748B', width: 104 },
  rowValue: { fontSize: 13, fontWeight: '500', color: '#0F172A', flex: 1 },
  actions: { flexDirection: 'row', gap: 12 },
  action: {
    flex: 1,
    height: 46,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#0B3D91',
    backgroundColor: '#FFFFFF',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  actionDanger: { borderColor: '#FECACA' },
  actionText: { fontWeight: '700', fontSize: 14, color: '#0B3D91', marginLeft: 8 },
  input: { height: 48, paddingHorizontal: 12, borderRadius: 12, borderWidth: 1, borderColor: '#E2E8F0', backgroundColor: '#FFFFFF', fontSize: 16, color: '#0F172A' },
});
