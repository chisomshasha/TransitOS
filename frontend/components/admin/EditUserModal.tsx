import React, { useEffect, useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { UserCog } from 'lucide-react-native';
import { useBranches, useUpdateUser } from '@/lib/queries';
import { useToast } from '@/components/ui/Toast';
import { Modal } from '@/components/ui/Modal';
import { Field } from '@/components/ui/Field';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { ROLE_LABELS, USER_STATUSES, type Role, type User, type UserStatus } from '@/lib/types';

export interface EditUserModalProps {
  visible: boolean;
  onClose: () => void;
  onSaved?: () => void;
  user: User;
  /** Roles the current actor is allowed to assign (server enforces this too). */
  assignableRoles: Role[];
}

const STATUS_LABELS: Record<UserStatus, string> = {
  active: 'Active',
  suspended: 'Suspended',
  pending: 'Pending',
};

export function EditUserModal({ visible, onClose, onSaved, user, assignableRoles }: EditUserModalProps) {
  const update = useUpdateUser(user.id);
  const toast = useToast();
  const branchesQ = useBranches({ page: 1, page_size: 100 });
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [role, setRole] = useState<Role>(user.role);
  const [branchId, setBranchId] = useState<string | null>(null);
  const [status, setStatus] = useState<UserStatus>('active');
  const [newPassword, setNewPassword] = useState('');

  useEffect(() => {
    if (!visible) return;
    setFullName(user.full_name);
    setPhone(user.phone ?? '');
    setRole(user.role);
    setBranchId(user.branch_id ?? null);
    setStatus(user.status);
    setNewPassword('');
  }, [visible, user]);

  const close = () => onClose();

  const branchOptions = (branchesQ.data?.items ?? []).map((b) => ({ label: b.name, value: b.id }));
  // Always include the user's current role even if the actor can't re-assign it,
  // so the picker never silently shows the wrong value.
  const roleChoices = assignableRoles.includes(role) ? assignableRoles : [role, ...assignableRoles];
  const roleOptions = roleChoices.map((r) => ({ label: ROLE_LABELS[r], value: r }));
  const statusOptions = USER_STATUSES.map((st) => ({ label: STATUS_LABELS[st], value: st }));

  const onSubmit = async () => {
    if (!fullName.trim()) return toast.error('Full name is required');
    if (newPassword && newPassword.length < 10) return toast.error('New password must be at least 10 characters');
    try {
      await update.mutateAsync({
        full_name: fullName.trim(),
        phone: phone.trim() || null,
        role,
        branch_id: branchId,
        status,
        ...(newPassword ? { new_password: newPassword } : {}),
      });
      toast.success(`${fullName.trim()} updated`);
      onSaved?.();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not update user');
    }
  };

  return (
    <Modal visible={visible} onClose={close} title="Edit user" variant="sheet">
      <View style={s.infoBanner}>
        <UserCog size={18} color="#0E7490" />
        <Text style={s.infoText}>Email can't be changed here. You can only assign a role at or below your own seniority.</Text>
      </View>
      <Field label="Full name" required>
        <TextInput style={s.input} value={fullName} onChangeText={setFullName} placeholder="Jane Doe" placeholderTextColor="#94A3B8" />
      </Field>
      <Field label="Phone">
        <TextInput style={s.input} value={phone} onChangeText={setPhone} placeholder="+234…" placeholderTextColor="#94A3B8" keyboardType="phone-pad" />
      </Field>
      <Field label="Role" required>
        <Select value={role} onChange={setRole} options={roleOptions} />
      </Field>
      <Field label="Branch" helperText="Leave unset for company-wide roles">
        <Select value={branchId} onChange={setBranchId} options={branchOptions} placeholder="No branch" />
      </Field>
      <Field label="Status" required>
        <View style={s.chipRow}>
          {USER_STATUSES.map((st) => {
            const active = status === st;
            return (
              <Pressable key={st} onPress={() => setStatus(st)} style={[s.chip, active && s.chipActive]} accessibilityRole="button" accessibilityState={{ selected: active }}>
                <Text style={[s.chipText, active && s.chipTextActive]}>{STATUS_LABELS[st]}</Text>
              </Pressable>
            );
          })}
        </View>
      </Field>
      <Field label="Reset password" helperText="Leave blank to keep the current password">
        <TextInput style={s.input} value={newPassword} onChangeText={setNewPassword} placeholder="New password (optional)" placeholderTextColor="#94A3B8" secureTextEntry autoCapitalize="none" />
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
