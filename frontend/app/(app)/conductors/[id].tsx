import React, { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { MapPin, Mail, Phone, Building2, CreditCard, Pencil } from 'lucide-react-native';
import { useBranches, useConductors } from '@/lib/queries';
import { useAuth } from '@/lib/auth-context';
import { canAccess } from '@/lib/rbac';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { EditConductorModal } from '@/components/admin/EditConductorModal';
import type { Role } from '@/lib/types';

const EDIT_ROLES: Role[] = [
  'super_admin', 'owner', 'general_manager',
  'branch_manager', 'fleet_manager', 'operations_manager',
];

export default function ConductorDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user } = useAuth();
  const { data, isLoading } = useConductors({ page: 1, page_size: 200 });
  const branchesQ = useBranches({ page: 1, page_size: 200 });
  const c = (data?.items ?? []).find((x) => x.id === id);
  const [editOpen, setEditOpen] = useState(false);

  if (isLoading) return <View style={s.loading}><Spinner label="Loading conductor…" /></View>;
  if (!c) return <View style={s.loading}><Text style={s.errorText}>Conductor not found</Text></View>;

  const branchName = c.branch_id
    ? branchesQ.data?.items.find((b) => b.id === c.branch_id)?.name ?? '—'
    : '—';
  const canEdit = canAccess(user?.role, EDIT_ROLES);

  return (
    <ScrollView style={s.root} contentContainerStyle={{ padding: 16 }}>
      <Card>
        <View style={s.header}>
          <View style={s.avatar}><MapPin size={24} color="#0E7490" /></View>
          <View style={{ flex: 1 }}>
            <Text style={s.name}>{c.full_name ?? 'Unnamed conductor'}</Text>
            <Text style={s.sub}>Badge {c.badge_no}</Text>
          </View>
          <Badge
            label={c.status === 'active' ? 'active' : c.status}
            tone={c.status === 'active' ? 'success' : 'warning'}
          />
        </View>
        {canEdit ? (
          <Pressable style={s.editBtn} onPress={() => setEditOpen(true)}>
            <Pencil size={14} color="#0B3D91" />
            <Text style={s.editBtnText}>Edit details</Text>
          </Pressable>
        ) : null}
        <View style={s.divider} />
        <InfoRow icon={<CreditCard size={14} color="#64748B" />} label="Badge no." value={c.badge_no} />
        <InfoRow icon={<Mail size={14} color="#64748B" />} label="Email" value={c.email ?? '—'} />
        <InfoRow icon={<Phone size={14} color="#64748B" />} label="Phone" value={c.phone ?? '—'} />
        <InfoRow icon={<Building2 size={14} color="#64748B" />} label="Branch" value={branchName} />
      </Card>

      <EditConductorModal
        conductor={c}
        visible={editOpen}
        onClose={() => setEditOpen(false)}
        onSaved={() => setEditOpen(false)}
      />
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
  editBtn: { flexDirection: 'row', alignItems: 'center', alignSelf: 'flex-start', marginTop: 10, paddingVertical: 6, paddingHorizontal: 10, borderRadius: 8, backgroundColor: '#ECFEFF' },
  editBtnText: { fontSize: 12.5, fontWeight: '700', color: '#0B3D91', marginLeft: 5 },
  avatar: { width: 48, height: 48, borderRadius: 8, backgroundColor: '#ECFEFF', alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  name: { fontSize: 18, fontWeight: '700', color: '#171717' },
  sub: { fontSize: 13, color: '#737373', marginTop: 2 },
  divider: { height: 1, backgroundColor: '#E5E7EB', marginVertical: 16 },
  infoRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 6 },
  infoLabel: { fontSize: 13, color: '#64748B', width: 110, marginLeft: 8 },
  infoValue: { fontSize: 13, fontWeight: '500', color: '#171717', flex: 1 },
});
