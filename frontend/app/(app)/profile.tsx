import React, { useState } from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import {
  Building2,
  KeyRound,
  LogOut,
  Mail,
  Phone,
  ShieldCheck,
  User as UserIcon,
} from 'lucide-react-native';
import { useAuth } from '@/lib/auth-context';
import { useBranches } from '@/lib/queries';
import { getErrorMessage, postNoContent } from '@/lib/api';
import { checkPasswordStrength } from '@/lib/password';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { useToast } from '@/components/ui/Toast';
import { ROLE_LABELS } from '@/lib/types';

export default function ProfileScreen() {
  const { user, logout } = useAuth();
  const toast = useToast();
  const branchesQ = useBranches({ page: 1, page_size: 200 });
  const branchName = user?.branch_id
    ? branchesQ.data?.items.find((b) => b.id === user.branch_id)?.name ?? '—'
    : 'Platform-wide';
  const roleLabel = user?.role ? ROLE_LABELS[user.role] ?? user.role : '—';

  return (
    <ScrollView style={s.root} contentContainerStyle={{ padding: 16 }}>
      <Card>
        <View style={s.header}>
          <View style={s.avatar}><UserIcon size={28} color="#0E7490" /></View>
          <View style={{ flex: 1 }}>
            <Text style={s.name}>{user?.full_name ?? '—'}</Text>
            <Text style={s.sub}>{user?.email ?? ''}</Text>
          </View>
          <Badge label={roleLabel} tone="primary" />
        </View>
        <View style={s.divider} />
        <InfoRow icon={<Mail size={14} color="#64748B" />} label="Email" value={user?.email ?? '—'} />
        <InfoRow icon={<Phone size={14} color="#64748B" />} label="Phone" value={user?.phone ?? '—'} />
        <InfoRow icon={<Building2 size={14} color="#64748B" />} label="Branch" value={branchName} />
        <InfoRow icon={<ShieldCheck size={14} color="#64748B" />} label="Role" value={roleLabel} />
      </Card>

      <View style={{ height: 16 }} />
      <ChangePasswordCard />

      <View style={{ height: 16 }} />
      <Pressable
        onPress={() => { void logout(); }}
        style={s.signOut}
        accessibilityRole="button"
        accessibilityLabel="Sign out"
      >
        <LogOut size={16} color="#FFFFFF" />
        <Text style={s.signOutText}>Sign out</Text>
      </Pressable>
      <Text style={s.version}>TransitOS v1.2.0</Text>
    </ScrollView>
  );
}

/**
 * Self-service password change.
 *
 * Calls `POST /auth/change-password` (current_password, new_password).
 * The backend revokes every refresh token on success, so the session
 * ends and the user signs in again with the new password.
 */
function ChangePasswordCard() {
  const toast = useToast();
  const { logout } = useAuth();

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async () => {
    if (!currentPassword) {
      return setError('Enter your current password.');
    }
    const weakness = checkPasswordStrength(newPassword);
    if (weakness) return setError(weakness);
    if (newPassword !== confirmPassword) {
      return setError('New passwords do not match.');
    }
    if (newPassword === currentPassword) {
      return setError('New password must be different from the current one.');
    }

    setSubmitting(true);
    setError(null);
    try {
      await postNoContent('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      toast.success('Password changed. Please sign in again.');
      // The backend revoked all refresh tokens for this user, so the
      // current session is dead — log out cleanly instead of leaving
      // the user on a screen whose next request will 401.
      await logout();
    } catch (e) {
      setError(getErrorMessage(e, 'Could not change your password.'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card>
      <View style={s.changeHeader}>
        <KeyRound size={18} color="#0B3D91" />
        <Text style={s.changeTitle}>Change password</Text>
      </View>
      <Text style={s.changeHint}>
        10+ characters with an uppercase letter, a lowercase letter, a number and a symbol.
        You will be signed out on every device afterwards.
      </Text>

      <Text style={s.changeLabel}>CURRENT PASSWORD</Text>
      <TextInput
        style={s.changeInput}
        value={currentPassword}
        onChangeText={setCurrentPassword}
        placeholder="Your current password"
        placeholderTextColor="#94A3B8"
        secureTextEntry
        autoCapitalize="none"
        autoCorrect={false}
        textContentType="password"
      />

      <Text style={s.changeLabel}>NEW PASSWORD</Text>
      <TextInput
        style={s.changeInput}
        value={newPassword}
        onChangeText={setNewPassword}
        placeholder="10+ chars · upper, lower, number, symbol"
        placeholderTextColor="#94A3B8"
        secureTextEntry
        autoCapitalize="none"
        autoCorrect={false}
        textContentType="newPassword"
      />

      <Text style={s.changeLabel}>CONFIRM NEW PASSWORD</Text>
      <TextInput
        style={s.changeInput}
        value={confirmPassword}
        onChangeText={setConfirmPassword}
        placeholder="Repeat the new password"
        placeholderTextColor="#94A3B8"
        secureTextEntry
        autoCapitalize="none"
        autoCorrect={false}
        textContentType="newPassword"
        onSubmitEditing={() => { void onSubmit(); }}
      />

      {error ? <Text style={s.changeError}>{error}</Text> : null}

      <Pressable
        onPress={() => { void onSubmit(); }}
        disabled={submitting}
        style={({ pressed }) => [
          s.changeButton,
          submitting ? { opacity: 0.6 } : null,
          pressed && !submitting ? { opacity: 0.85 } : null,
        ]}
        accessibilityRole="button"
        accessibilityLabel="Change password"
      >
        <Text style={s.changeButtonText}>{submitting ? 'Updating…' : 'Update password'}</Text>
      </Pressable>
    </Card>
  );
}

function InfoRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <View style={s.infoRow}>
      {icon}
      <Text style={s.infoLabel}>{label}</Text>
      <Text style={s.infoValue}>{value}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F8F7F4' },
  header: { flexDirection: 'row', alignItems: 'center' },
  avatar: { width: 56, height: 56, borderRadius: 28, backgroundColor: '#ECFEFF', alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  name: { fontSize: 18, fontWeight: '700', color: '#171717', marginBottom: 2 },
  sub: { fontSize: 13, color: '#737373' },
  divider: { height: 1, backgroundColor: '#E5E7EB', marginVertical: 16 },
  infoRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 6 },
  infoLabel: { fontSize: 13, color: '#64748B', width: 80, marginLeft: 8 },
  infoValue: { fontSize: 13, fontWeight: '500', color: '#171717', flex: 1 },
  changeHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 6 },
  changeTitle: { fontSize: 16, fontWeight: '700', color: '#171717', marginLeft: 8 },
  changeHint: { fontSize: 12, color: '#64748B', marginBottom: 14, lineHeight: 17 },
  changeLabel: { fontSize: 11, fontWeight: '700', color: '#64748B', letterSpacing: 0.6, marginBottom: 6, marginTop: 10 },
  changeInput: {
    borderWidth: 1,
    borderColor: '#E2E8F0',
    backgroundColor: '#F8FAFC',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 11,
    fontSize: 14,
    color: '#0F172A',
  },
  changeError: { fontSize: 13, color: '#B91C1C', marginTop: 12, fontWeight: '500' },
  changeButton: {
    marginTop: 16,
    height: 46,
    borderRadius: 12,
    backgroundColor: '#0B3D91',
    alignItems: 'center',
    justifyContent: 'center',
  },
  changeButtonText: { color: '#FFFFFF', fontWeight: '700', fontSize: 14 },
  signOut: {
    height: 48, borderRadius: 12, backgroundColor: '#B91C1C',
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
  },
  signOutText: { color: '#FFFFFF', fontWeight: '600', marginLeft: 8 },
  version: { textAlign: 'center', fontSize: 12, color: '#A3A3A3', marginTop: 16 },
});
