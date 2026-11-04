import React, { useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { Package, Plus, Trash2, User } from 'lucide-react-native';
import { useAddManifestEntry, useDeleteManifestEntry, useManifest } from '@/lib/queries';
import { useAuth } from '@/lib/auth-context';
import { canAccess } from '@/lib/rbac';
import { useToast } from '@/components/ui/Toast';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { Field } from '@/components/ui/Field';
import { Select } from '@/components/ui/Select';
import { formatNGN } from '@/lib/format';
import { TRIP_MANIFEST_MUTATE_ROLES } from '@/lib/money-loop';
import type { ManifestEntry, ManifestPaymentStatus, ManifestType, Trip } from '@/lib/types';

export interface ManifestEditorProps {
  trip: Trip;
}

/**
 * The passenger and cargo manifest for a trip.
 *
 * The manifest is what the money is measured against: the backend sums
 * the fares to produce the trip's `total_revenue`, and the same sum
 * becomes the `expected_total` of the cash-up. Without entries on the
 * manifest every cash-up would look like a full overage.
 *
 * The backend refuses to add or remove entries once the trip has
 * departed, so the buttons are hidden in the same states.
 */

const MANIFEST_LOCKED_STATUSES = ['departed', 'arrived', 'closed', 'cashed_up', 'cancelled'];

const PAYMENT_OPTIONS: Array<{ label: string; value: ManifestPaymentStatus }> = [
  { label: 'Pay on board', value: 'on_board' },
  { label: 'Already paid', value: 'paid' },
  { label: 'Cancelled', value: 'cancelled' },
];

export function ManifestEditor({ trip }: ManifestEditorProps) {
  const { user } = useAuth();
  const toast = useToast();
  const manifestQ = useManifest(trip.id);
  const addEntry = useAddManifestEntry(trip.id);
  const removeEntry = useDeleteManifestEntry(trip.id);

  const [showAll, setShowAll] = useState(false);
  const [adding, setAdding] = useState<ManifestType | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const entries = manifestQ.data?.items ?? [];
  const visible = showAll ? entries : entries.slice(0, 3);

  const canEdit = canAccess(user?.role, TRIP_MANIFEST_MUTATE_ROLES);
  const locked = MANIFEST_LOCKED_STATUSES.includes(trip.status);
  const editable = canEdit && !locked;

  const onDelete = async (entry: ManifestEntry) => {
    setBusyId(entry.id);
    try {
      await removeEntry.mutateAsync(entry.id);
      toast.success('Manifest entry removed');
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not remove the manifest entry');
    } finally {
      setBusyId(null);
    }
  };

  const onAdded = () => {
    setAdding(null);
    toast.success('Manifest entry added');
  };

  return (
    <View testID="manifest-editor">
      <View style={s.headRow}>
        <Text style={s.heading}>Manifest ({entries.length} entries)</Text>
        {editable ? (
          <View style={s.headActions}>
            <Pressable
              style={s.addBtn}
              onPress={() => setAdding('passenger')}
              accessibilityRole="button"
              accessibilityLabel="Add passenger"
              testID="manifest-add-passenger"
            >
              <Plus size={13} color="#0B3D91" />
              <Text style={s.addBtnText}>Passenger</Text>
            </Pressable>
            <Pressable
              style={s.addBtn}
              onPress={() => setAdding('cargo')}
              accessibilityRole="button"
              accessibilityLabel="Add cargo"
              testID="manifest-add-cargo"
            >
              <Plus size={13} color="#0B3D91" />
              <Text style={s.addBtnText}>Cargo</Text>
            </Pressable>
          </View>
        ) : null}
      </View>

      {!canEdit ? (
        <Text style={s.readOnly}>
          Only a conductor or manager can change the manifest.
        </Text>
      ) : locked ? (
        <Text style={s.readOnly}>
          The manifest is locked once the trip has departed.
        </Text>
      ) : null}

      <View style={s.card}>
        {entries.length === 0 ? (
          <Text style={s.emptyText}>
            No manifest entries yet. Add the passengers and cargo for this trip so the
            expected revenue is correct.
          </Text>
        ) : (
          <>
            {visible.map((m) => (
              <View key={m.id} style={s.row}>
                <View style={s.iconBox}>
                  {m.type === 'cargo' ? (
                    <Package size={16} color="#0E7490" />
                  ) : (
                    <User size={16} color="#0B3D91" />
                  )}
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={s.name}>
                    {m.type === 'cargo'
                      ? `Parcel — ${m.cargo_description ?? ''}`
                      : m.passenger_name ?? '—'}
                  </Text>
                  <Text style={s.sub}>
                    {m.type === 'cargo'
                      ? `${m.cargo_weight_kg ?? 0} kg`
                      : `Seat ${m.seat_number ?? '—'}`}{' '}
                    · {formatNGN(m.fare)}
                  </Text>
                </View>
                {m.type === 'cargo' ? (
                  <Badge label="CARGO" tone="info" size="sm" />
                ) : (
                  <Badge
                    label={m.payment_status.toUpperCase()}
                    tone={
                      m.payment_status === 'paid'
                        ? 'success'
                        : m.payment_status === 'on_board'
                        ? 'info'
                        : 'danger'
                    }
                    size="sm"
                  />
                )}
                {editable ? (
                  <Pressable
                    style={s.deleteBtn}
                    onPress={() => onDelete(m)}
                    disabled={busyId === m.id}
                    accessibilityRole="button"
                    accessibilityLabel="Remove manifest entry"
                    hitSlop={8}
                  >
                    <Trash2 size={16} color="#B91C1C" />
                  </Pressable>
                ) : null}
              </View>
            ))}
            {entries.length > 3 ? (
              <Pressable style={s.more} onPress={() => setShowAll((v) => !v)}>
                <Text style={s.moreText}>
                  {showAll ? 'Show less' : `… ${entries.length - 3} more — View all`}
                </Text>
              </Pressable>
            ) : null}
          </>
        )}
      </View>

      <ManifestFormModal
        trip={trip}
        type={adding}
        onClose={() => setAdding(null)}
        onAdded={onAdded}
        saving={addEntry.isPending}
        save={addEntry.mutateAsync}
      />
    </View>
  );
}

function ManifestFormModal({
  trip,
  type,
  onClose,
  onAdded,
  saving,
  save,
}: {
  trip: Trip;
  type: ManifestType | null;
  onClose: () => void;
  onAdded: () => void;
  saving: boolean;
  save: (body: Record<string, unknown>) => Promise<unknown>;
}) {
  const toast = useToast();
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [seat, setSeat] = useState('');
  const [description, setDescription] = useState('');
  const [weight, setWeight] = useState('');
  const [fare, setFare] = useState('');
  const [paymentStatus, setPaymentStatus] = useState<ManifestPaymentStatus>('on_board');

  const reset = () => {
    setName('');
    setPhone('');
    setSeat('');
    setDescription('');
    setWeight('');
    setFare('');
    setPaymentStatus('on_board');
  };

  const close = () => {
    reset();
    onClose();
  };

  const onSave = async () => {
    const amount = parseFloat(fare);
    if (!Number.isFinite(amount) || amount < 0) {
      toast.error('Enter a valid fare');
      return;
    }
    if (type === 'cargo') {
      const kg = parseFloat(weight);
      if (!Number.isFinite(kg) || kg <= 0) {
        toast.error('Enter the cargo weight in kilograms');
        return;
      }
      if (!description.trim()) {
        toast.error('Describe the cargo');
        return;
      }
    } else if (!name.trim()) {
      toast.error('Enter the passenger name');
      return;
    }

    const body: Record<string, unknown> = {
      trip_id: trip.id,
      type,
      fare: amount,
      payment_status: paymentStatus,
    };
    if (type === 'cargo') {
      body.cargo_description = description.trim();
      body.cargo_weight_kg = parseFloat(weight);
      if (name.trim()) body.cargo_sender_name = name.trim();
      if (phone.trim()) body.cargo_receiver_phone = phone.trim();
    } else {
      body.passenger_name = name.trim();
      if (phone.trim()) body.passenger_phone = phone.trim();
      if (seat.trim()) body.seat_number = seat.trim();
    }

    try {
      await save(body);
      reset();
      onAdded();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not add the manifest entry');
    }
  };

  return (
    <Modal
      visible={type !== null}
      onClose={close}
      title={type === 'cargo' ? 'Add cargo' : 'Add passenger'}
      variant="sheet"
    >
      {type === 'cargo' ? (
        <>
          <Field label="Cargo description" required>
            <TextInput
              style={s.input}
              value={description}
              onChangeText={setDescription}
              placeholder="e.g. 2 cartons of drinks"
            />
          </Field>
          <Field label="Weight (kg)" required>
            <TextInput
              style={s.input}
              value={weight}
              onChangeText={setWeight}
              keyboardType="numeric"
              placeholder="e.g. 25"
            />
          </Field>
          <Field label="Sender">
            <TextInput
              style={s.input}
              value={name}
              onChangeText={setName}
              placeholder="Name of the sender"
            />
          </Field>
          <Field label="Receiver phone">
            <TextInput
              style={s.input}
              value={phone}
              onChangeText={setPhone}
              keyboardType="phone-pad"
              placeholder="08000000000"
            />
          </Field>
        </>
      ) : (
        <>
          <Field label="Passenger name" required>
            <TextInput
              style={s.input}
              value={name}
              onChangeText={setName}
              placeholder="Full name"
            />
          </Field>
          <Field label="Phone">
            <TextInput
              style={s.input}
              value={phone}
              onChangeText={setPhone}
              keyboardType="phone-pad"
              placeholder="08000000000"
            />
          </Field>
          <Field label="Seat number">
            <TextInput
              style={s.input}
              value={seat}
              onChangeText={setSeat}
              placeholder="e.g. 12"
            />
          </Field>
        </>
      )}

      <Field label="Fare (₦)" required>
        <TextInput
          style={s.input}
          value={fare}
          onChangeText={setFare}
          keyboardType="numeric"
          placeholder="e.g. 2500"
        />
      </Field>

      <Field label="Payment status">
        <Select
          value={paymentStatus}
          onChange={setPaymentStatus}
          options={PAYMENT_OPTIONS}
          placeholder="Payment status"
        />
      </Field>

      <Button label="Add to manifest" onPress={onSave} loading={saving} fullWidth />
      <View style={{ height: 8 }} />
      <Button label="Cancel" variant="ghost" fullWidth onPress={close} />
    </Modal>
  );
}

const s = StyleSheet.create({
  headRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 10,
    marginTop: 4,
  },
  heading: { fontSize: 16, fontWeight: '700', color: '#0F172A' },
  headActions: { flexDirection: 'row' },
  addBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    marginLeft: 6,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 9999,
    borderWidth: 1,
    borderColor: '#0B3D91',
    backgroundColor: '#FFFFFF',
  },
  addBtnText: { fontSize: 12, fontWeight: '700', color: '#0B3D91', marginLeft: 4 },
  readOnly: { fontSize: 12, color: '#64748B', marginBottom: 8, lineHeight: 17 },
  card: {
    backgroundColor: '#F8FAFC',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    padding: 14,
  },
  emptyText: { color: '#64748B', fontSize: 13, lineHeight: 19 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
  },
  iconBox: {
    width: 30,
    height: 30,
    borderRadius: 8,
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#E2E8F0',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
  },
  name: { fontSize: 14, fontWeight: '700', color: '#0F172A' },
  sub: { fontSize: 12, color: '#64748B', marginTop: 2 },
  deleteBtn: { marginLeft: 10, padding: 4 },
  more: { paddingVertical: 10 },
  moreText: { color: '#0B3D91', fontWeight: '600', fontSize: 13 },
  input: {
    height: 44,
    paddingHorizontal: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#CBD5E1',
    backgroundColor: '#FFFFFF',
    fontSize: 15,
    color: '#0F172A',
  },
});
