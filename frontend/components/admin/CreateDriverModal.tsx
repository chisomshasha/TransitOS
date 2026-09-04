import React, { useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { UserCog } from 'lucide-react-native';
import { useBranches, useCreateDriver, useUsersByRole } from '@/lib/queries';
import { useToast } from '@/components/ui/Toast';
import { Modal } from '@/components/ui/Modal';
import { Field } from '@/components/ui/Field';
import { Button } from '@/components/ui/Button';

export interface CreateDriverModalProps {
  visible?: boolean;
  open?: boolean;
  onClose: () => void;
  onSaved?: () => void;
}

export function CreateDriverModal({ visible, open, onClose, onSaved }: CreateDriverModalProps) {
  const show = !!(visible ?? open);
  const create = useCreateDriver();
  const toast = useToast();
  const usersQ = useUsersByRole('driver');
  const branchesQ = useBranches({ page: 1, page_size: 100 });
  const [userId, setUserId] = useState('');
  const [licenseNo, setLicenseNo] = useState('');
  const [licenseExpiry, setLicenseExpiry] = useState('');
  const [years, setYears] = useState('0');

  const reset = () => { setUserId(''); setLicenseNo(''); setLicenseExpiry(''); setYears('0'); };
  const close = () => { reset(); onClose(); };

  const onSubmit = async () => {
    if (!userId) return toast.error('Pick the driver’s user account');
    if (!licenseNo.trim()) return toast.error('License number is required');
    if (!licenseExpiry.trim()) return toast.error('License expiry date is required');
    const expiry = new Date(licenseExpiry);
    if (Number.isNaN(expiry.getTime())) return toast.error('Expiry date is invalid');
    const yearsN = parseInt(years, 10);
    if (!Number.isFinite(yearsN) || yearsN < 0) return toast.error('Years of experience must be ≥ 0');
    try {
      await create.mutateAsync({
        user_id: userId,
        license_no: licenseNo.trim().toUpperCase(),
        license_expiry: expiry.toISOString(),
        years_experience: yearsN,
        status: 'active',
      });
      toast.success('Driver added');
      reset();
      onSaved?.();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not add driver');
    }
  };

  const userOptions = usersQ.data?.items ?? [];
  const selectedUser = userOptions.find((u) => u.id === userId);
  const selectedUserBranchName = selectedUser
    ? branchesQ.data?.items.find((b) => b.id === selectedUser.branch_id)?.name ?? '—'
    : null;

  return (
    <Modal visible={show} onClose={close} title="New driver" variant="sheet">
      <View style={s.infoBanner}>
        <UserCog size={18} color="#0E7490" />
        <Text style={s.infoText}>
          Drivers are linked to an existing user with role “Driver”. If none show up, invite the user first from the Users page.
        </Text>
      </View>
      <Field label="User" required helperText={userOptions.length === 0 ? 'No driver-role users yet — invite one first' : undefined}>
        {userOptions.length === 0 ? (
          <View style={s.warnBox}><Text style={s.warnText}>No driver users available</Text></View>
        ) : (
          <View style={s.chipRow}>
            {userOptions.map((u) => {
              const active = userId === u.id;
              return (
                <Pressable key={u.id} onPress={() => setUserId(u.id)} style={[s.chip, active && s.chipActive]} accessibilityRole="button" accessibilityState={{ selected: active }}>
                  <Text style={[s.chipText, active && s.chipTextActive]}>{u.full_name}</Text>
                </Pressable>
              );
            })}
          </View>
        )}
      </Field>
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
      {selectedUser ? (
        <View style={s.branchBox}>
          <Text style={s.branchLabel}>Branch (from this user's account)</Text>
          <Text style={s.branchValue}>{selectedUserBranchName}</Text>
        </View>
      ) : null}
      <View style={s.spacerL} />
      <Button label="Add driver" onPress={onSubmit} loading={create.isPending} fullWidth />
      <View style={s.spacerS} />
      <Button label="Cancel" onPress={close} variant="ghost" fullWidth />
    </Modal>
  );
}

const s = StyleSheet.create({
  infoBanner: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#ECFEFF', borderRadius: 12, padding: 12, marginBottom: 12 },
  infoText: { fontSize: 13, color: '#0B3D91', marginLeft: 8, flex: 1 },
  warnBox: { minHeight: 44, paddingHorizontal: 12, borderRadius: 12, borderWidth: 1, borderColor: '#FDE68A', backgroundColor: '#FFFBEB', alignItems: 'center', justifyContent: 'center' },
  warnText: { fontSize: 14, color: '#B45309' },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap' },
  chip: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 9999, marginRight: 6, marginBottom: 6, backgroundColor: '#F1F5F9' },
  chipActive: { backgroundColor: '#0B3D91' },
  chipText: { fontSize: 12, fontWeight: '500', color: '#334155' },
  chipTextActive: { color: '#FFFFFF' },
  input: { height: 48, paddingHorizontal: 12, borderRadius: 12, borderWidth: 1, borderColor: '#E2E8F0', backgroundColor: '#FFFFFF', fontSize: 16, color: '#0F172A' },
  row: { flexDirection: 'row', marginHorizontal: -6 },
  col: { flex: 1, paddingHorizontal: 6 },
  branchBox: { backgroundColor: '#F8FAFC', borderRadius: 12, paddingHorizontal: 12, paddingVertical: 10, marginBottom: 16 },
  branchLabel: { fontSize: 12, color: '#64748B' },
  branchValue: { fontSize: 14, fontWeight: '600', color: '#1E293B', marginTop: 2 },
  spacerL: { height: 12 },
  spacerS: { height: 8 },
});
