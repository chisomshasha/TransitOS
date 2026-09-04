import React, { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { Route as RouteIcon } from 'lucide-react-native';
import { useBranches, useCreateRoute } from '@/lib/queries';
import { useToast } from '@/components/ui/Toast';
import { Modal } from '@/components/ui/Modal';
import { Field } from '@/components/ui/Field';
import { Button } from '@/components/ui/Button';
import { ROUTE_TYPES, type RouteType } from '@/lib/types';

export interface CreateRouteModalProps {
  visible?: boolean;
  open?: boolean;
  onClose: () => void;
  onSaved?: () => void;
}

const TYPE_LABELS: Record<RouteType, string> = {
  intrastate: 'Intrastate',
  interstate: 'Interstate',
};

export function CreateRouteModal({ visible, open, onClose, onSaved }: CreateRouteModalProps) {
  const show = !!(visible ?? open);
  const create = useCreateRoute();
  const toast = useToast();
  const branchesQ = useBranches({ page: 1, page_size: 100 });
  const branchOptions = branchesQ.data?.items ?? [];
  const [name, setName] = useState('');
  const [type, setType] = useState<RouteType>('intrastate');
  const [originBranchId, setOriginBranchId] = useState('');
  const [destBranchId, setDestBranchId] = useState('');
  const [originCity, setOriginCity] = useState('');
  const [destCity, setDestCity] = useState('');
  const [distance, setDistance] = useState('');
  const [duration, setDuration] = useState('');
  const [passengerFare, setPassengerFare] = useState('');
  const [cargoFare, setCargoFare] = useState('');

  useEffect(() => {
    if (!show) return;
    if (!originBranchId && branchOptions.length > 0) setOriginBranchId(branchOptions[0].id);
    if (!destBranchId && branchOptions.length > 1) setDestBranchId(branchOptions[1].id);
    else if (!destBranchId && branchOptions.length === 1) setDestBranchId(branchOptions[0].id);
  }, [show, branchOptions, originBranchId, destBranchId]);

  const reset = () => {
    setName(''); setType('intrastate'); setOriginBranchId(''); setDestBranchId('');
    setOriginCity(''); setDestCity(''); setDistance(''); setDuration('');
    setPassengerFare(''); setCargoFare('');
  };
  const close = () => { reset(); onClose(); };

  const onSubmit = async () => {
    if (!name.trim()) return toast.error('Route name is required');
    if (!originBranchId) return toast.error('Origin branch is required');
    if (!destBranchId) return toast.error('Destination branch is required');
    if (originBranchId === destBranchId) return toast.error('Origin and destination branches must differ');
    if (!originCity.trim() || !destCity.trim()) return toast.error('Origin and destination cities are required');
    const distN = parseFloat(distance);
    const durN = parseFloat(duration);
    const fareN = parseFloat(passengerFare);
    const cargoN = parseFloat(cargoFare);
    if (!Number.isFinite(distN) || distN < 0) return toast.error('Distance must be ≥ 0');
    if (!Number.isFinite(durN) || durN < 0) return toast.error('Duration must be ≥ 0');
    if (!Number.isFinite(fareN) || fareN < 0) return toast.error('Passenger fare must be ≥ 0');
    if (!Number.isFinite(cargoN) || cargoN < 0) return toast.error('Cargo fare must be ≥ 0');
    try {
      await create.mutateAsync({
        name: name.trim(),
        branch_id: originBranchId,
        type,
        origin_branch_id: originBranchId,
        destination_branch_id: destBranchId,
        origin_city: originCity.trim(),
        destination_city: destCity.trim(),
        distance_km: distN,
        base_fare_passenger: fareN,
        base_fare_cargo_per_kg: cargoN,
        estimated_duration_hours: durN,
        intermediate_stops: [],
        required_permits: [],
        is_active: true,
      });
      toast.success(`Route "${name.trim()}" created`);
      reset();
      onSaved?.();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not create route');
    }
  };

  const chipList = (options: { id: string; name: string }[], activeId: string, onPick: (id: string) => void) => (
    <View style={s.chipRow}>
      {options.map((b) => {
        const active = b.id === activeId;
        return (
          <Pressable key={b.id} onPress={() => onPick(b.id)} style={[s.chip, active && s.chipActive]} accessibilityRole="button" accessibilityState={{ selected: active }}>
            <Text style={[s.chipText, active && s.chipTextActive]}>{b.name}</Text>
          </Pressable>
        );
      })}
    </View>
  );

  return (
    <Modal visible={show} onClose={close} title="New route" variant="sheet">
      <View style={s.infoBanner}>
        <RouteIcon size={18} color="#0E7490" />
        <Text style={s.infoText}>A route connects an origin branch to a destination branch. Trips are scheduled against routes.</Text>
      </View>
      {branchOptions.length < 2 ? (
        <View style={s.warnBanner}>
          <Text style={s.warnBannerText}>You need at least 2 branches to create a route. Create the second branch first.</Text>
        </View>
      ) : null}
      <Field label="Name" required>
        <TextInput style={s.input} value={name} onChangeText={setName} placeholder="Lagos ↔ Abuja Express" placeholderTextColor="#94A3B8" />
      </Field>
      <Field label="Type" required>
        <View style={s.chipRow}>
          {ROUTE_TYPES.map((t) => {
            const active = t === type;
            return (
              <Pressable key={t} onPress={() => setType(t)} style={[s.chip, active && s.chipActive]} accessibilityRole="button" accessibilityState={{ selected: active }}>
                <Text style={[s.chipText, active && s.chipTextActive]}>{TYPE_LABELS[t]}</Text>
              </Pressable>
            );
          })}
        </View>
      </Field>
      <Field label="Origin branch" required>{chipList(branchOptions, originBranchId, setOriginBranchId)}</Field>
      <Field label="Destination branch" required>{chipList(branchOptions, destBranchId, setDestBranchId)}</Field>
      <View style={s.row}>
        <View style={s.col}>
          <Field label="Origin city" required>
            <TextInput style={s.input} value={originCity} onChangeText={setOriginCity} placeholder="Lagos" placeholderTextColor="#94A3B8" />
          </Field>
        </View>
        <View style={s.col}>
          <Field label="Destination city" required>
            <TextInput style={s.input} value={destCity} onChangeText={setDestCity} placeholder="Abuja" placeholderTextColor="#94A3B8" />
          </Field>
        </View>
      </View>
      <View style={s.row}>
        <View style={s.col}>
          <Field label="Distance (km)" required>
            <TextInput style={s.input} value={distance} onChangeText={setDistance} placeholder="750" placeholderTextColor="#94A3B8" keyboardType="decimal-pad" />
          </Field>
        </View>
        <View style={s.col}>
          <Field label="Duration (hrs)" required>
            <TextInput style={s.input} value={duration} onChangeText={setDuration} placeholder="9.5" placeholderTextColor="#94A3B8" keyboardType="decimal-pad" />
          </Field>
        </View>
      </View>
      <View style={s.row}>
        <View style={s.col}>
          <Field label="Passenger fare" required>
            <TextInput style={s.input} value={passengerFare} onChangeText={setPassengerFare} placeholder="12000" placeholderTextColor="#94A3B8" keyboardType="decimal-pad" />
          </Field>
        </View>
        <View style={s.col}>
          <Field label="Cargo fare /kg" required>
            <TextInput style={s.input} value={cargoFare} onChangeText={setCargoFare} placeholder="150" placeholderTextColor="#94A3B8" keyboardType="decimal-pad" />
          </Field>
        </View>
      </View>
      <View style={s.spacerL} />
      <Button label="Create route" onPress={onSubmit} loading={create.isPending} fullWidth disabled={branchOptions.length < 2} />
      <View style={s.spacerS} />
      <Button label="Cancel" onPress={close} variant="ghost" fullWidth />
    </Modal>
  );
}

const s = StyleSheet.create({
  infoBanner: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#ECFEFF', borderRadius: 12, padding: 12, marginBottom: 12 },
  infoText: { fontSize: 13, color: '#0B3D91', marginLeft: 8, flex: 1 },
  warnBanner: { backgroundColor: '#FFFBEB', borderWidth: 1, borderColor: '#FEF3C7', borderRadius: 12, padding: 12, marginBottom: 12 },
  warnBannerText: { fontSize: 12, color: '#B45309' },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap' },
  chip: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 9999, marginRight: 6, marginBottom: 6, backgroundColor: '#F1F5F9' },
  chipActive: { backgroundColor: '#0B3D91' },
  chipText: { fontSize: 12, fontWeight: '500', color: '#334155' },
  chipTextActive: { color: '#FFFFFF' },
  input: { height: 48, paddingHorizontal: 12, borderRadius: 12, borderWidth: 1, borderColor: '#E2E8F0', backgroundColor: '#FFFFFF', fontSize: 16, color: '#0F172A' },
  row: { flexDirection: 'row', marginHorizontal: -6 },
  col: { flex: 1, paddingHorizontal: 6 },
  spacerL: { height: 12 },
  spacerS: { height: 8 },
});
