import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Stack, useRouter } from 'expo-router';
import {
  ArrowRightLeft,
  BarChart3,
  Bell,
  Bus,
  ClipboardList,
  FileText,
  Fuel,
  LayoutGrid,
  MapPin,
  RefreshCw,
  Route as RouteIcon,
  Truck,
  User,
  Users,
  Wallet,
  Wrench,
} from 'lucide-react-native';
import { useAuth } from '@/lib/auth-context';
import { canAccess } from '@/lib/rbac';
import { Badge } from '@/components/ui/Badge';
import { ROLE_LABELS } from '@/lib/types';
import { brand } from '@/lib/theme';

interface Tile {
  key: string;
  label: string;
  sub: string;
  href: string;
  icon: React.ReactNode;
  iconBg: string;
  show: boolean;
}

export default function MoreScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const role = user?.role;

  const mgmt = canAccess(role, ['super_admin', 'owner', 'general_manager', 'branch_manager', 'operations_manager']);
  const fleet = canAccess(role, ['super_admin', 'owner', 'general_manager', 'branch_manager', 'fleet_manager']);
  const finance = canAccess(role, ['super_admin', 'owner', 'general_manager', 'branch_manager', 'chief_accountant', 'branch_accountant']);
  const topAdmin = canAccess(role, ['super_admin', 'owner', 'general_manager']);

  const sections: { title: string; tiles: Tile[] }[] = [
    {
      title: 'Operations',
      tiles: [
        { key: 'trips', label: 'Trips', sub: 'Schedule & live', href: '/trips', icon: <Bus size={20} color="#0B3D91" />, iconBg: '#DBEAFE', show: true },
        { key: 'vehicles', label: 'Vehicles', sub: 'Fleet & docs', href: '/vehicles', icon: <Truck size={20} color="#B45309" />, iconBg: '#FEF3C7', show: fleet },
        { key: 'users', label: 'Users', sub: 'Staff & roles', href: '/users', icon: <Users size={20} color="#047857" />, iconBg: '#D1FAE5', show: mgmt },
        { key: 'routes', label: 'Routes', sub: 'Lines & fares', href: '/routes', icon: <RouteIcon size={20} color="#2563EB" />, iconBg: '#DBEAFE', show: fleet },
        { key: 'map', label: 'Live map', sub: 'Fleet positions', href: '/map', icon: <MapPin size={20} color="#1D4ED8" />, iconBg: '#DBEAFE', show: fleet },
        { key: 'transfers', label: 'Transfers', sub: 'Cross-branch', href: '/transfers', icon: <ArrowRightLeft size={20} color="#B45309" />, iconBg: '#FEF3C7', show: fleet },
      ],
    },
    {
      title: 'Finance',
      tiles: [
        { key: 'cashups', label: 'Cash Ups', sub: 'Approvals', href: '/cash-ups', icon: <Wallet size={20} color="#047857" />, iconBg: '#D1FAE5', show: finance || role === 'conductor' },
        { key: 'expenses', label: 'Expenses', sub: 'Costs', href: '/expenses', icon: <FileText size={20} color="#B91C1C" />, iconBg: '#FEE2E2', show: finance },
      ],
    },
    {
      title: 'Fleet',
      tiles: [
        { key: 'fuel', label: 'Fuel', sub: 'Logs & efficiency', href: '/fuel', icon: <Fuel size={20} color="#B45309" />, iconBg: '#FEF3C7', show: fleet },
        { key: 'maintenance', label: 'Maintenance', sub: 'Services due', href: '/maintenance', icon: <Wrench size={20} color="#0B3D91" />, iconBg: '#DBEAFE', show: fleet },
        { key: 'incidents', label: 'Incidents', sub: 'Reports', href: '/incidents', icon: <ClipboardList size={20} color="#B91C1C" />, iconBg: '#FEE2E2', show: fleet },
      ],
    },
    {
      title: 'System',
      tiles: [
        { key: 'notifications', label: 'Notifications', sub: 'Alerts inbox', href: '/notifications', icon: <Bell size={20} color="#B91C1C" />, iconBg: '#FEE2E2', show: true },
        { key: 'audit', label: 'Audit log', sub: 'Who did what', href: '/audit-log', icon: <ClipboardList size={20} color="#475569" />, iconBg: '#E2E8F0', show: mgmt },
        { key: 'roles', label: 'Role permissions', sub: 'CRUD matrix', href: '/role-permissions', icon: <Users size={20} color="#7C3AED" />, iconBg: '#EDE9FE', show: topAdmin },
        { key: 'sync', label: 'Sync', sub: 'Offline queue', href: '/sync', icon: <RefreshCw size={20} color="#0B3D91" />, iconBg: '#DBEAFE', show: true },
      ],
    },
  ];

  return (
    <>
      <Stack.Screen options={{ title: 'More' }} />
      <ScrollView style={s.root} contentContainerStyle={{ padding: 16 }}>
        <View style={s.userCard}>
          <View style={{ flex: 1 }}>
            <Text style={s.userName}>Hi, {(user?.full_name ?? 'there').split(' ')[0]}</Text>
            <Text style={s.userSub}>TransitOS{user?.branch_id ? ' · Branch scoped' : ' · All branches'}</Text>
          </View>
          <Badge label={role ? ROLE_LABELS[role] ?? role : '—'} tone="info" />
        </View>

        {sections.map((sec) => {
          const tiles = sec.tiles.filter((t) => t.show);
          if (!tiles.length) return null;
          return (
            <View key={sec.title}>
              <Text style={s.sectionTitle}>{sec.title}</Text>
              <View style={s.grid}>
                {tiles.map((t) => (
                  <Pressable
                    key={t.key}
                    style={s.tileWrap}
                    onPress={() => router.push(t.href as never)}
                    accessibilityRole="button"
                    accessibilityLabel={t.label}
                  >
                    <View style={s.tile}>
                      <View style={[s.tileIcon, { backgroundColor: t.iconBg }]}>{t.icon}</View>
                      <Text style={s.tileLabel}>{t.label}</Text>
                      <Text style={s.tileSub}>{t.sub}</Text>
                    </View>
                  </Pressable>
                ))}
              </View>
            </View>
          );
        })}
      </ScrollView>
    </>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F4F4F2' },
  userCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F8FAFC',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    padding: 16,
    marginBottom: 18,
  },
  userName: { fontSize: 18, fontWeight: '700', color: '#0F172A' },
  userSub: { fontSize: 13, color: '#64748B', marginTop: 4 },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: '#0F172A', marginBottom: 10 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', marginHorizontal: -6, marginBottom: 14 },
  tileWrap: { width: '50%', padding: 6 },
  tile: {
    backgroundColor: '#F8FAFC',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    padding: 14,
    minHeight: 128,
    justifyContent: 'flex-start',
  },
  tileIcon: {
    width: 44,
    height: 44,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
  },
  tileLabel: { fontSize: 16, fontWeight: '700', color: '#0F172A' },
  tileSub: { fontSize: 12, color: '#64748B', marginTop: 2 },
});
