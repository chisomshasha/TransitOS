import React, { useState } from 'react';
import { FlatList, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { useBranches, useVehicles } from '@/lib/queries';
import { useCreateTransfer } from '@/lib/queries-p5';
import { Modal } from '@/components/ui/Modal';
import { Field } from '@/components/ui/Field';
import { Button } from '@/components/ui/Button';
import { useToast } from '@/components/ui/Toast';
import { brand } from '@/lib/theme';

interface Props {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
  defaultVehicleId?: string;
}

export function CreateTransferModal({ open, onClose, onSaved, defaultVehicleId }: Props) {
  const toast = useToast();
  const vehiclesQ = useVehicles({ page: 1, page_size: 200 });
  const branchesQ = useBranches({ page: 1, page_size: 200 });
  const create = useCreateTransfer();

  const [vehicleId, setVehicleId] = useState(defaultVehicleId ?? '');
  const [toBranchId, setToBranchId] = useState('');
  const [reason, setReason] = useState('');
  const [expectedReturn, setExpectedReturn] = useState('');

  const vehicles = vehiclesQ.data?.items ?? [];
  const branches = branchesQ.data?.items ?? [];
  const selectedVehicle = vehicles.find((v) => v.id === vehicleId);

  React.useEffect(() => {
    if (open) {
      setVehicleId(defaultVehicleId ?? '');
      setToBranchId('');
      setReason('');
      setExpectedReturn('');
    }
  }, [open, defaultVehicleId]);

  const availableBranches = branches.filter(
    (b) => b.id !== selectedVehicle?.branch_id && b.status === 'active',
  );

  const onSubmit = async () => {
    if (!vehicleId) return toast.error('Select a vehicle');
    if (!toBranchId) return toast.error('Select destination branch');
    if (!reason.trim()) return toast.error('Reason is required');
    let expectedIso: string | null = null;
    if (expectedReturn.trim()) {
      const d = new Date(expectedReturn.trim());
      if (isNaN(d.getTime())) return toast.error('Invalid return date (use YYYY-MM-DD)');
      expectedIso = d.toISOString();
    }
    try {
      await create.mutateAsync({
        vehicle_id: vehicleId,
        to_branch_id: toBranchId,
        reason: reason.trim(),
        expected_return_at: expectedIso,
      });
      toast.success('Transfer initiated');
      onSaved();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not initiate transfer');
    }
  };

  return (
    <Modal visible={open} onClose={onClose} title="Initiate transfer" variant="sheet">
      <Text style={s.label}>VEHICLE</Text>
      <View style={s.chipWrap}>
        {vehicles.map((v) => (
          <Pressable
            key={v.id}
            style={[s.chip, vehicleId === v.id && s.chipActive]}
            onPress={() => setVehicleId(v.id)}
          >
            <Text style={[s.chipText, vehicleId === v.id && s.chipTextActive]}>{v.reg_number}</Text>
          </Pressable>
        ))}
      </View>

      {selectedVehicle ? (
        <Text style={s.helpText}>
          From: {branches.find((b) => b.id === selectedVehicle.branch_id)?.name ?? '—'}
        </Text>
      ) : null}

      <Text style={s.label}>DESTINATION BRANCH</Text>
      {availableBranches.length === 0 ? (
        <Text style={s.helpText}>No other active branches available.</Text>
      ) : (
        <View style={s.chipWrap}>
          {availableBranches.map((b) => (
            <Pressable
              key={b.id}
              style={[s.chip, toBranchId === b.id && s.chipActive]}
              onPress={() => setToBranchId(b.id)}
            >
              <Text style={[s.chipText, toBranchId === b.id && s.chipTextActive]}>{b.name}</Text>
            </Pressable>
          ))}
        </View>
      )}

      <Field label="Reason" required>
        <TextInput
          style={s.input}
          value={reason}
          onChangeText={setReason}
          placeholder="e.g. Short-term loan for peak route"
          placeholderTextColor="#94A3B8"
          multiline
          numberOfLines={3}
          textAlignVertical="top"
        />
      </Field>

      <Field label="Expected return (YYYY-MM-DD, optional)">
        <TextInput
          style={s.input}
          value={expectedReturn}
          onChangeText={setExpectedReturn}
          placeholder="2026-12-31"
          placeholderTextColor="#94A3B8"
          autoCapitalize="none"
        />
      </Field>

      <View style={{ height: 12 }} />
      <Button label="Initiate transfer" onPress={onSubmit} loading={create.isPending} fullWidth />
      <View style={{ height: 8 }} />
      <Button label="Cancel" variant="ghost" onPress={onClose} fullWidth />
    </Modal>
  );
}

const s = StyleSheet.create({
  label: {
    fontSize: 11,
    fontWeight: '700',
    color: '#64748B',
    letterSpacing: 0.6,
    textTransform: 'uppercase',
    marginTop: 8,
    marginBottom: 6,
  },
  chipWrap: { flexDirection: 'row', flexWrap: 'wrap' },
  chip: {
    backgroundColor: '#E2E8F0',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 7,
    marginRight: 6,
    marginBottom: 6,
  },
  chipActive: { backgroundColor: brand.navy },
  chipText: { fontSize: 13, fontWeight: '600', color: '#475569' },
  chipTextActive: { color: '#FFFFFF' },
  helpText: { fontSize: 12, color: '#64748B', marginTop: 4, marginBottom: 8 },
  input: {
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#E2E8F0',
    borderRadius: 10,
    padding: 10,
    fontSize: 14,
    color: '#0F172A',
    minHeight: 80,
  },
});
