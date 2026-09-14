import React, { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { useBranches } from '@/lib/queries';
import { useAuth } from '@/lib/auth-context';
import { canAccess } from '@/lib/rbac';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { CreateBranchModal } from '@/components/admin/CreateBranchModal';
import { Building2, MapPin, Phone, Mail, Pencil } from 'lucide-react-native';
import type { Role } from '@/lib/types';

const BRANCH_EDITOR_ROLES: Role[] = [
  'super_admin', 'owner', 'general_manager', 'branch_manager',
];

export default function BranchDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user } = useAuth();
  const { data, isLoading } = useBranches({ page: 1, page_size: 100 });
  const branch = (data?.items ?? []).find((b) => b.id === id);
  const [editOpen, setEditOpen] = useState(false);

  if (isLoading) {
    return <View style={s.loading}><Spinner label="Loading branch…" /></View>;
  }
  if (!branch) {
    return (
      <View style={s.loading}>
        <Text style={s.errorText}>Branch not found</Text>
      </View>
    );
  }

  const canEdit = canAccess(user?.role, BRANCH_EDITOR_ROLES);

  return (
    <ScrollView style={s.root} contentContainerStyle={{ padding: 16 }}>
      <Card>
        <View style={s.header}>
          <View style={s.iconBox}><Building2 size={24} color="#0E7490" /></View>
          <View style={{ flex: 1 }}>
            <Text style={s.name}>{branch.name}</Text>
            <Text style={s.code}>{branch.code}</Text>
          </View>
          <Badge
            label={branch.is_active ? 'active' : 'inactive'}
            tone={branch.is_active ? 'success' : 'neutral'}
          />
        </View>
        {canEdit ? (
          <Pressable style={s.editBtn} onPress={() => setEditOpen(true)}>
            <Pencil size={14} color="#0B3D91" />
            <Text style={s.editBtnText}>Edit details</Text>
          </Pressable>
        ) : null}
        <View style={s.divider} />
        <InfoRow icon={<MapPin size={14} color="#64748B" />} label="Address" value={branch.address || '—'} />
        <InfoRow icon={<MapPin size={14} color="#64748B" />} label="City" value={branch.city} />
        <InfoRow icon={<MapPin size={14} color="#64748B" />} label="State" value={branch.state} />
        <InfoRow icon={<Phone size={14} color="#64748B" />} label="Phone" value={branch.contact_phone || '—'} />
        <InfoRow icon={<Mail size={14} color="#64748B" />} label="Email" value={branch.contact_email || '—'} />
      </Card>

      <CreateBranchModal
        editing={branch}
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
  iconBox: { width: 48, height: 48, borderRadius: 8, backgroundColor: '#ECFEFF', alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  name: { fontSize: 18, fontWeight: '700', color: '#171717' },
  code: { fontSize: 13, color: '#737373', marginTop: 2 },
  divider: { height: 1, backgroundColor: '#E5E7EB', marginVertical: 16 },
  infoRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 6 },
  infoLabel: { fontSize: 13, color: '#64748B', width: 80, marginLeft: 8 },
  infoValue: { fontSize: 13, fontWeight: '500', color: '#171717', flex: 1 },
});
