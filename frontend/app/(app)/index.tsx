import React, { useMemo, useState } from 'react';
import {
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
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
import { UpdateChannelBanner } from '@/components/UpdateChannelBanner';
import {
  dashboardViewFor,
  roleSeesMoney,
  type GlanceId,
  type KpiId,
} from '@/lib/dashboard-view';
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

  // The view decides what this role needs. A request the backend will
  // refuse is a request worth not making: it is noise in the log, and a
  // card that reads zero because the request failed is worse than no
  // card at all.
  const view = dashboardViewFor(user?.role);

  const branches = useBranches({ page: 1, page_size: 50 }, view.needsBranches);
  const vehicles = useVehicles({ page: 1, page_size: 50 }, view.needsFleet);
  const trips = useTrips({ page: 1, page_size: 8 });
  const dashSummary = useDashboardSummary(view.needsSummary);

  const summaryParams = useMemo(() => {
    const to = new Date();
    const from = new Date(to.getTime() - 30 * 24 * 60 * 60 * 1000);
    return { from: from.toISOString(), to: to.toISOString() };
  }, []);
  // The reports summary is closed to drivers and conductors. Asking for
  // it anyway meant a 403 on every dashboard load and a revenue card
  // reading zero because the request had failed.
  const seesMoney = roleSeesMoney(user?.role);
  const summary = useOperationsSummary(summaryParams, seesMoney);

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
      .filter((b) => b.gps != null)
      .map((b) => ({
        id: b.id,
        lat: b.gps!.lat,
        lng: b.gps!.lng,
        label: b.name,
        color: 'warning' as const,
      }));
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

  const canCreateTrip = canAccess(user?.role, [
    'super_admin', 'owner', 'general_manager', 'branch_manager',
    'operations_manager',
  ]);
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

  // The trips the backend returned are already scoped: a driver or a
  // conductor gets only their own trips, a branch manager only their
  // branch's. So these figures are the reader's own, not the company's.
  const myTrips = trips.data?.items ?? [];
  const myTripsTotal = trips.data?.total ?? myTrips.length;
  const onDuty = myTrips.filter((t) =>
    ['boarding', 'departed'].includes(t.status),
  ).length;
  const passengersRecorded = myTrips.reduce(
    (sum, t) => sum + (t.passenger_count ?? 0),
    0,
  );

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
            {view.subtitle}
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
          {/* Which update channel this build is on — only shows on a
              build that is not production. */}
          <UpdateChannelBanner />

          {/* The role's own figures — the card set comes from
              lib/dashboard-view.ts, not from the platform view. */}
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', marginHorizontal: -6 }}>
            {view.kpis.map((id) => {
              const card = kpiFor(id, {
                  revenue,
                  variance,
                  tripsToday,
                  myTripsTotal,
                  onDuty,
                  passengersRecorded,
                  activeFleet: activeBuses.active,
                  totalVehicles: activeBuses.total,
                  pendingCashUps: ds?.pending_cash_ups ?? 0,
                  inMaintenance: ds?.vehicles_maintenance ?? 0,
                  docsExpiring: ds?.documents_expiring_30d ?? 0,
                  licensesExpiring: ds?.licenses_expiring_30d ?? 0,
                  openIncidents: ds?.open_incidents ?? 0,
                }, router);
              return <KpiCard key={id} {...card} />;
            })}
          </View>

          {/* The small counters — also the role's own. */}
          {view.glance.length > 0 ? (
            <>
              <Text style={{ fontSize: 16, fontWeight: '700', color: brand.slate, marginTop: 22, marginBottom: 10 }}>
                At a glance
              </Text>
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', marginHorizontal: -6 }}>
                {view.glance.map((id) => {
                  const counter = glanceFor(id, {
                      driversOnDuty: ds?.drivers_on_duty ?? 0,
                      inMaintenance: ds?.vehicles_maintenance ?? 0,
                      docsExpiring: ds?.documents_expiring_30d ?? 0,
                      licensesExpiring: ds?.licenses_expiring_30d ?? 0,
                      openIncidents: ds?.open_incidents ?? 0,
                      openTransfers: ds?.open_transfers ?? 0,
                      pendingCashUps: ds?.pending_cash_ups ?? 0,
                      totalVehicles: activeBuses.total,
                    }, router);
                  return <MiniKpi key={id} {...counter} />;
                })}
              </View>
            </>
          ) : null}

          {/* Live operations */}
          {view.liveOperations ? (
            <>
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
                  {view.fleetMap ? 'Live operations' : 'Your trips'}
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
                    {canCreateTrip
                      ? 'Create a trip to start operations'
                      : 'Trips assigned to you will appear here'}
                  </Text>
                </View>
              ) : (
                liveTrips.map((t) => (
                  <TripLiveCard key={t.id} trip={t} onPress={() => router.push(`/trips/${t.id}` as never)} />
                ))
              )}
            </>
          ) : null}

          {/* Fleet map */}
          {view.fleetMap ? (
            <>
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
            </>
          ) : null}

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

/** The figures the cards are built from. */
interface KpiFigures {
  revenue: number;
  variance: number;
  tripsToday: number;
  myTripsTotal: number;
  onDuty: number;
  passengersRecorded: number;
  activeFleet: number;
  totalVehicles: number;
  pendingCashUps: number;
  inMaintenance: number;
  docsExpiring: number;
  licensesExpiring: number;
  openIncidents: number;
}

/** The big card for one figure. */
function kpiFor(
  id: KpiId,
  f: KpiFigures,
  router: { push: (route: any) => void },
): {
  icon: React.ReactNode;
  iconBg: string;
  label: string;
  value: string;
  sub: string;
  valueColor?: string;
  onPress?: () => void;
} {
  switch (id) {
    case 'revenue':
      return {
        icon: <TrendingUp size={18} color={brand.success} />,
        iconBg: brand.successBg,
        label: 'Revenue',
        value: formatNGN(f.revenue),
        sub: 'Last 30 days',
      };
    case 'trips_today':
      return {
        icon: <Bus size={18} color={brand.navy} />,
        iconBg: brand.yellowSoft,
        label: 'Trips today',
        value: String(f.tripsToday),
        sub: 'Scheduled',
      };
    case 'active_fleet':
      return {
        icon: <Bus size={18} color={brand.info} />,
        iconBg: brand.infoBg,
        label: 'Active fleet',
        value: `${f.activeFleet}/${f.totalVehicles || '—'}`,
        sub: 'Available / on trip',
      };
    case 'cash_variance':
      return {
        icon: <Wallet size={18} color={f.variance >= 0 ? brand.success : brand.danger} />,
        iconBg: f.variance >= 0 ? brand.successBg : brand.dangerBg,
        label: 'Cash variance',
        value: formatNGN(f.variance),
        sub: f.variance >= 0 ? 'Within tolerance' : 'Needs review',
        valueColor: f.variance >= 0 ? brand.success : brand.danger,
        onPress: () => router.push('/cash-ups'),
      };
    case 'your_trips':
      return {
        icon: <Bus size={18} color={brand.navy} />,
        iconBg: brand.yellowSoft,
        label: 'Your trips',
        value: String(f.myTripsTotal),
        sub: 'Assigned to you',
      };
    case 'on_duty':
      return {
        icon: <UserCog size={18} color={f.onDuty > 0 ? brand.success : brand.muted} />,
        iconBg: f.onDuty > 0 ? brand.successBg : brand.infoBg,
        label: 'On duty',
        value: f.onDuty > 0 ? 'Yes' : 'No',
        sub: 'Boarding or on the road',
        valueColor: f.onDuty > 0 ? brand.success : brand.muted,
      };
    case 'passengers_recorded':
      return {
        icon: <Users size={18} color={brand.navy} />,
        iconBg: brand.infoBg,
        label: 'Passengers recorded',
        value: String(f.passengersRecorded),
        sub: 'On your trips',
      };
    case 'open_incidents':
      return {
        icon: <AlertTriangle size={18} color="#B91C1C" />,
        iconBg: brand.dangerBg,
        label: 'Open incidents',
        value: String(f.openIncidents),
        sub: 'Not yet resolved',
        valueColor: f.openIncidents > 0 ? '#B91C1C' : undefined,
      };
    case 'in_maintenance':
      return {
        icon: <Wrench size={18} color="#B45309" />,
        iconBg: brand.yellowSoft,
        label: 'In maintenance',
        value: String(f.inMaintenance),
        sub: 'Off the road',
        valueColor: f.inMaintenance > 0 ? '#B45309' : undefined,
      };
    case 'docs_expiring':
      return {
        icon: <ClipboardList size={18} color="#B91C1C" />,
        iconBg: brand.dangerBg,
        label: 'Docs expiring',
        value: String(f.docsExpiring),
        sub: 'Within 30 days',
        valueColor: f.docsExpiring > 0 ? '#B91C1C' : undefined,
      };
    case 'licenses_expiring':
      return {
        icon: <FileText size={18} color="#B45309" />,
        iconBg: brand.yellowSoft,
        label: 'Licenses expiring',
        value: String(f.licensesExpiring),
        sub: 'Within 30 days',
        valueColor: f.licensesExpiring > 0 ? '#B45309' : undefined,
      };
    case 'pending_cashups':
      return {
        icon: <Wallet size={18} color="#B45309" />,
        iconBg: brand.yellowSoft,
        label: 'Pending cash-ups',
        value: String(f.pendingCashUps),
        sub: 'Awaiting approval',
        valueColor: f.pendingCashUps > 0 ? '#B45309' : undefined,
      };
    default:
      return {
        icon: <Bus size={18} color={brand.navy} />,
        iconBg: brand.infoBg,
        label: 'Trips',
        value: String(f.tripsToday),
        sub: 'Today',
      };
  }
}

/** The small counter for one figure. */
function glanceFor(
  id: GlanceId,
  f: {
    driversOnDuty: number;
    inMaintenance: number;
    docsExpiring: number;
    licensesExpiring: number;
    openIncidents: number;
    openTransfers: number;
    pendingCashUps: number;
    totalVehicles: number;
  },
  router: { push: (route: any) => void },
): {
  icon: React.ReactNode;
  label: string;
  value: number;
  sub?: string;
  valueColor?: string;
  onPress?: () => void;
} {
  switch (id) {
    case 'drivers_on_duty':
      return {
        icon: <UserCog size={14} color={brand.navy} />,
        label: 'Drivers on duty',
        value: f.driversOnDuty,
        onPress: () => router.push('/drivers'),
      };
    case 'in_maintenance':
      return {
        icon: <Wrench size={14} color="#B45309" />,
        label: 'In maintenance',
        value: f.inMaintenance,
        valueColor: f.inMaintenance > 0 ? '#B45309' : undefined,
        onPress: () => router.push('/maintenance'),
      };
    case 'docs_expiring':
      return {
        icon: <ClipboardList size={14} color="#B91C1C" />,
        label: 'Docs expiring',
        value: f.docsExpiring,
        sub: '30 days',
        valueColor: f.docsExpiring > 0 ? '#B91C1C' : undefined,
        onPress: () => router.push('/vehicles'),
      };
    case 'licenses_expiring':
      return {
        icon: <FileText size={14} color="#B45309" />,
        label: 'Licenses expiring',
        value: f.licensesExpiring,
        sub: '30 days',
        valueColor: f.licensesExpiring > 0 ? '#B45309' : undefined,
        onPress: () => router.push('/drivers'),
      };
    case 'open_incidents':
      return {
        icon: <AlertTriangle size={14} color="#B91C1C" />,
        label: 'Open incidents',
        value: f.openIncidents,
        valueColor: f.openIncidents > 0 ? '#B91C1C' : undefined,
        onPress: () => router.push('/incidents'),
      };
    case 'open_transfers':
      return {
        icon: <ArrowRightLeft size={14} color={brand.navy} />,
        label: 'Open transfers',
        value: f.openTransfers,
        onPress: () => router.push('/transfers'),
      };
    case 'pending_cashups':
      return {
        icon: <Wallet size={14} color="#B45309" />,
        label: 'Pending cash-ups',
        value: f.pendingCashUps,
        valueColor: f.pendingCashUps > 0 ? '#B45309' : undefined,
        onPress: () => router.push('/cash-ups'),
      };
    case 'total_vehicles':
      return {
        icon: <Users size={14} color={brand.navy} />,
        label: 'Total vehicles',
        value: f.totalVehicles,
        onPress: () => router.push('/vehicles'),
      };
    default:
      return { icon: <Users size={14} color={brand.navy} />, label: 'Total', value: 0 };
  }
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
      <View style={{ flexDirection: 'row', alignItems: 'flex-start', marginBottom: 4 }}>
        <View style={{ paddingTop: 1 }}>{icon}</View>
        {/* Two lines: the counters sit four across on a phone, and a
            one-line label was truncated to "Driver…" and "Pendi…". */}
        <Text style={{ fontSize: 10, color: brand.muted, fontWeight: '500', marginLeft: 4, flex: 1 }} numberOfLines={2}>
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
