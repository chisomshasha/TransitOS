import React, { useState } from 'react';
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, TextInput, View } from 'react-native';
import { useRouter } from 'expo-router';
import { Fuel as FuelIcon } from 'lucide-react-native';
import { useCreateFuelLog, useFuelLogs, useVehicles } from '@/lib/queries';
import { Card } from '@/components/ui/Card';
import { Spinner } from '@/components/ui/Spinner';
import { PageHeader } from '@/components/ui/PageHeader';
import { Modal } from '@/components/ui/Modal';
import { Field } from '@/components/ui/Field';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { useToast } from '@/components/ui/Toast';
import { useAuth } from '@/lib/auth-context';
import { canAccess } from '@/lib/rbac';
import { formatNGN } from '@/lib/format';
import type { Role } from '@/lib/types';

const CREATOR_ROLES: Role[] = [
  'super_admin', 'owner', 'general_manager', 'branch_manager', 'fleet_manager',
];

export default function FuelScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const toast = useToast();
  const create = useCreateFuelLog();
  const [open, setOpen] = useState(false);
  const [vehicleId, setVehicleId] = useState<string | null>(null);
  const [liters, setLiters] = useState('');
  const [cost, setCost] = useState('');
  const [odometer, setOdometer] = useState('');
  const [station, setStation] = useState('');
  const [note, setNote] = useState('');
  const { data, isLoading, isFetching, refetch } = useFuelLogs({ page: 1, page_size: 50 });
  const vehiclesQ = useVehicles({ page: 1, page_size: 200 });
  const items = data?.items ?? [];
  const canCreate = canAccess(user?.role, CREATOR_ROLES);
  const vehicleOptions = (vehiclesQ.data?.items ?? []).map((v) => ({ label: v.reg_number, value: v.id }));
  const plateOf = (id: string) => vehiclesQ.data?.items.find((v) => v.id === id)?.reg_number ?? '—';

  const reset = () => {
    setVehicleId(null);
    setLiters('');
    setCost('');
    setOdometer('');
    setStation('');
    setNote('');
  };
  const close = () => { reset(); setOpen(false); };

  const onSubmit = async () => {
    if (!vehicleId) return toast.error('Vehicle is required');
    const l = parseFloat(liters);
    if (!Number.isFinite(l) || l <= 0) return toast.error('Liters must be greater than 0');
    const c = parseFloat(cost);
    if (!Number.isFinite(c) || c <= 0) return toast.error('Cost must be greater than 0');
    const odo = parseInt(odometer, 10);
    if (!Number.isFinite(odo) || odo < 0) return toast.error('Odometer must be ≥ 0');

    // The branch comes from the vehicle — the API requires it and used to
    // be missing from this payload, which made every save fail with 422.
    const vehicle = vehiclesQ.data?.items.find((v) => v.id === vehicleId);
    if (!vehicle) return toast.error('Pick a valid vehicle');

    try {
      await create.mutateAsync({
        vehicle_id: vehicleId,
        branch_id: vehicle.branch_id,
        occurred_at: new Date().toISOString(),
        liters: l,
        cost_total: c,
        cost_per_liter: Math.round((c / l) * 100) / 100,
        odometer_km: odo,
        station_name: station.trim() || null,
        notes: note.trim() || null,
      } as any);
      toast.success('Fuel log saved');
      reset();
      void refetch();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not save fuel log');
    }
  };

  return (
    <View style={s.root}>
      <View style={s.headerWrap}>
        <PageHeader
          title="Fuel"
          subtitle={`${data?.total ?? 0} total`}
          primaryActionLabel={canCreate ? 'Log fuel' : undefined}
          onPrimaryAction={canCreate ? () => setOpen(true) : undefined}
        />
      </View>
      {isLoading ? (
        <View style={s.loading}><Spinner label="Loading fuel logs…" /></View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(f) => f.id}
          contentContainerStyle={{ padding: 16 }}
          ItemSeparatorComponent={() => <View style={{ height: 12 }} />}
          refreshControl={<RefreshControl refreshing={isFetching && !isLoading} onRefresh={refetch} />}
          renderItem={({ item }) => (
            <Pressable onPress={() => router.push(`/fuel/${item.id}` as never)}>
              <Card padding="sm">
                <View style={s.row}>
                  <View style={s.iconBox}><FuelIcon size={18} color="#B45309" /></View>
                  <View style={s.body}>
                    <Text style={s.name}>{plateOf(item.vehicle_id)}</Text>
                    <Text style={s.sub}>
                      {item.liters} L · {new Date(item.occurred_at ?? item.created_at ?? Date.now()).toLocaleDateString()}
                    </Text>
                    {item.odometer_km != null ? <Text style={s.sub}>Odo: {item.odometer_km} km</Text> : null}
                  </View>
                  <Text style={s.amount}>{formatNGN(item.cost_total ?? 0)}</Text>
                </View>
              </Card>
            </Pressable>
          )}
        />
      )}
      <Modal visible={open} onClose={close} title="Log fuel" variant="sheet">
        <Field label="Vehicle" required>
          <Select value={vehicleId} onChange={setVehicleId} options={vehicleOptions} placeholder="Select vehicle" />
        </Field>
        <View style={s.rowInputs}>
          <View style={s.col}>
            <Field label="Liters" required>
              <TextInput style={s.input} value={liters} onChangeText={setLiters} placeholder="0" placeholderTextColor="#94A3B8" keyboardType="decimal-pad" />
            </Field>
          </View>
          <View style={s.col}>
            <Field label="Cost (₦)" required>
              <TextInput style={s.input} value={cost} onChangeText={setCost} placeholder="0" placeholderTextColor="#94A3B8" keyboardType="decimal-pad" />
            </Field>
          </View>
        </View>
        <Field label="Odometer (km)" required>
          <TextInput style={s.input} value={odometer} onChangeText={setOdometer} placeholder="0" placeholderTextColor="#94A3B8" keyboardType="number-pad" />
        </Field>
        <Field label="Station">
          <TextInput style={s.input} value={station} onChangeText={setStation} placeholder="optional" placeholderTextColor="#94A3B8" />
        </Field>
        <Field label="Note">
          <TextInput style={s.input} value={note} onChangeText={setNote} placeholder="optional" placeholderTextColor="#94A3B8" />
        </Field>
        <View style={{ height: 12 }} />
        <Button label="Save fuel log" onPress={onSubmit} loading={create.isPending} fullWidth />
        <View style={{ height: 8 }} />
        <Button label="Cancel" onPress={close} variant="ghost" fullWidth />
      </Modal>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F8F7F4' },
  headerWrap: { paddingHorizontal: 16, paddingTop: 8, paddingBottom: 12, backgroundColor: '#FFFFFF', borderBottomWidth: 1, borderBottomColor: '#E5E5E5' },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  row: { flexDirection: 'row', alignItems: 'center' },
  iconBox: { width: 40, height: 40, borderRadius: 8, backgroundColor: '#FFFBEB', alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  body: { flex: 1 },
  name: { fontSize: 14, fontWeight: '600', color: '#171717' },
  sub: { fontSize: 12, color: '#737373', marginTop: 2 },
  amount: { fontSize: 15, fontWeight: '700', color: '#0F172A' },
  rowInputs: { flexDirection: 'row', gap: 12 },
  col: { flex: 1 },
  input: { height: 48, paddingHorizontal: 12, borderRadius: 12, borderWidth: 1, borderColor: '#E2E8F0', backgroundColor: '#FFFFFF', fontSize: 16, color: '#0F172A' },
});
