import React, { useMemo, useState } from 'react';
import {
  Pressable,
  RefreshControl,
  ScrollView,
  Text,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';
import {
  AlertTriangle,
  ArrowRightLeft,
  Bus,
  ClipboardList,
  FileText,
  MapPin,
  Plus,
  QrCode,
  TrendingUp,
  UserCog,
  Users,
  Wallet,
  Wrench,
  ChevronRight,
} from 'lucide-react-native';
import { useAuth } from '@/lib/auth-context';
import {
  useBranches,
  useOperationsSummary,
  useTrips,
  useVehicles,
} from '@/lib/queries';
import { useDashboardSummary } from '@/lib/queries-p8';
import { formatNGN } from '@/lib/format';
import { brand, tripStatusColor } from '@/lib/theme';
import { MapModal, type MapPoint } from '@/components/ui/MapModal';
import { CreateBranchModal } from '@/components/admin/CreateBranchModal';
import { CreateUserModal } from '@/components/admin/CreateUserModal';
import { CreateVehicleModal } from '@/components/admin/CreateVehicleModal';
import { CreateDriverModal } from '@/components/admin/CreateDriverModal';
import { CreateConductorModal } from '@/components/admin/CreateConductorModal';
import { CreateRouteModal } from '@/components/admin/CreateRouteModal';
import { ErrorBoundary } from '@/components/ui/ErrorBoundary';
import { canAccess } from '@/lib/rbac';
import { ROLE_LABELS, TRIP_STATUS_LABELS, type Trip } from '@/lib/types';

export default function DashboardScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const [mapOpen, setMapOpen] = useState(false);
  const [branchOpen, setBranchOpen] = useState(false);
  const [userOpen, setUserOpen] = useState(false);
  const [vehicleOpen, setVehicleOpen] = useState(false);
  const [driverOpen, setDriverOpen] = useState(false);
  const [conductorOpen, setConductorOpen] = useState(false);
  const [routeOpen, setRouteOpen] = useState(false);

  const branches = useBranches({ page: 1, page_size: 50 });
  const vehicles = useVehicles({ page: 1, page_size: 50 });
  const trips = useTrips({ page: 1, page_size: 8 });
  const dashSummary = useDashboardSummary();

  const summaryParams = useMemo(() => {
    const to = new Date();
    const from = new Date(to.getTime() - 30 * 24 * 60 * 60 * 1000);
    return { from: from.toISOString(), to: to.toISOString() };
  }, []);
  const summary = useOperationsSummary(summaryParams);

  const liveTrips = useMemo(() => {
    const items = trips.data?.items ?? [];
    const live = items.filter((t) =>
      ['boarding', 'departed', 'planned'].includes(t.status),
    );
    return (live.length ? live : items).slice(0, 3);
  }, [trips.data]);

  const activeBuses = useMemo(() => {
    const all = vehicles.data?.items ?? [];
    const active = all.filter(
      (v) => v.status === 'available' || v.status === 'on_trip',
    ).length;
    return { active, total: all.length || vehicles.data?.total || 0 };
  }, [vehicles.data]);

  const mapPoints: MapPoint[] = useMemo(() => {
    return (branches.data?.items ?? [])
      .filter((b) => typeof (b as { lat?: number }).lat === 'number')
      .map((b) => {
        const bb = b as { id: string; name: string; lat?: number; lng?: number };
        return {
          id: bb.id,
          lat: bb.lat!,
          lng: bb.lng ?? 0,
          label: bb.name,
          color: 'warning' as const,
        };
      });
  }, [branches.data]);

  const refreshing =
    trips.isFetching ||
    branches.isFetching ||
    vehicles.isFetching ||
    summary.isFetching ||
    dashSummary.isFetching;

  const onRefresh = () => {
    trips.refetch();
    branches.refetch();
    vehicles.refetch();
    summary.refetch();
    dashSummary.refetch();
  };

  const greeting = useMemo(() => {
    const h = new Date().getHours();
    if (h < 12) return 'Good morning';
    if (h < 18) return 'Good afternoon';
    return 'Good evening';
  }, []);

  const canCreateBranch = canAccess(user?.role, [
    'super_admin', 'owner', 'general_manager', 'branch_manager',
  ]);
  const canCreateUser = canAccess(user?.role, [
    'super_admin', 'owner', 'general_manager', 'branch_manager',
  ]);
  const canCreateVehicle = canAccess(user?.role, [
    'super_admin', 'owner', 'general_manager', 'branch_manager',
    'fleet_manager', 'operations_manager',
  ]);
  const canCreateCrew = canAccess(user?.role, [
    'super_admin', 'owner', 'general_manager', 'branch_manager',
    'fleet_manager', 'operations_manager',
  ]);
  const canCreateRoute = canAccess(user?.role, [
    'super_admin', 'owner', 'general_manager', 'branch_manager',
    'fleet_manager', 'operations_manager',
  ]);
  const canScan = canAccess(user?.role, [
    'super_admin', 'owner', 'general_manager', 'branch_manager',
    'operations_manager', 'fleet_manager', 'driver', 'conductor',
  ]);

  const revenue = summary.data?.totals?.revenue ?? 0;
  const variance = summary.data?.totals?.variance ?? 0;

  const tripsToday = (trips.data?.items ?? []).filter((t) => {
    const d = new Date(t.scheduled_departure);
    const now = new Date();
    return (
      d.getFullYear() === now.getFullYear() &&
      d.getMonth() === now.getMonth() &&
      d.getDate() === now.getDate()
    );
  }).length;

  // Phase 8 expanded counters
  const ds = dashSummary.data;

  return (
    <ErrorBoundary scope="dashboard">
      <View style={{ flex: 1, backgroundColor: brand.bg }}>
        {/* Navy header */}
        <View
          style={{
            backgroundColor: brand.navy,
            paddingHorizontal: 20,
            paddingTop: 12,
            paddingBottom: 20,
          }}
        >
          <Text style={{ fontSize: 13, color: 'rgba(255,255,255,0.7)' }}>
            {greeting},
          </Text>
          <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 2 }}>
            <Text
              style={{
                fontSize: 22,
                fontWeight: '700',
                color: '#FFFFFF',
                flex: 1,
              }}
              numberOfLines={1}
            >
              {user?.full_name ?? 'there'}
            </Text>
            <View
              style={{
                width: 8,
                height: 8,
                borderRadius: 4,
                backgroundColor: brand.yellow,
                marginLeft: 8,
              }}
            />
          </View>
          <Text style={{ fontSize: 13, color: 'rgba(255,255,255,0.65)', marginTop: 4 }}>
            Here's what's happening with your fleet.
          </Text>
          {user ? (
            <View
              style={{
                alignSelf: 'flex-start',
                marginTop: 10,
                backgroundColor: 'rgba(255,204,0,0.2)',
                paddingHorizontal: 10,
                paddingVertical: 4,
                borderRadius: 20,
              }}
            >
              <Text style={{ fontSize: 11, fontWeight: '600', color: brand.yellow }}>
                {ROLE_LABELS[user.role] ?? user.role}
              </Text>
            </View>
          ) : null}
        </View>

        <ScrollView
          style={{ flex: 1 }}
          contentContainerStyle={{ padding: 16, paddingBottom: 100 }}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={brand.navy} />
          }
          showsVerticalScrollIndicator={false}
        >
          {/* Primary KPIs — 2x2 */}
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', marginHorizontal: -6 }}>
            <KpiCard
              icon={<TrendingUp size={18} color={brand.success} />}
              iconBg={brand.successBg}
              label="Revenue"
              value={formatNGN(revenue)}
              sub="Last 30 days"
            />
            <KpiCard
              icon={<Bus size={18} color={brand.navy} />}
              iconBg={brand.yellowSoft}
              label="Trips today"
              value={String(tripsToday)}
              sub="Scheduled"
            />
            <KpiCard
              icon={<Bus size={18} color={brand.info} />}
              iconBg={brand.infoBg}
              label="Active fleet"
              value={`${activeBuses.active}/${activeBuses.total || '—'}`}
              sub="Available / on trip"
            />
            <KpiCard
              icon={<Wallet size={18} color={variance >= 0 ? brand.success : brand.danger} />}
              iconBg={variance >= 0 ? brand.successBg : brand.dangerBg}
              label="Cash variance"
              value={formatNGN(variance)}
              sub={variance >= 0 ? 'Within tolerance' : 'Needs review'}
              valueColor={variance >= 0 ? brand.success : brand.danger}
              onPress={() => router.push('/cash-ups' as never)}
            />
          </View>

          {/* Phase 8 expanded KPIs — At a Glance */}
          <Text style={{ fontSize: 16, fontWeight: '700', color: brand.slate, marginTop: 22, marginBottom: 10 }}>
            At a glance
          </Text>
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', marginHorizontal: -6 }}>
            <MiniKpi
              icon={<UserCog size={14} color={brand.navy} />}
              label="Drivers on duty"
              value={ds?.drivers_on_duty ?? 0}
              onPress={() => router.push('/drivers' as never)}
            />
            <MiniKpi
              icon={<Wrench size={14} color="#B45309" />}
              label="In maintenance"
              value={ds?.vehicles_maintenance ?? 0}
              valueColor={ds && ds.vehicles_maintenance > 0 ? '#B45309' : undefined}
              onPress={() => router.push('/maintenance' as never)}
            />
            <MiniKpi
              icon={<ClipboardList size={14} color="#B91C1C" />}
              label="Docs expiring"
              value={ds?.documents_expiring_30d ?? 0}
              sub="30 days"
              valueColor={ds && ds.documents_expiring_30d > 0 ? '#B91C1C' : undefined}
              onPress={() => router.push('/vehicles' as never)}
            />
            <MiniKpi
              icon={<FileText size={14} color="#B45309" />}
              label="Licenses expiring"
              value={ds?.licenses_expiring_30d ?? 0}
              sub="30 days"
              valueColor={ds && ds.licenses_expiring_30d > 0 ? '#B45309' : undefined}
              onPress={() => router.push('/drivers' as never)}
            />
            <MiniKpi
              icon={<AlertTriangle size={14} color="#B91C1C" />}
              label="Open incidents"
              value={ds?.open_incidents ?? 0}
              valueColor={ds && ds.open_incidents > 0 ? '#B91C1C' : undefined}
              onPress={() => router.push('/incidents' as never)}
            />
            <MiniKpi
              icon={<ArrowRightLeft size={14} color={brand.navy} />}
              label="Open transfers"
              value={ds?.open_transfers ?? 0}
              onPress={() => router.push('/transfers' as never)}
            />
            <MiniKpi
              icon={<Wallet size={14} color="#B45309" />}
              label="Pending cash-ups"
              value={ds?.pending_cash_ups ?? 0}
              valueColor={ds && ds.pending_cash_ups > 0 ? '#B45309' : undefined}
              onPress={() => router.push('/cash-ups' as never)}
            />
            <MiniKpi
              icon={<Users size={14} color={brand.navy} />}
              label="Total vehicles"
              value={activeBuses.total}
              onPress={() => router.push('/vehicles' as never)}
            />
          </View>

          {/* Live operations */}
          <View
            style={{
              flexDirection: 'row',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginTop: 22,
              marginBottom: 10,
            }}
          >
            <Text style={{ fontSize: 16, fontWeight: '700', color: brand.slate }}>
              Live operations
            </Text>
            <Pressable onPress={() => router.push('/trips' as never)} hitSlop={8}>
              <Text style={{ fontSize: 13, fontWeight: '600', color: brand.navy }}>
                See all →
              </Text>
            </Pressable>
          </View>

          {liveTrips.length === 0 ? (
            <View
              style={{
                backgroundColor: '#fff',
                borderRadius: 14,
                padding: 20,
                alignItems: 'center',
                borderWidth: 1,
                borderColor: brand.border,
              }}
            >
              <Bus size={36} color={brand.yellow} />
              <Text style={{ marginTop: 10, fontWeight: '700', color: brand.slate }}>
                No trips yet
              </Text>
              <Text style={{ marginTop: 4, fontSize: 13, color: brand.muted, textAlign: 'center' }}>
                Create a trip to start operations
              </Text>
            </View>
          ) : (
            liveTrips.map((t) => (
              <TripLiveCard key={t.id} trip={t} onPress={() => router.push(`/trips/${t.id}` as never)} />
            ))
          )}

          {/* Fleet map */}
          <View
            style={{
              flexDirection: 'row',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginTop: 22,
              marginBottom: 10,
            }}
          >
            <Text style={{ fontSize: 16, fontWeight: '700', color: brand.slate }}>
              Fleet map
            </Text>
            <Pressable onPress={() => setMapOpen(true)} hitSlop={8}>
              <Text style={{ fontSize: 13, fontWeight: '600', color: brand.navy }}>
                Open full map →
              </Text>
            </Pressable>
          </View>

          <Pressable
            onPress={() => setMapOpen(true)}
            style={{
              backgroundColor: '#fff',
              borderRadius: 14,
              overflow: 'hidden',
              borderWidth: 1,
              borderColor: brand.border,
              minHeight: 120,
              justifyContent: 'center',
              alignItems: 'center',
              padding: 20,
            }}
          >
            <MapPin size={28} color={brand.navy} />
            <Text style={{ marginTop: 8, fontWeight: '600', color: brand.slate }}>
              {mapPoints.length
                ? `${mapPoints.length} branch location${mapPoints.length > 1 ? 's' : ''}`
                : 'Tap to open map'}
            </Text>
            <Text style={{ marginTop: 4, fontSize: 12, color: brand.muted }}>
              Branches & active routes
            </Text>
            <View
              style={{
                marginTop: 12,
                backgroundColor: brand.navy,
                paddingHorizontal: 16,
                paddingVertical: 8,
                borderRadius: 20,
              }}
            >
              <Text style={{ color: '#fff', fontWeight: '600', fontSize: 13 }}>
                Open full map
              </Text>
            </View>
          </Pressable>

          {/* Quick actions */}
          {(canCreateBranch || canCreateUser || canCreateVehicle || canCreateCrew || canCreateRoute) && (
            <View style={{ marginTop: 22 }}>
              <Text style={{ fontSize: 16, fontWeight: '700', color: brand.slate, marginBottom: 10 }}>
                Quick actions
              </Text>
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', marginHorizontal: -4 }}>
                {canCreateBranch && (
                  <QuickAction label="Branch" onPress={() => setBranchOpen(true)} />
                )}
                {canCreateUser && (
                  <QuickAction label="Invite user" onPress={() => setUserOpen(true)} />
                )}
                {canCreateVehicle && (
                  <QuickAction label="Vehicle" onPress={() => setVehicleOpen(true)} />
                )}
                {canCreateCrew && (
                  <QuickAction label="Driver" onPress={() => setDriverOpen(true)} />
                )}
                {canCreateCrew && (
                  <QuickAction label="Conductor" onPress={() => setConductorOpen(true)} />
                )}
                {canCreateRoute && (
                  <QuickAction label="Route" onPress={() => setRouteOpen(true)} />
                )}
              </View>
            </View>
          )}
        </ScrollView>

        {/* Scan FAB */}
        {canScan ? (
          <Pressable
            onPress={() => router.push('/scan' as never)}
            style={s.scanFab}
            accessibilityLabel="Scan QR code"
          >
            <QrCode size={24} color={brand.navy} strokeWidth={2.5} />
          </Pressable>
        ) : null}

        <MapModal
          visible={mapOpen}
          onClose={() => setMapOpen(false)}
          title="Fleet map"
          points={mapPoints}
          zoom={6}
        />
        <CreateBranchModal visible={branchOpen} onClose={() => setBranchOpen(false)} />
        <CreateUserModal visible={userOpen} onClose={() => setUserOpen(false)} />
        <CreateVehicleModal visible={vehicleOpen} onClose={() => setVehicleOpen(false)} />
        <CreateDriverModal visible={driverOpen} onClose={() => setDriverOpen(false)} />
        <CreateConductorModal visible={conductorOpen} onClose={() => setConductorOpen(false)} />
        <CreateRouteModal visible={routeOpen} onClose={() => setRouteOpen(false)} />
      </View>
    </ErrorBoundary>
  );
}

function KpiCard({
  icon, iconBg, label, value, sub, valueColor, onPress,
}: {
  icon: React.ReactNode; iconBg: string; label: string; value: string;
  sub: string; valueColor?: string; onPress?: () => void;
}) {
  const inner = (
    <View
      style={{
        backgroundColor: '#fff',
        borderRadius: 14,
        padding: 14,
        borderWidth: 1,
        borderColor: brand.border,
        minHeight: 100,
      }}
    >
      <View
        style={{
          width: 32, height: 32, borderRadius: 10, backgroundColor: iconBg,
          alignItems: 'center', justifyContent: 'center', marginBottom: 8,
        }}
      >
        {icon}
      </View>
      <Text style={{ fontSize: 11, color: brand.muted, fontWeight: '500' }}>{label}</Text>
      <Text
        style={{
          fontSize: 18, fontWeight: '700', color: valueColor ?? brand.slate, marginTop: 2,
        }}
        numberOfLines={1}
      >
        {value}
      </Text>
      <Text style={{ fontSize: 10, color: brand.muted, marginTop: 2 }}>{sub}</Text>
    </View>
  );
  return (
    <View style={{ width: '50%', padding: 6 }}>
      {onPress ? <Pressable onPress={onPress}>{inner}</Pressable> : inner}
    </View>
  );
}

function MiniKpi({
  icon, label, value, sub, valueColor, onPress,
}: {
  icon: React.ReactNode; label: string; value: number;
  sub?: string; valueColor?: string; onPress?: () => void;
}) {
  const inner = (
    <View
      style={{
        backgroundColor: '#fff',
        borderRadius: 12,
        padding: 12,
        borderWidth: 1,
        borderColor: brand.border,
        minHeight: 72,
      }}
    >
      <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 4 }}>
        {icon}
        <Text style={{ fontSize: 10, color: brand.muted, fontWeight: '500', marginLeft: 4, flex: 1 }} numberOfLines={1}>
          {label}
        </Text>
      </View>
      <Text
        style={{
          fontSize: 20, fontWeight: '800', color: valueColor ?? brand.slate,
        }}
        numberOfLines={1}
      >
        {value}
      </Text>
      {sub ? <Text style={{ fontSize: 9, color: brand.muted, marginTop: 1 }}>{sub}</Text> : null}
    </View>
  );
  return (
    <View style={{ width: '25%', padding: 4 }}>
      {onPress ? <Pressable onPress={onPress}>{inner}</Pressable> : inner}
    </View>
  );
}

function TripLiveCard({ trip, onPress }: { trip: Trip; onPress: () => void }) {
  const colors = tripStatusColor[trip.status] ?? tripStatusColor.planned;
  const dep = new Date(trip.scheduled_departure);
  const time = dep.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  return (
    <Pressable
      onPress={onPress}
      style={{
        backgroundColor: '#fff', borderRadius: 14, marginBottom: 10,
        borderWidth: 1, borderColor: brand.border, overflow: 'hidden', flexDirection: 'row',
      }}
    >
      <View style={{ width: 4, backgroundColor: colors.text }} />
      <View style={{ flex: 1, padding: 12 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center' }}>
          <View
            style={{
              backgroundColor: colors.bg, paddingHorizontal: 8, paddingVertical: 3,
              borderRadius: 8, marginRight: 8,
            }}
          >
            <Text style={{ fontSize: 11, fontWeight: '700', color: colors.text }}>
              {TRIP_STATUS_LABELS[trip.status] ?? trip.status}
            </Text>
          </View>
          <Text
            style={{ flex: 1, fontSize: 14, fontWeight: '700', color: brand.slate }}
            numberOfLines={1}
          >
            Trip · {time}
          </Text>
          <ChevronRight size={16} color={brand.muted} />
        </View>
        <Text style={{ fontSize: 12, color: brand.muted, marginTop: 6 }}>
          {dep.toLocaleDateString()} · Status {trip.status}
        </Text>
        {(trip.passenger_count != null || trip.total_revenue != null) && (
          <Text style={{ fontSize: 12, color: brand.navy, marginTop: 4, fontWeight: '600' }}>
            {trip.passenger_count != null ? `${trip.passenger_count} pax` : ''}
            {trip.passenger_count != null && trip.total_revenue != null ? ' · ' : ''}
            {trip.total_revenue != null ? formatNGN(trip.total_revenue) : ''}
          </Text>
        )}
      </View>
    </Pressable>
  );
}

function QuickAction({ label, onPress }: { label: string; onPress: () => void }) {
  return (
    <View style={{ width: '33.33%', padding: 4 }}>
      <Pressable
        onPress={onPress}
        style={{
          backgroundColor: '#fff', borderRadius: 12, borderWidth: 1,
          borderColor: brand.border, paddingVertical: 12, alignItems: 'center',
        }}
      >
        <Plus size={16} color={brand.navy} />
        <Text
          style={{ fontSize: 11, fontWeight: '600', color: brand.slate, marginTop: 4 }}
          numberOfLines={1}
        >
          {label}
        </Text>
      </Pressable>
    </View>
  );
}

const s = StyleSheet.create({
  scanFab: {
    position: 'absolute',
    right: 20,
    bottom: 90,
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: brand.yellow,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 8,
  },
});
