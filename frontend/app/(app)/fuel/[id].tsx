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
import { Fuel as FuelIcon, Pencil, Trash2 } from 'lucide-react-native';
import {
  useDeleteFuelLog,
  useFuelLog,
  useUpdateFuelLog,
} from '@/lib/queries-finances';
import { useBranches, useVehicles } from '@/lib/queries';
import { Card } from '@/components/ui/Card';
import { Spinner } from '@/components/ui/Spinner';
import { Modal } from '@/components/ui/Modal';
import { Field } from '@/components/ui/Field';
import { Button } from '@/components/ui/Button';
import { useToast } from '@/components/ui/Toast';
import { useAuth } from '@/lib/auth-context';
import { canAccess } from '@/lib/rbac';
import { formatNGN } from '@/lib/format';
import type { Role } from '@/lib/types';

const EDIT_ROLES: Role[] = [
  'super_admin', 'owner', 'general_manager', 'branch_manager', 'fleet_manager',
];

export default function FuelLogDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const toast = useToast();
  const { user } = useAuth();

  const logQ = useFuelLog(id ?? '');
  const update = useUpdateFuelLog(id ?? '');
  const remove = useDeleteFuelLog();
  const vehiclesQ = useVehicles({ page: 1, page_size: 200 });
  const branchesQ = useBranches({ page: 1, page_size: 100 });

  const [editOpen, setEditOpen] = useState(false);
  const [liters, setLiters] = useState('');
  const [cost, setCost] = useState('');
  const [odometer, setOdometer] = useState('');
  const [station, setStation] = useState('');
  const [notes, setNotes] = useState('');

  const log = logQ.data;

  const openEdit = () => {
    if (!log) return;
    setLiters(String(log.liters ?? ''));
    setCost(String(log.cost_total ?? ''));
    setOdometer(String(log.odometer_km ?? ''));
    setStation(log.station_name ?? '');
    setNotes(log.notes ?? '');
    setEditOpen(true);
  };

  const onSave = async () => {
    const l = parseFloat(liters);
    if (!Number.isFinite(l) || l <= 0) return toast.error('Liters must be greater than 0');
    const c = parseFloat(cost);
    if (!Number.isFinite(c) || c < 0) return toast.error('Cost must be ≥ 0');
    const odo = parseInt(odometer, 10);
    if (!Number.isFinite(odo) || odo < 0) return toast.error('Odometer must be ≥ 0');
    try {
      await update.mutateAsync({
        liters: l,
        cost_total: c,
        cost_per_liter: Math.round((c / l) * 100) / 100,
        odometer_km: odo,
        station_name: station.trim() || null,
        notes: notes.trim() || null,
      });
      toast.success('Fuel log updated');
      setEditOpen(false);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not update the fuel log');
    }
  };

  const onDelete = () => {
    Alert.alert(
      'Delete fuel log?',
      'This removes the entry and its effect on the vehicle odometer and fuel level.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await remove.mutateAsync(id);
              toast.success('Fuel log deleted');
              router.back();
            } catch (e: any) {
              toast.error(e?.response?.data?.detail ?? 'Could not delete the fuel log');
            }
          },
        },
      ],
    );
  };

  if (logQ.isLoading) {
    return (
      <>
        <Stack.Screen options={{ title: 'Fuel log' }} />
        <View style={s.loading}><Spinner label="Loading fuel log…" /></View>
      </>
    );
  }

  if (!log) {
    return (
      <>
        <Stack.Screen options={{ title: 'Fuel log' }} />
        <View style={s.loading}><Text style={s.errorText}>Fuel log not found</Text></View>
      </>
    );
  }

  const vehicle = vehiclesQ.data?.items.find((v) => v.id === log.vehicle_id);
  const branch = branchesQ.data?.items.find((b) => b.id === log.branch_id);
  const canEdit = canAccess(user?.role, EDIT_ROLES);
  const perLiter = log.liters > 0 ? log.cost_total / log.liters : 0;

  return (
    <>
      <Stack.Screen options={{ title: 'Fuel log' }} />
      <ScrollView style={s.root} contentContainerStyle={{ padding: 16, paddingBottom: 60 }}>
        <Card>
          <View style={s.hero}>
            <View style={s.iconBox}><FuelIcon size={20} color="#B45309" /></View>
            <View style={{ flex: 1 }}>
              <Text style={s.heroLabel}>{vehicle?.reg_number ?? log.vehicle_id}</Text>
              <Text style={s.heroAmount}>{formatNGN(log.cost_total)}</Text>
              <Text style={s.heroSub}>
                {log.liters} L · {formatNGN(perLiter)}/L
              </Text>
            </View>
          </View>
        </Card>

        <View style={{ height: 12 }} />
        <Card>
          <Row label="Occurred" value={new Date(log.occurred_at ?? log.created_at).toLocaleString()} />
          <Row label="Odometer" value={`${log.odometer_km} km`} />
          <Row label="Cost / litre" value={formatNGN(perLiter)} />
          <Row label="Branch" value={branch?.name ?? log.branch_id} />
          {log.station_name ? <Row label="Station" value={log.station_name} /> : null}
          {log.notes ? <Row label="Notes" value={log.notes} /> : null}
          <Row label="Recorded" value={new Date(log.created_at).toLocaleString()} />
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

      <Modal visible={editOpen} onClose={() => setEditOpen(false)} title="Edit fuel log" variant="sheet">
        <Field label="Liters" required>
          <TextInput style={s.input} value={liters} onChangeText={setLiters} keyboardType="decimal-pad" placeholder="0" placeholderTextColor="#94A3B8" />
        </Field>
        <Field label="Cost (₦)" required>
          <TextInput style={s.input} value={cost} onChangeText={setCost} keyboardType="decimal-pad" placeholder="0" placeholderTextColor="#94A3B8" />
        </Field>
        <Field label="Odometer (km)" required>
          <TextInput style={s.input} value={odometer} onChangeText={setOdometer} keyboardType="number-pad" placeholder="0" placeholderTextColor="#94A3B8" />
        </Field>
        <Field label="Station">
          <TextInput style={s.input} value={station} onChangeText={setStation} placeholder="optional" placeholderTextColor="#94A3B8" />
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
      <Text style={s.rowValue} numberOfLines={2}>{value}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F4F4F2' },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  errorText: { fontSize: 16, color: '#B91C1C' },
  hero: { flexDirection: 'row', alignItems: 'center' },
  iconBox: { width: 44, height: 44, borderRadius: 12, backgroundColor: '#FEF3C7', alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  heroLabel: { fontSize: 12, fontWeight: '700', color: '#64748B', textTransform: 'uppercase', letterSpacing: 0.6 },
  heroAmount: { fontSize: 24, fontWeight: '800', color: '#0F172A', marginTop: 2 },
  heroSub: { fontSize: 13, color: '#64748B', marginTop: 2 },
  row: { flexDirection: 'row', alignItems: 'flex-start', paddingVertical: 7 },
  rowLabel: { fontSize: 13, color: '#64748B', width: 100 },
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
