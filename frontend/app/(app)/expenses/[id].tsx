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
import { Pencil, Receipt, Trash2 } from 'lucide-react-native';
import {
  useDeleteExpense,
  useExpense,
  useUpdateExpense,
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
  EXPENSE_CATEGORIES,
  EXPENSE_CATEGORY_LABELS,
  type ExpenseCategory,
  type Role,
} from '@/lib/types';

const EDIT_ROLES: Role[] = [
  'super_admin', 'owner', 'general_manager', 'branch_manager', 'chief_accountant', 'branch_accountant',
];

export default function ExpenseDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const toast = useToast();
  const { user } = useAuth();

  const expenseQ = useExpense(id ?? '');
  const update = useUpdateExpense(id ?? '');
  const remove = useDeleteExpense();
  const vehiclesQ = useVehicles({ page: 1, page_size: 200 });
  const branchesQ = useBranches({ page: 1, page_size: 100 });

  const [editOpen, setEditOpen] = useState(false);
  const [amount, setAmount] = useState('');
  const [category, setCategory] = useState<ExpenseCategory>('other');
  const [notes, setNotes] = useState('');
  const [vendor, setVendor] = useState('');

  const expense = expenseQ.data;

  const openEdit = () => {
    if (!expense) return;
    setAmount(String(expense.amount ?? ''));
    setCategory(expense.category ?? 'other');
    setNotes(expense.notes ?? '');
    setVendor(expense.vendor_name ?? '');
    setEditOpen(true);
  };

  const onSave = async () => {
    const amt = parseFloat(amount);
    if (!Number.isFinite(amt) || amt < 0) return toast.error('Amount must be ≥ 0');
    try {
      await update.mutateAsync({
        amount: amt,
        category,
        notes: notes.trim() || null,
        vendor_name: vendor.trim() || null,
      });
      toast.success('Expense updated');
      setEditOpen(false);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not update the expense');
    }
  };

  const onDelete = () => {
    Alert.alert(
      'Delete expense?',
      'This removes the expense from every total and report. It cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await remove.mutateAsync(id);
              toast.success('Expense deleted');
              router.back();
            } catch (e: any) {
              toast.error(e?.response?.data?.detail ?? 'Could not delete the expense');
            }
          },
        },
      ],
    );
  };

  if (expenseQ.isLoading) {
    return (
      <>
        <Stack.Screen options={{ title: 'Expense' }} />
        <View style={s.loading}><Spinner label="Loading expense…" /></View>
      </>
    );
  }

  if (!expense) {
    return (
      <>
        <Stack.Screen options={{ title: 'Expense' }} />
        <View style={s.loading}><Text style={s.errorText}>Expense not found</Text></View>
      </>
    );
  }

  const vehicle = vehiclesQ.data?.items.find((v) => v.id === expense.vehicle_id);
  const branch = branchesQ.data?.items.find((b) => b.id === expense.branch_id);
  const canEdit = canAccess(user?.role, EDIT_ROLES);

  return (
    <>
      <Stack.Screen options={{ title: 'Expense' }} />
      <ScrollView style={s.root} contentContainerStyle={{ padding: 16, paddingBottom: 60 }}>
        <Card>
          <View style={s.hero}>
            <View style={s.iconBox}><Receipt size={20} color="#B91C1C" /></View>
            <View style={{ flex: 1 }}>
              <Text style={s.heroLabel}>{EXPENSE_CATEGORY_LABELS[expense.category] ?? expense.category}</Text>
              <Text style={s.heroAmount}>{formatNGN(expense.amount)}</Text>
            </View>
            <Badge
              label={expense.scope === 'on_trip' ? 'On trip' : 'Standalone'}
              tone={expense.scope === 'on_trip' ? 'info' : 'neutral'}
            />
          </View>
        </Card>

        <View style={{ height: 12 }} />
        <Card>
          <Row label="Vehicle" value={vehicle?.reg_number ?? expense.vehicle_id} />
          <Row label="Branch" value={branch?.name ?? expense.branch_id} />
          <Row
            label="Occurred"
            value={new Date(expense.occurred_at ?? expense.created_at).toLocaleString()}
          />
          {expense.trip_id ? <Row label="Trip" value={expense.trip_id} /> : null}
          {expense.vendor_name ? <Row label="Vendor" value={expense.vendor_name} /> : null}
          {expense.odometer_km != null ? <Row label="Odometer" value={`${expense.odometer_km} km`} /> : null}
          {expense.notes ? <Row label="Notes" value={expense.notes} /> : null}
          <Row label="Recorded" value={new Date(expense.created_at).toLocaleString()} />
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

      <Modal visible={editOpen} onClose={() => setEditOpen(false)} title="Edit expense" variant="sheet">
        <Field label="Amount (₦)" required>
          <TextInput style={s.input} value={amount} onChangeText={setAmount} keyboardType="decimal-pad" placeholder="0" placeholderTextColor="#94A3B8" />
        </Field>
        <Field label="Category" required>
          <Select
            value={category}
            onChange={setCategory}
            options={EXPENSE_CATEGORIES.map((c) => ({ label: EXPENSE_CATEGORY_LABELS[c], value: c }))}
            placeholder="Select category"
          />
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
      <Text style={s.rowValue} numberOfLines={2}>{value}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F4F4F2' },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  errorText: { fontSize: 16, color: '#B91C1C' },
  hero: { flexDirection: 'row', alignItems: 'center' },
  iconBox: { width: 44, height: 44, borderRadius: 12, backgroundColor: '#FEE2E2', alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  heroLabel: { fontSize: 12, fontWeight: '700', color: '#64748B', textTransform: 'uppercase', letterSpacing: 0.6 },
  heroAmount: { fontSize: 24, fontWeight: '800', color: '#0F172A', marginTop: 2 },
  row: { flexDirection: 'row', alignItems: 'flex-start', paddingVertical: 7 },
  rowLabel: { fontSize: 13, color: '#64748B', width: 92 },
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
