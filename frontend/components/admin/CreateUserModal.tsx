import React, { useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { KeyRound } from 'lucide-react-native';
import { useBranches, useCreateUser } from '@/lib/queries';
import { useToast } from '@/components/ui/Toast';
import { Modal } from '@/components/ui/Modal';
import { Field } from '@/components/ui/Field';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { ROLES, ROLE_LABELS, type Role } from '@/lib/types';

export interface CreateUserModalProps {
  visible?: boolean;
  open?: boolean;
  onClose: () => void;
  onSaved?: () => void;
}

function generateTempPassword(): string {
  const lower = 'abcdefghjkmnpqrstuvwxyz';
  const upper = 'ABCDEFGHJKMNPQRSTUVWXYZ';
  const digits = '23456789';
  const special = '#@%*';
  const all = lower + upper + digits + special;
  const pick = (s: string) => s[Math.floor(Math.random() * s.length)];
  let out = [pick(lower), pick(upper), pick(digits), pick(special)];
  for (let i = 0; i < 8; i++) out.push(pick(all));
  out = out.sort(() => Math.random() - 0.5);
  return out.join('');
}

export function CreateUserModal({ visible, open, onClose, onSaved }: CreateUserModalProps) {
  const show = !!(visible ?? open);
  const create = useCreateUser();
  const toast = useToast();
  const branchesQ = useBranches({ page: 1, page_size: 100 });
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [role, setRole] = useState<Role | null>(null);
  const [branchId, setBranchId] = useState<string | null>(null);
  const [tempPassword, setTempPassword] = useState('');

  const reset = () => { setFullName(''); setEmail(''); setPhone(''); setRole(null); setBranchId(null); setTempPassword(''); };
  const close = () => { reset(); onClose(); };

  const branchOptions = (branchesQ.data?.items ?? []).map((b) => ({ label: b.name, value: b.id }));

  const onSubmit = async () => {
    if (!fullName.trim()) return toast.error('Full name is required');
    if (!email.trim()) return toast.error('Email is required');
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) return toast.error('Email looks invalid');
    if (!role) return toast.error('Role is required');
    if (!branchId) return toast.error('Branch is required');
    const pwd = tempPassword || generateTempPassword();
    try {
      await create.mutateAsync({
        full_name: fullName.trim(),
        email: email.trim().toLowerCase(),
        phone: phone.trim() || null,
        role,
        branch_id: branchId,
        password: pwd,
      });
      toast.success(`User invited. Temporary password: ${pwd}`);
      reset();
      onSaved?.();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not create user');
    }
  };

  return (
    <Modal visible={show} onClose={close} title="New user" variant="sheet">
      <View style={s.infoBanner}>
        <KeyRound size={18} color="#0E7490" />
        <Text style={s.infoText}>
          A temporary password is generated for the new user. They must change it at first sign-in.
        </Text>
      </View>
      <Field label="Full name" required>
        <TextInput style={s.input} value={fullName} onChangeText={setFullName} placeholder="Jane Doe" placeholderTextColor="#94A3B8" />
      </Field>
      <View style={s.row}>
        <View style={s.col}>
          <Field label="Email" required>
            <TextInput style={s.input} value={email} onChangeText={setEmail} placeholder="jane@company.com" placeholderTextColor="#94A3B8" autoCapitalize="none" keyboardType="email-address" />
          </Field>
        </View>
        <View style={s.col}>
          <Field label="Phone">
            <TextInput style={s.input} value={phone} onChangeText={setPhone} placeholder="+234…" placeholderTextColor="#94A3B8" keyboardType="phone-pad" />
          </Field>
        </View>
      </View>
      <Field label="Role" required>
        <View style={s.chipRow}>
          {ROLES.map((r) => {
            const active = role === r;
            return (
              <Pressable key={r} onPress={() => setRole(r)} style={[s.chip, active && s.chipActive]} accessibilityRole="button" accessibilityState={{ selected: active }}>
                <Text style={[s.chipText, active && s.chipTextActive]}>{ROLE_LABELS[r]}</Text>
              </Pressable>
            );
          })}
        </View>
      </Field>
      <Field label="Branch" required>
        <Select value={branchId} onChange={setBranchId} options={branchOptions} placeholder="Select branch" />
      </Field>
      <Field label="Temporary password" helperText="Auto-generated — you can edit it, or tap regenerate">
        <View style={s.row}>
          <View style={s.col}>
            <TextInput style={s.input} value={tempPassword} onChangeText={setTempPassword} placeholder="e.g. Ab3#xK9pQ2" placeholderTextColor="#94A3B8" autoCapitalize="none" autoCorrect={false} />
          </View>
          <View style={s.col}>
            <Button label="Regenerate" onPress={() => setTempPassword(generateTempPassword())} variant="secondary" />
          </View>
        </View>
      </Field>
      <View style={s.spacerL} />
      <Button label="Create user" onPress={onSubmit} loading={create.isPending} fullWidth />
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
