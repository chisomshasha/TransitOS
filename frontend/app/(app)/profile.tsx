import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Building2, LogOut, Mail, Phone, ShieldCheck, User as UserIcon } from 'lucide-react-native';
import { useAuth } from '@/lib/auth-context';
import { useBranches } from '@/lib/queries';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { ROLE_LABELS } from '@/lib/types';

export default function ProfileScreen() {
  const { user, logout } = useAuth();
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
      <Pressable
        onPress={() => { void logout(); }}
        style={s.signOut}
        accessibilityRole="button"
        accessibilityLabel="Sign out"
      >
        <LogOut size={16} color="#FFFFFF" />
        <Text style={s.signOutText}>Sign out</Text>
      </Pressable>
      <Text style={s.version}>TransitOS v1.1.0</Text>
    </ScrollView>
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
  signOut: {
    height: 48, borderRadius: 12, backgroundColor: '#B91C1C',
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
  },
  signOutText: { color: '#FFFFFF', fontWeight: '600', marginLeft: 8 },
  version: { textAlign: 'center', fontSize: 12, color: '#A3A3A3', marginTop: 16 },
});
