import React, { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { UserCog } from 'lucide-react-native';
import { useUpdateDriver } from '@/lib/queries';
import { useToast } from '@/components/ui/Toast';
import { Modal } from '@/components/ui/Modal';
import { Field } from '@/components/ui/Field';
import { Button } from '@/components/ui/Button';
import { STAFF_STATUSES, type Driver, type StaffStatus } from '@/lib/types';

export interface EditDriverModalProps {
  visible: boolean;
  onClose: () => void;
  onSaved?: () => void;
  driver: Driver;
}

const STATUS_LABELS: Record<StaffStatus, string> = {
  active: 'Active',
  suspended: 'Suspended',
  on_leave: 'On leave',
};

export function EditDriverModal({ visible, onClose, onSaved, driver }: EditDriverModalProps) {
  const update = useUpdateDriver(driver.id);
  const toast = useToast();
  const [licenseNo, setLicenseNo] = useState('');
  const [licenseExpiry, setLicenseExpiry] = useState('');
  const [years, setYears] = useState('0');
  const [status, setStatus] = useState<StaffStatus>('active');

  useEffect(() => {
    if (!visible) return;
    setLicenseNo(driver.license_no);
    setLicenseExpiry(driver.license_expiry ? driver.license_expiry.slice(0, 10) : '');
    setYears(String(driver.years_experience ?? 0));
    setStatus(driver.status);
  }, [visible, driver]);

  const close = () => onClose();

  const onSubmit = async () => {
    if (!licenseNo.trim()) return toast.error('License number is required');
    if (!licenseExpiry.trim()) return toast.error('License expiry date is required');
    const expiry = new Date(licenseExpiry);
    if (Number.isNaN(expiry.getTime())) return toast.error('Expiry date is invalid');
    const yearsN = parseInt(years, 10);
    if (!Number.isFinite(yearsN) || yearsN < 0) return toast.error('Years of experience must be ≥ 0');
    try {
      await update.mutateAsync({
        license_no: licenseNo.trim().toUpperCase(),
        license_expiry: expiry.toISOString(),
        years_experience: yearsN,
        status,
      });
      toast.success('Driver updated');
      onSaved?.();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not update driver');
    }
  };

  return (
    <Modal visible={visible} onClose={close} title="Edit driver" variant="sheet">
      <View style={s.infoBanner}>
        <UserCog size={18} color="#0E7490" />
        <Text style={s.infoText}>The linked user account can't be changed here — create a new driver record to link a different account.</Text>
      </View>
      <Field label="License number" required>
        <TextInput style={s.input} value={licenseNo} onChangeText={setLicenseNo} placeholder="Lagos-12345" placeholderTextColor="#94A3B8" autoCapitalize="characters" autoCorrect={false} />
      </Field>
      <View style={s.row}>
        <View style={s.col}>
          <Field label="License expiry" required helperText="YYYY-MM-DD">
            <TextInput style={s.input} value={licenseExpiry} onChangeText={setLicenseExpiry} placeholder="2029-12-31" placeholderTextColor="#94A3B8" autoCapitalize="none" />
          </Field>
        </View>
        <View style={s.col}>
          <Field label="Years exp.">
            <TextInput style={s.input} value={years} onChangeText={setYears} placeholder="0" placeholderTextColor="#94A3B8" keyboardType="numeric" />
          </Field>
        </View>
      </View>
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
  row: { flexDirection: 'row', marginHorizontal: -6 },
  col: { flex: 1, paddingHorizontal: 6 },
  spacerL: { height: 12 },
  spacerS: { height: 8 },
});
