import React from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { useBranches, useUsers } from '@/lib/queries';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { User, Mail, Phone, Building2 } from 'lucide-react-native';
import { ROLE_LABELS } from '@/lib/types';

export default function UserDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data, isLoading } = useUsers({ page: 1, page_size: 200 });
  const branchesQ = useBranches({ page: 1, page_size: 200 });
  const u = (data?.items ?? []).find((x) => x.id === id);

  if (isLoading) return <View style={s.loading}><Spinner label="Loading user…" /></View>;
  if (!u) return <View style={s.loading}><Text style={s.errorText}>User not found</Text></View>;

  const branchName = branchesQ.data?.items.find((b) => b.id === u.branch_id)?.name ?? '—';

  return (
    <ScrollView style={s.root} contentContainerStyle={{ padding: 16 }}>
      <Card>
        <View style={s.header}>
          <View style={s.avatar}>
            <User size={28} color="#0E7490" />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={s.name}>{u.full_name}</Text>
            <Badge label={ROLE_LABELS[u.role] ?? u.role} tone="primary" />
          </View>
          <Badge
            label={u.is_active ? 'active' : 'inactive'}
            tone={u.is_active ? 'success' : 'neutral'}
          />
        </View>
        <View style={s.divider} />
        <InfoRow icon={<Mail size={14} color="#64748B" />} label="Email" value={u.email} />
        <InfoRow icon={<Phone size={14} color="#64748B" />} label="Phone" value={u.phone ?? '—'} />
        <InfoRow icon={<Building2 size={14} color="#64748B" />} label="Branch" value={branchName} />
      </Card>
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
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  errorText: { fontSize: 16, color: '#B91C1C' },
  header: { flexDirection: 'row', alignItems: 'center' },
  avatar: { width: 56, height: 56, borderRadius: 28, backgroundColor: '#ECFEFF', alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  name: { fontSize: 18, fontWeight: '700', color: '#171717', marginBottom: 4 },
  divider: { height: 1, backgroundColor: '#E5E7EB', marginVertical: 16 },
  infoRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 6 },
  infoLabel: { fontSize: 13, color: '#64748B', width: 80, marginLeft: 8 },
  infoValue: { fontSize: 13, fontWeight: '500', color: '#171717', flex: 1 },
});
