import React from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { useRoute } from 'expo-router';
import { UserCog, Mail, Phone, Building2, CreditCard, CalendarDays } from 'lucide-react-native';
import { useBranches, useDrivers } from '@/lib/queries';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';

export default function DriverDetailScreen() {
  const route = useRoute();
  const id = (route.params as { id: string })?.id;
  const { data, isLoading } = useDrivers({ page: 1, page_size: 200 });
  const branchesQ = useBranches({ page: 1, page_size: 200 });
  const d = (data?.items ?? []).find((x) => x.id === id);

  if (isLoading) return <View style={s.loading}><Spinner label="Loading driver…" /></View>;
  if (!d) return <View style={s.loading}><Text style={s.errorText}>Driver not found</Text></View>;

  const branchName = d.user?.branch_id
    ? branchesQ.data?.items.find((b) => b.id === d.user?.branch_id)?.name ?? '—'
    : '—';
  const expiry = d.license_expiry ? new Date(d.license_expiry) : null;

  return (
    <ScrollView style={s.root} contentContainerStyle={{ padding: 16 }}>
      <Card>
        <View style={s.header}>
          <View style={s.avatar}><UserCog size={24} color="#0E7490" /></View>
          <View style={{ flex: 1 }}>
            <Text style={s.name}>{d.user?.full_name ?? 'Unnamed driver'}</Text>
            <Text style={s.sub}>{d.user?.email ?? ''}</Text>
          </View>
          <Badge
            label={d.status === 'active' ? 'active' : d.status}
            tone={d.status === 'active' ? 'success' : 'warning'}
          />
        </View>
        <View style={s.divider} />
        <InfoRow icon={<CreditCard size={14} color="#64748B" />} label="License no." value={d.license_no} />
        <InfoRow
          icon={<CalendarDays size={14} color="#64748B" />}
          label="License expiry"
          value={expiry ? expiry.toLocaleDateString() : '—'}
        />
        <InfoRow icon={<UserCog size={14} color="#64748B" />} label="Years exp." value={String(d.years_experience ?? 0)} />
        <InfoRow icon={<Mail size={14} color="#64748B" />} label="Email" value={d.user?.email ?? '—'} />
        <InfoRow icon={<Phone size={14} color="#64748B" />} label="Phone" value={d.user?.phone ?? '—'} />
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
  avatar: { width: 48, height: 48, borderRadius: 8, backgroundColor: '#ECFEFF', alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  name: { fontSize: 18, fontWeight: '700', color: '#171717' },
  sub: { fontSize: 13, color: '#737373', marginTop: 2 },
  divider: { height: 1, backgroundColor: '#E5E7EB', marginVertical: 16 },
  infoRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 6 },
  infoLabel: { fontSize: 13, color: '#64748B', width: 110, marginLeft: 8 },
  infoValue: { fontSize: 13, fontWeight: '500', color: '#171717', flex: 1 },
});
