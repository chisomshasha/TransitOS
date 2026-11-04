import React, { useState } from 'react';
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, TextInput, View } from 'react-native';
import { useRouter } from 'expo-router';
import { Receipt } from 'lucide-react-native';
import { useBranches, useCreateExpense, useExpenses, useVehicles } from '@/lib/queries';
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
import {
  EXPENSE_CATEGORIES,
  EXPENSE_CATEGORY_LABELS,
  EXPENSE_SCOPES,
  type ExpenseCategory,
  type ExpenseScope,
  type Role,
} from '@/lib/types';

const CREATOR_ROLES: Role[] = [
  'super_admin', 'owner', 'general_manager', 'branch_manager', 'chief_accountant', 'branch_accountant',
];

const CATEGORIES = EXPENSE_CATEGORIES;
const SCOPES = EXPENSE_SCOPES.map((v) => ({
  label: v === 'on_trip' ? 'On a trip' : 'Standalone (branch overhead)',
  value: v,
}));

export default function ExpensesScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const toast = useToast();
  const create = useCreateExpense();
  const [open, setOpen] = useState(false);
  const [branchId, setBranchId] = useState<string | null>(null);
  const [vehicleId, setVehicleId] = useState<string | null>(null);
  const [scope, setScope] = useState<ExpenseScope>('standalone');
  const [category, setCategory] = useState<ExpenseCategory | ''>('');
  const [amount, setAmount] = useState('');
  const [note, setNote] = useState('');
  const [tripId, setTripId] = useState<string | null>(null);
  const { data, isLoading, isFetching, refetch } = useExpenses({ page: 1, page_size: 50 });
  const branchesQ = useBranches({ page: 1, page_size: 100 });
  const vehiclesQ = useVehicles({ page: 1, page_size: 200 });
  const items = data?.items ?? [];
  const canCreate = canAccess(user?.role, CREATOR_ROLES);
  const branchOptions = (branchesQ.data?.items ?? []).map((b) => ({ label: b.name, value: b.id }));
  const vehicleOptions = (vehiclesQ.data?.items ?? []).map((v) => ({
    label: v.reg_number ?? v.id,
    value: v.id,
  }));

  const reset = () => {
    setBranchId(null);
    setVehicleId(null);
    setScope('standalone');
    setCategory('');
    setAmount('');
    setNote('');
    setTripId(null);
  };
  const close = () => { reset(); setOpen(false); };

  const onSubmit = async () => {
    // The API requires vehicle_id, scope and occurred_at — the original
    // form omitted all three and was rejected with a 422.
    if (!branchId) return toast.error('Branch is required');
    if (!vehicleId) return toast.error('Vehicle is required');
    if (!category) return toast.error('Category is required');
    const amt = parseFloat(amount);
    if (!Number.isFinite(amt) || amt <= 0) return toast.error('Amount must be greater than 0');
    if (scope === 'on_trip' && !tripId) {
      return toast.error('Select the trip this expense belongs to');
    }

    try {
      await create.mutateAsync({
        branch_id: branchId,
        vehicle_id: vehicleId,
        scope,
        trip_id: scope === 'on_trip' ? tripId : null,
        category,
        amount: amt,
        occurred_at: new Date().toISOString(),
        notes: note.trim() || null,
      } as any);
      toast.success('Expense recorded');
      reset();
      void refetch();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not record expense');
    }
  };

  return (
    <View style={s.root}>
      <View style={s.headerWrap}>
        <PageHeader
          title="Expenses"
          subtitle={`${data?.total ?? 0} total`}
          primaryActionLabel={canCreate ? 'Record expense' : undefined}
          onPrimaryAction={canCreate ? () => setOpen(true) : undefined}
        />
      </View>
      {isLoading ? (
        <View style={s.loading}><Spinner label="Loading expenses…" /></View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(e) => e.id}
          contentContainerStyle={{ padding: 16 }}
          ItemSeparatorComponent={() => <View style={{ height: 12 }} />}
          refreshControl={<RefreshControl refreshing={isFetching && !isLoading} onRefresh={refetch} />}
          renderItem={({ item }) => (
            <Pressable onPress={() => router.push(`/expenses/${item.id}` as never)}>
              <Card padding="sm">
                <View style={s.row}>
                  <View style={s.iconBox}><Receipt size={18} color="#B45309" /></View>
                  <View style={s.body}>
                    <Text style={s.name}>{item.category}</Text>
                    <Text style={s.sub}>
                      {new Date(item.occurred_at ?? item.created_at ?? Date.now()).toLocaleDateString()}
                      {item.scope === 'on_trip' ? ' · on trip' : ' · standalone'}
                    </Text>
                    {item.notes ? <Text style={s.sub} numberOfLines={1}>{item.notes}</Text> : null}
                  </View>
                  <Text style={s.amount}>{formatNGN(item.amount)}</Text>
                </View>
              </Card>
            </Pressable>
          )}
        />
      )}
      <Modal visible={open} onClose={close} title="Record expense" variant="sheet">
        <Field label="Branch" required>
          <Select value={branchId} onChange={setBranchId} options={branchOptions} placeholder="Select branch" />
        </Field>
        <Field label="Vehicle" required>
          <Select value={vehicleId} onChange={setVehicleId} options={vehicleOptions} placeholder="Select vehicle" />
        </Field>
        <Field label="Scope" required>
          <Select
            value={scope}
            onChange={setScope}
            options={SCOPES}
            placeholder="Select scope"
          />
        </Field>
        <Field label="Category" required>
          <Select
            value={category}
            onChange={setCategory}
            options={CATEGORIES.map((c) => ({ label: EXPENSE_CATEGORY_LABELS[c], value: c }))}
            placeholder="Select category"
          />
        </Field>
        {scope === 'on_trip' ? (
          <Field label="Trip ID" required helperText="Paste the trip this expense belongs to">
            <TextInput
              style={s.input}
              value={tripId ?? ''}
              onChangeText={setTripId}
              placeholder="Trip id"
              placeholderTextColor="#94A3B8"
              autoCapitalize="none"
            />
          </Field>
        ) : null}
        <Field label="Amount (₦)" required>
          <TextInput style={s.input} value={amount} onChangeText={setAmount} placeholder="0" placeholderTextColor="#94A3B8" keyboardType="decimal-pad" />
        </Field>
        <Field label="Note">
          <TextInput style={s.input} value={note} onChangeText={setNote} placeholder="optional" placeholderTextColor="#94A3B8" />
        </Field>
        <View style={{ height: 12 }} />
        <Button label="Save expense" onPress={onSubmit} loading={create.isPending} fullWidth />
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
  amount: { fontSize: 15, fontWeight: '700', color: '#B91C1C' },
  input: { height: 48, paddingHorizontal: 12, borderRadius: 12, borderWidth: 1, borderColor: '#E2E8F0', backgroundColor: '#FFFFFF', fontSize: 16, color: '#0F172A' },
});
