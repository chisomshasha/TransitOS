import React, { useState } from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';
import { Bus } from 'lucide-react-native';
import { useBranches, useCreateVehicle } from '@/lib/queries';
import { useToast } from '@/components/ui/Toast';
import { Modal } from '@/components/ui/Modal';
import { Field } from '@/components/ui/Field';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { VEHICLE_STATUSES, VEHICLE_STATUS_LABELS, type VehicleStatus } from '@/lib/types';

export interface CreateVehicleModalProps {
  visible?: boolean;
  open?: boolean;
  onClose: () => void;
  onSaved?: () => void;
}

export function CreateVehicleModal({ visible, open, onClose, onSaved }: CreateVehicleModalProps) {
  const show = !!(visible ?? open);
  const create = useCreateVehicle();
  const toast = useToast();
  const branchesQ = useBranches({ page: 1, page_size: 100 });
  const [plate, setPlate] = useState('');
  const [model, setModel] = useState('');
  const [capacity, setCapacity] = useState('');
  const [year, setYear] = useState('');
  const [branchId, setBranchId] = useState<string | null>(null);
  const [status, setStatus] = useState<VehicleStatus>('available');

  const reset = () => { setPlate(''); setModel(''); setCapacity(''); setYear(''); setBranchId(null); setStatus('available'); };
  const close = () => { reset(); onClose(); };

  const branchOptions = (branchesQ.data?.items ?? []).map((b) => ({ label: b.name, value: b.id }));
  const statusOptions = VEHICLE_STATUSES.map((st) => ({ label: VEHICLE_STATUS_LABELS[st], value: st }));

  const onSubmit = async () => {
    if (!plate.trim()) return toast.error('Plate number is required');
    if (!model.trim()) return toast.error('Model is required');
    if (!branchId) return toast.error('Branch is required');
    const cap = parseInt(capacity, 10);
    if (!Number.isFinite(cap) || cap < 1) return toast.error('Capacity must be at least 1');
    const yr = year.trim() ? parseInt(year, 10) : null;
    if (yr !== null && (!Number.isFinite(yr) || yr < 1990 || yr > 2100)) return toast.error('Year must be between 1990 and 2100');
    try {
      await create.mutateAsync({
        plate_number: plate.trim().toUpperCase(),
        model: model.trim(),
        capacity_seats: cap,
        year,
        branch_id: branchId,
        status,
      });
      toast.success(`Vehicle ${plate.trim().toUpperCase()} added`);
      reset();
      onSaved?.();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not add vehicle');
    }
  };

  return (
    <Modal visible={show} onClose={close} title="New vehicle" variant="sheet">
      <View style={s.infoBanner}>
        <Bus size={18} color="#0E7490" />
        <Text style={s.infoText}>Vehicles belong to a branch and can be assigned to trips while available.</Text>
      </View>
      <View style={s.row}>
        <View style={s.col}>
          <Field label="Plate number" required>
            <TextInput style={s.input} value={plate} onChangeText={setPlate} placeholder="LAG-123-XY" placeholderTextColor="#94A3B8" autoCapitalize="characters" autoCorrect={false} />
          </Field>
        </View>
        <View style={s.col}>
          <Field label="Model" required>
            <TextInput style={s.input} value={model} onChangeText={setModel} placeholder="Toyota Hiace" placeholderTextColor="#94A3B8" />
          </Field>
        </View>
      </View>
      <View style={s.row}>
        <View style={s.col}>
          <Field label="Seats" required>
            <TextInput style={s.input} value={capacity} onChangeText={setCapacity} placeholder="18" placeholderTextColor="#94A3B8" keyboardType="numeric" />
          </Field>
        </View>
        <View style={s.col}>
          <Field label="Year">
            <TextInput style={s.input} value={year} onChangeText={setYear} placeholder="2021" placeholderTextColor="#94A3B8" keyboardType="numeric" />
          </Field>
        </View>
      </View>
      <Field label="Branch" required>
        <Select value={branchId} onChange={setBranchId} options={branchOptions} placeholder="Select branch" />
      </Field>
      <Field label="Status" required>
        <Select value={status} onChange={setStatus} options={statusOptions} />
      </Field>
      <View style={s.spacerL} />
      <Button label="Add vehicle" onPress={onSubmit} loading={create.isPending} fullWidth />
      <View style={s.spacerS} />
      <Button label="Cancel" onPress={close} variant="ghost" fullWidth />
    </Modal>
  );
}

const s = StyleSheet.create({
  infoBanner: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#ECFEFF', borderRadius: 12, padding: 12, marginBottom: 12 },
  infoText: { fontSize: 13, color: '#0B3D91', marginLeft: 8, flex: 1 },
  input: { height: 48, paddingHorizontal: 12, borderRadius: 12, borderWidth: 1, borderColor: '#E2E8F0', backgroundColor: '#FFFFFF', fontSize: 16, color: '#0F172A' },
  row: { flexDirection: 'row', marginHorizontal: -6 },
  col: { flex: 1, paddingHorizontal: 6 },
  spacerL: { height: 12 },
  spacerS: { height: 8 },
});
