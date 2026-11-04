import React, { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { MapPin } from 'lucide-react-native';
import { useUpdateConductor } from '@/lib/queries';
import { useToast } from '@/components/ui/Toast';
import { Modal } from '@/components/ui/Modal';
import { Field } from '@/components/ui/Field';
import { Button } from '@/components/ui/Button';
import { STAFF_STATUSES, type Conductor, type StaffStatus } from '@/lib/types';

export interface EditConductorModalProps {
  visible: boolean;
  onClose: () => void;
  onSaved?: () => void;
  conductor: Conductor;
}

const STATUS_LABELS: Record<StaffStatus, string> = {
  active: 'Active',
  suspended: 'Suspended',
  on_leave: 'On leave',
};

export function EditConductorModal({ visible, onClose, onSaved, conductor }: EditConductorModalProps) {
  const update = useUpdateConductor(conductor.id);
  const toast = useToast();
  const [badgeNo, setBadgeNo] = useState('');
  const [status, setStatus] = useState<StaffStatus>('active');

  useEffect(() => {
    if (!visible) return;
    setBadgeNo(conductor.badge_no);
    setStatus(conductor.status);
  }, [visible, conductor]);

  const close = () => onClose();

  const onSubmit = async () => {
    if (!badgeNo.trim()) return toast.error('Badge number is required');
    if (!/^[A-Z0-9-]+$/.test(badgeNo.trim().toUpperCase())) {
      return toast.error('Badge must be uppercase letters / digits / dashes');
    }
    try {
      await update.mutateAsync({ badge_no: badgeNo.trim().toUpperCase(), status });
      toast.success('Conductor updated');
      onSaved?.();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not update conductor');
    }
  };

  return (
    <Modal visible={visible} onClose={close} title="Edit conductor" variant="sheet">
      <View style={s.infoBanner}>
        <MapPin size={18} color="#0E7490" />
        <Text style={s.infoText}>The linked user account can't be changed here — create a new conductor record to link a different account.</Text>
      </View>
      <Field label="Badge number" required helperText="Uppercase letters, digits, dashes (e.g. CON-001)">
        <TextInput style={s.input} value={badgeNo} onChangeText={setBadgeNo} placeholder="CON-001" placeholderTextColor="#94A3B8" autoCapitalize="characters" autoCorrect={false} />
      </Field>
      <Field label="Status" required>
        <View style={s.chipRow}>
          {STAFF_STATUSES.map((st) => {
            const active = status === st;
            return (
              <Pressable key={st} onPress={() => setStatus(st)} style={[s.chip, active && s.chipActive]} accessibilityRole="button" accessibilityState={{ selected: active }}>
                <Text style={[s.chipText, active && s.chipTextActive]}>{STATUS_LABELS[st]}</Text>
              </Pressable>
            );
          })}
        </View>
      </Field>
      <View style={s.spacerL} />
      <Button label="Save changes" onPress={onSubmit} loading={update.isPending} fullWidth />
      <View style={s.spacerS} />
      <Button label="Cancel" onPress={close} variant="ghost" fullWidth />
    </Modal>
  );
}

const s = StyleSheet.create({
  infoBanner: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#ECFEFF', borderRadius: 12, padding: 12, marginBottom: 12 },
  infoText: { fontSize: 13, color: '#0B3D91', marginLeft: 8, flex: 1 },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap' },
  chip: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 9999, marginRight: 6, marginBottom: 6, backgroundColor: '#F1F5F9' },
  chipActive: { backgroundColor: '#0B3D91' },
  chipText: { fontSize: 12, fontWeight: '500', color: '#334155' },
  chipTextActive: { color: '#FFFFFF' },
  input: { height: 48, paddingHorizontal: 12, borderRadius: 12, borderWidth: 1, borderColor: '#E2E8F0', backgroundColor: '#FFFFFF', fontSize: 16, color: '#0F172A' },
  spacerL: { height: 12 },
  spacerS: { height: 8 },
});
