import React, { useState } from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';
import { CheckCircle2, CircleDot, XCircle } from 'lucide-react-native';
import { useChangeTripStatus } from '@/lib/queries';
import { useAuth } from '@/lib/auth-context';
import { canAccess } from '@/lib/rbac';
import { useToast } from '@/components/ui/Toast';
import { Button } from '@/components/ui/Button';
import { Modal } from '@/components/ui/Modal';
import { Field } from '@/components/ui/Field';
import { TRIP_STATUS_ACTIONS, TRIP_MUTATE_ROLES, tripStatusActions } from '@/lib/money-loop';
import { TRIP_STATUS_LABELS } from '@/lib/types';
import type { Trip, TripStatus } from '@/lib/types';

export interface TripStatusPanelProps {
  trip: Trip;
}

/**
 * Moves a trip through its lifecycle.
 *
 * The buttons are generated from the same transition table the backend
 * enforces (`TRIP_TRANSITIONS`), so the app can never offer a move the
 * server would reject. Cancelling always asks for a reason, because the
 * backend refuses a cancellation without one.
 */
export function TripStatusPanel({ trip }: TripStatusPanelProps) {
  const { user } = useAuth();
  const toast = useToast();
  const changeStatus = useChangeTripStatus(trip.id);
  const [cancelling, setCancelling] = useState(false);
  const [reason, setReason] = useState('');

  const canManage = canAccess(user?.role, TRIP_MUTATE_ROLES);
  const actions = tripStatusActions(trip.status);
  const terminal = actions.length === 0;

  const onAdvance = async (target: TripStatus) => {
    try {
      const body: { status: string; cancelled_reason?: string } = { status: target };
      if (target === 'cancelled') body.cancelled_reason = reason.trim();
      await changeStatus.mutateAsync(body);
      toast.success(`Trip marked ${TRIP_STATUS_LABELS[target].toLowerCase()}`);
      setCancelling(false);
      setReason('');
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not update the trip status');
    }
  };

  const onCancelPressed = () => {
    setReason('');
    setCancelling(true);
  };

  return (
    <View style={s.card} testID="trip-status-panel">
      <View style={s.header}>
        <CircleDot size={18} color="#0B3D91" />
        <Text style={s.title}>Trip status</Text>
        <View style={s.statusPill}>
          <Text style={s.statusText}>{TRIP_STATUS_LABELS[trip.status] ?? trip.status}</Text>
        </View>
      </View>

      {terminal ? (
        <View style={s.terminal}>
          {trip.status === 'cancelled' ? (
            <>
              <XCircle size={16} color="#B91C1C" />
              <Text style={s.terminalText}>
                This trip was cancelled
                {trip.cancelled_reason ? ` — ${trip.cancelled_reason}` : ''}.
              </Text>
            </>
          ) : trip.status === 'cashed_up' ? (
            <>
              <CheckCircle2 size={16} color="#047857" />
              <Text style={s.terminalText}>
                The cash-up for this trip was approved. Nothing more to do.
              </Text>
            </>
          ) : (
            <>
              <CheckCircle2 size={16} color="#B45309" />
              <Text style={s.terminalText}>
                This trip is closed. Record the cash-up below to finish the money loop.
              </Text>
            </>
          )}
        </View>
      ) : !canManage ? (
        <Text style={s.readOnly}>
          Only a branch manager, operations manager or administrator can move a trip
          through its stages.
        </Text>
      ) : (
        <View style={s.actions}>
          {actions.map((a) => {
            const spec = TRIP_STATUS_ACTIONS[a];
            if (a === 'cancelled') {
              return (
                <Button
                  key={a}
                  label={spec.label}
                  variant="danger"
                  fullWidth
                  onPress={onCancelPressed}
                  disabled={changeStatus.isPending}
                  testID="trip-status-cancel"
                />
              );
            }
            return (
              <View key={a} style={s.actionBlock}>
                <Text style={s.hint}>{spec.hint}</Text>
                <Button
                  label={spec.label}
                  onPress={() => onAdvance(a)}
                  loading={changeStatus.isPending}
                  fullWidth
                  testID="trip-status-advance"
                />
              </View>
            );
          })}
        </View>
      )}

      <Modal
        visible={cancelling}
        onClose={() => setCancelling(false)}
        title="Cancel trip"
        variant="sheet"
      >
        <Text style={s.modalText}>
          Cancelling a trip is recorded against your name in the audit log and cannot be
          undone. Tell the branch why the trip is being called off.
        </Text>
        <Field label="Reason for cancellation" required>
          <TextInput
            style={s.reasonInput}
            value={reason}
            onChangeText={setReason}
            placeholder="e.g. Vehicle breakdown at mile 12"
            multiline
            accessibilityLabel="Reason for cancellation"
          />
        </Field>
        <Button
          label="Cancel trip"
          variant="danger"
          fullWidth
          loading={changeStatus.isPending}
          disabled={reason.trim().length < 2}
          onPress={() => onAdvance('cancelled')}
        />
        <View style={{ height: 8 }} />
        <Button label="Keep trip" variant="ghost" fullWidth onPress={() => setCancelling(false)} />
      </Modal>
    </View>
  );
}

const s = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    padding: 16,
    marginBottom: 16,
  },
  header: { flexDirection: 'row', alignItems: 'center' },
  title: { flex: 1, fontSize: 16, fontWeight: '600', color: '#1E293B', marginLeft: 8 },
  statusPill: {
    backgroundColor: '#EFF6FF',
    borderRadius: 9999,
    paddingHorizontal: 10,
    paddingVertical: 3,
  },
  statusText: { fontSize: 12, fontWeight: '700', color: '#0B3D91' },
  actions: { marginTop: 12 },
  actionBlock: { marginTop: 8 },
  hint: { fontSize: 12, color: '#64748B', marginBottom: 8, lineHeight: 17 },
  readOnly: { fontSize: 12, color: '#64748B', marginTop: 10, lineHeight: 18 },
  terminal: { flexDirection: 'row', alignItems: 'flex-start', marginTop: 10 },
  terminalText: { flex: 1, fontSize: 12, color: '#475569', marginLeft: 8, lineHeight: 18 },
  modalText: { fontSize: 13, color: '#475569', marginBottom: 16, lineHeight: 19 },
  reasonInput: {
    minHeight: 80,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#CBD5E1',
    backgroundColor: '#FFFFFF',
    fontSize: 14,
    color: '#0F172A',
    textAlignVertical: 'top',
  },
});
