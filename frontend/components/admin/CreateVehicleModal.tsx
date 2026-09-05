import React, { useState } from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';
import { Bus } from 'lucide-react-native';
import { useBranches, useCreateVehicle } from '@/lib/queries';
import { useToast } from '@/components/ui/Toast';
import { Modal } from '@/components/ui/Modal';
import { Field } from '@/components/ui/Field';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { VEHICLE_STATUSES, VEHICLE_STATUS_LABELS, VEHICLE_TYPES, type VehicleStatus, type VehicleType } from '@/lib/types';

export interface CreateVehicleModalProps {
  visible?: boolean;
  open?: boolean;
  onClose: () => void;
  onSaved?: () => void;
}

const VEHICLE_TYPE_LABELS: Record<VehicleType, string> = {
  bus: 'Bus',
  minibus: 'Minibus',
  truck: 'Truck',
};

export function CreateVehicleModal({ visible, open, onClose, onSaved }: CreateVehicleModalProps) {
  const show = !!(visible ?? open);
  const create = useCreateVehicle();
  const toast = useToast();
  const branchesQ = useBranches({ page: 1, page_size: 100 });
  const [regNumber, setRegNumber] = useState('');
  const [type, setType] = useState<VehicleType>('bus');
  const [capacitySeats, setCapacitySeats] = useState('');
  const [capacityKg, setCapacityKg] = useState('');
  const [branchId, setBranchId] = useState<string | null>(null);
  const [status, setStatus] = useState<VehicleStatus>('available');

  const reset = () => {
    setRegNumber(''); setType('bus'); setCapacitySeats(''); setCapacityKg('');
    setBranchId(null); setStatus('available');
  };
  const close = () => { reset(); onClose(); };

  const branchOptions = (branchesQ.data?.items ?? []).map((b) => ({ label: b.name, value: b.id }));
  const statusOptions = VEHICLE_STATUSES.map((st) => ({ label: VEHICLE_STATUS_LABELS[st], value: st }));
  const typeOptions = VEHICLE_TYPES.map((t) => ({ label: VEHICLE_TYPE_LABELS[t], value: t }));

  const onSubmit = async () => {
    if (!regNumber.trim()) return toast.error('Registration number is required');
    if (!branchId) return toast.error('Branch is required');
    const seats = parseInt(capacitySeats, 10);
    if (!Number.isFinite(seats) || seats < 1) return toast.error('Seat capacity must be at least 1');
    const kg = capacityKg.trim() ? parseInt(capacityKg, 10) : 0;
    if (!Number.isFinite(kg) || kg < 0) return toast.error('Cargo capacity must be ≥ 0');
    try {
      await create.mutateAsync({
        reg_number: regNumber.trim().toUpperCase(),
        type,
        capacity_seats: seats,
        capacity_kg: kg,
        branch_id: branchId,
        status,
      });
      toast.success(`Vehicle ${regNumber.trim().toUpperCase()} added`);
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
      <Field label="Registration number" required>
        <TextInput style={s.input} value={regNumber} onChangeText={setRegNumber} placeholder="LAG-123-XY" placeholderTextColor="#94A3B8" autoCapitalize="characters" autoCorrect={false} />
      </Field>
      <Field label="Type" required>
        <Select value={type} onChange={setType} options={typeOptions} />
      </Field>
      <View style={s.row}>
        <View style={s.col}>
          <Field label="Seats" required>
            <TextInput style={s.input} value={capacitySeats} onChangeText={setCapacitySeats} placeholder="18" placeholderTextColor="#94A3B8" keyboardType="numeric" />
          </Field>
        </View>
        <View style={s.col}>
          <Field label="Cargo (kg)" helperText="Optional, defaults to 0">
            <TextInput style={s.input} value={capacityKg} onChangeText={setCapacityKg} placeholder="0" placeholderTextColor="#94A3B8" keyboardType="numeric" />
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
