import React, { useState } from 'react';
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, TextInput, View } from 'react-native';
import { useRouter } from 'expo-router';
import { Wrench } from 'lucide-react-native';
import { useCreateMaintenance, useMaintenance, useVehicles } from '@/lib/queries';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
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
import { MAINTENANCE_TYPES, type MaintenanceType, type Role } from '@/lib/types';

const CREATOR_ROLES: Role[] = [
  'super_admin', 'owner', 'general_manager', 'branch_manager', 'fleet_manager',
];

export default function MaintenanceScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const toast = useToast();
  const create = useCreateMaintenance();
  const [open, setOpen] = useState(false);
  const [vehicleId, setVehicleId] = useState<string | null>(null);
  const [type, setType] = useState<MaintenanceType>('routine');
  const [title, setTitle] = useState('');
  const [cost, setCost] = useState('');
  const [note, setNote] = useState('');
  const { data, isLoading, isFetching, refetch } = useMaintenance({ page: 1, page_size: 50 });
  const vehiclesQ = useVehicles({ page: 1, page_size: 200 });
  const items = data?.items ?? [];
  const canCreate = canAccess(user?.role, CREATOR_ROLES);
  const vehicleOptions = (vehiclesQ.data?.items ?? []).map((v) => ({ label: v.reg_number, value: v.id }));
  const plateOf = (id: string) => vehiclesQ.data?.items.find((v) => v.id === id)?.reg_number ?? '—';

  const reset = () => { setVehicleId(null); setType('routine'); setTitle(''); setCost(''); setNote(''); };
  const close = () => { reset(); setOpen(false); };

  const onSubmit = async () => {
    if (!vehicleId) return toast.error('Vehicle is required');
    // The API requires a title of at least 2 characters.
    if (title.trim().length < 2) return toast.error('Give the job a short title');
    const costN = parseFloat(cost);
    if (!Number.isFinite(costN) || costN < 0) return toast.error('Cost must be ≥ 0');

    // The branch comes from the vehicle — the API requires it and it used
    // to be missing from this payload, which made every save fail.
    const vehicle = vehiclesQ.data?.items.find((v) => v.id === vehicleId);
    if (!vehicle) return toast.error('Pick a valid vehicle');

    try {
      await create.mutateAsync({
        vehicle_id: vehicleId,
        branch_id: vehicle.branch_id,
        type,
        status: 'scheduled',
        title: title.trim(),
        cost_parts: costN,
        cost_labor: 0,
        cost_total: costN,
        notes: note.trim() || null,
      } as any);
      toast.success('Maintenance logged');
      reset();
      void refetch();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not log maintenance');
    }
  };

  return (
    <View style={s.root}>
      <View style={s.headerWrap}>
        <PageHeader
          title="Maintenance"
          subtitle={`${data?.total ?? 0} total`}
          primaryActionLabel={canCreate ? 'Log maintenance' : undefined}
          onPrimaryAction={canCreate ? () => setOpen(true) : undefined}
        />
      </View>
      {isLoading ? (
        <View style={s.loading}><Spinner label="Loading maintenance…" /></View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(m) => m.id}
          contentContainerStyle={{ padding: 16 }}
          ItemSeparatorComponent={() => <View style={{ height: 12 }} />}
          refreshControl={<RefreshControl refreshing={isFetching && !isLoading} onRefresh={refetch} />}
          renderItem={({ item }) => (
            <Pressable onPress={() => router.push(`/maintenance/${item.id}` as never)}>
              <Card padding="sm">
                <View style={s.row}>
                  <View style={s.iconBox}><Wrench size={18} color="#0B3D91" /></View>
                  <View style={s.body}>
                    <Text style={s.name}>{item.title}</Text>
                    <Text style={s.sub}>
                      {plateOf(item.vehicle_id)} · {item.type}
                    </Text>
                  </View>
                  <View style={s.right}>
                    <Badge label={item.status.replace(/_/g, ' ')} tone={item.status === 'completed' ? 'success' : item.status === 'cancelled' ? 'neutral' : 'info'} size="sm" />
                    <Text style={s.amount}>{formatNGN(item.cost_total ?? 0)}</Text>
                  </View>
                </View>
              </Card>
            </Pressable>
          )}
        />
      )}
      <Modal visible={open} onClose={close} title="Log maintenance" variant="sheet">
        <Field label="Vehicle" required>
          <Select value={vehicleId} onChange={setVehicleId} options={vehicleOptions} placeholder="Select vehicle" />
        </Field>
        <Field label="Type" required>
          <Select
            value={type}
            onChange={setType}
            options={MAINTENANCE_TYPES.map((t) => ({ label: t.replace(/_/g, ' '), value: t }))}
            placeholder="Select type"
          />
        </Field>
        <Field label="Title" required helperText="What is being done?">
          <TextInput style={s.input} value={title} onChangeText={setTitle} placeholder="e.g. Brake service" placeholderTextColor="#94A3B8" />
        </Field>
        <Field label="Cost (₦)">
          <TextInput style={s.input} value={cost} onChangeText={setCost} placeholder="0" placeholderTextColor="#94A3B8" keyboardType="decimal-pad" />
        </Field>
        <Field label="Note">
          <TextInput style={s.input} value={note} onChangeText={setNote} placeholder="optional" placeholderTextColor="#94A3B8" />
        </Field>
        <View style={{ height: 12 }} />
        <Button label="Save maintenance" onPress={onSubmit} loading={create.isPending} fullWidth />
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
  iconBox: { width: 40, height: 40, borderRadius: 8, backgroundColor: '#DBEAFE', alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  body: { flex: 1 },
  right: { alignItems: 'flex-end' },
  name: { fontSize: 14, fontWeight: '600', color: '#171717' },
  sub: { fontSize: 12, color: '#737373', marginTop: 2 },
  amount: { fontSize: 15, fontWeight: '700', color: '#0F172A', marginTop: 4 },
  input: { height: 48, paddingHorizontal: 12, borderRadius: 12, borderWidth: 1, borderColor: '#E2E8F0', backgroundColor: '#FFFFFF', fontSize: 16, color: '#0F172A' },
});
