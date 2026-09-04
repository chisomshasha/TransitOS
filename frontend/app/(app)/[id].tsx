import React, { useRef, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Stack, useLocalSearchParams, useRouter } from 'expo-router';
import * as Print from 'expo-print';
import * as Sharing from 'expo-sharing';
import * as FileSystem from 'expo-file-system/legacy';
import {
  AlertTriangle,
  ClipboardList,
  FileText,
  Wallet,
} from 'lucide-react-native';
import {
  useConductors,
  useDrivers,
  useManifest,
  useRoutes,
  useTrip,
  useVehicles,
} from '@/lib/queries';
import { api } from '@/lib/api';
import { Avatar } from '@/components/ui/kit';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { CashUpSection } from '@/components/CashUpSection';
import { useToast } from '@/components/ui/Toast';
import { formatNGN } from '@/lib/format';
import { TRIP_STATUS_LABELS } from '@/lib/types';
import { brand } from '@/lib/theme';

const STATUS_TONE: Record<string, 'neutral' | 'info' | 'primary' | 'success' | 'warning' | 'danger'> = {
  planned: 'neutral',
  boarding: 'info',
  departed: 'primary',
  arrived: 'info',
  closed: 'warning',
  cashed_up: 'success',
  cancelled: 'danger',
};

function fmtDuration(ms: number): string {
  const mins = Math.max(0, Math.round(ms / 60000));
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return `${h}h ${m}m`;
}

export default function TripDetailScreen() {
  const router = useRouter();
  const toast = useToast();
  const { id } = useLocalSearchParams<{ id: string }>();

  const scrollRef = useRef<ScrollView>(null);
  const [cashUpY, setCashUpY] = useState(0);
  const [showAllManifest, setShowAllManifest] = useState(false);

  const tripQ = useTrip(id ?? '');
  const routesQ = useRoutes({ page: 1, page_size: 200 });
  const vehiclesQ = useVehicles({ page: 1, page_size: 200 });
  const driversQ = useDrivers({ page: 1, page_size: 200 });
  const conductorsQ = useConductors({ page: 1, page_size: 200 });
  const manifestQ = useManifest(id ?? '');

  const t = tripQ.data;
  const manifest = manifestQ.data?.items ?? [];
  const visibleManifest = showAllManifest ? manifest : manifest.slice(0, 3);

  const onExportWaybill = async () => {
    if (!t) return;
    try {
      const resp = await api.get(`/trips/${t.id}/waybill.pdf`, { responseType: 'arraybuffer' });
      const bytes = new Uint8Array(resp.data as ArrayBuffer);
      let binary = '';
      for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
      const base64 = btoa(binary);
      const fileUri = `${FileSystem.cacheDirectory}waybill-${t.id.slice(0, 8)}.pdf`;
      await FileSystem.writeAsStringAsync(fileUri, base64, {
        encoding: FileSystem.EncodingType.Base64,
      });
      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(fileUri, { mimeType: 'application/pdf' });
      } else {
        await Print.printAsync({ uri: fileUri });
      }
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not export waybill');
    }
  };

  if (tripQ.isLoading) {
    return (
      <>
        <Stack.Screen options={{ title: 'Trip' }} />
        <View style={s.loading}>
          <Spinner label="Loading trip…" />
        </View>
      </>
    );
  }
  if (!t) {
    return (
      <>
        <Stack.Screen options={{ title: 'Trip' }} />
        <View style={s.loading}>
          <Text style={s.errorText}>Trip not found</Text>
        </View>
      </>
    );
  }

  const routeObj = routesQ.data?.items.find((r) => r.id === t.route_id);
  const driver = driversQ.data?.items.find((d) => d.id === t.driver_id);
  const conductor = conductorsQ.data?.items.find((c) => c.id === t.conductor_id);
  const dep = new Date(t.scheduled_departure);
  const arr = new Date(t.scheduled_arrival);
  const onDuty = ['boarding', 'departed'].includes(t.status);

  return (
    <>
      <Stack.Screen options={{ title: `Trip ${t.id.slice(0, 8).toUpperCase()}` }} />
      <ScrollView
        ref={scrollRef}
        style={s.root}
        contentContainerStyle={{ padding: 16, paddingBottom: 60 }}
      >
        {/* ── Hero ─ */}
        <View style={s.hero}>
          <View style={s.heroTop}>
            <View style={{ flex: 1 }}>
              <Text style={s.heroRoute}>
                {routeObj?.origin_city ?? '—'} → {routeObj?.destination_city ?? '—'}
              </Text>
              <Text style={s.heroDep}>
                Departed {dep.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </Text>
              <Text style={s.heroArr}>
                Arrived {arr.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} ·{' '}
                {fmtDuration(arr.getTime() - dep.getTime())}
              </Text>
            </View>
            <Badge
              label={TRIP_STATUS_LABELS[t.status] ?? t.status}
              tone={STATUS_TONE[t.status] ?? 'neutral'}
            />
          </View>
          <View style={s.heroStats}>
            <HeroStat label="Pax" value={String(t.passenger_count)} />
            <HeroStat label="Cargo" value={`${t.cargo_weight_kg} kg`} />
            <HeroStat label="Revenue" value={formatNGN(t.total_revenue)} />
          </View>
        </View>

        {/* ── Crew ─ */}
        <Text style={s.sectionTitle}>Crew</Text>
        <View style={s.crewCard}>
          <CrewRow
            name={driver?.full_name ?? '—'}
            sub={`Driver · ${driver?.license_no ?? ''}`}
            onDuty={onDuty}
          />
          <View style={s.crewDivider} />
          <CrewRow
            name={conductor?.full_name ?? '—'}
            sub={`Conductor · Badge ${conductor?.badge_no ?? ''}`}
            onDuty={onDuty}
          />
        </View>

        {/* ── Actions ─ */}
        <Text style={s.sectionTitle}>Actions</Text>
        <View style={s.actionGrid}>
          <Pressable
            style={[s.actionBase, { backgroundColor: brand.navy }]}
            onPress={onExportWaybill}
          >
            <FileText size={20} color="#FFFFFF" />
            <Text style={[s.actionText, { color: '#FFFFFF' }]}>Export waybill</Text>
          </Pressable>
          <Pressable
            style={[s.actionBase, s.actionBorder]}
            onPress={() => router.push(`/pre-trip-checklist?tripId=${t.id}` as never)}
          >
            <ClipboardList size={20} color={brand.navy} />
            <Text style={[s.actionText, { color: brand.navy }]}>Pre-trip checklist</Text>
          </Pressable>
          <Pressable
            style={[s.actionBase, s.actionBorder]}
            onPress={() => router.push(`/report-incident?tripId=${t.id}` as never)}
          >
            <AlertTriangle size={20} color={brand.navy} />
            <Text style={[s.actionText, { color: brand.navy }]}>Report incident</Text>
          </Pressable>
          <Pressable
            style={[s.actionBase, s.actionBorder]}
            onPress={() => scrollRef.current?.scrollTo({ y: cashUpY - 80, animated: true })}
          >
            <Wallet size={20} color={brand.navy} />
            <Text style={[s.actionText, { color: brand.navy }]}>View cash-up</Text>
          </Pressable>
        </View>

        {/* ── Manifest ─ */}
        <Text style={s.sectionTitle}>Manifest ({manifest.length} entries)</Text>
        <View style={s.manifestCard}>
          {manifest.length === 0 ? (
            <Text style={s.emptyText}>No manifest entries yet.</Text>
          ) : (
            <>
              {visibleManifest.map((m) => (
                <View key={m.id} style={s.manifestRow}>
                  <View style={{ flex: 1 }}>
                    <Text style={s.manifestName}>
                      {m.type === 'cargo'
                        ? `Parcel — ${m.cargo_description ?? ''}`
                        : m.passenger_name ?? '—'}
                    </Text>
                    <Text style={s.manifestSub}>
                      {m.type === 'cargo'
                        ? `${m.cargo_weight_kg ?? 0} kg`
                        : `Seat ${m.seat_number ?? '—'}`}{' '}
                      · {formatNGN(m.fare)}
                    </Text>
                  </View>
                  {m.type === 'cargo' ? (
                    <Badge label="CARGO" tone="info" size="sm" />
                  ) : (
                    <Badge
                      label={m.payment_status.toUpperCase()}
                      tone={
                        m.payment_status === 'paid'
                          ? 'success'
                          : m.payment_status === 'on_board'
                          ? 'info'
                          : 'danger'
                      }
                      size="sm"
                    />
                  )}
                </View>
              ))}
              {manifest.length > 3 ? (
                <Pressable
                  style={s.manifestMore}
                  onPress={() => setShowAllManifest((v) => !v)}
                >
                  <Text style={s.manifestMoreText}>
                    {showAllManifest
                      ? 'Show less'
                      : `… ${manifest.length - 3} more — View all`}
                  </Text>
                </Pressable>
              ) : null}
            </>
          )}
        </View>

        {/* ── Cash-up ─ */}
        <View
          onLayout={(e) => setCashUpY(e.nativeEvent.layout.y)}
          style={{ marginTop: 16 }}
        >
          <CashUpSection trip={t} />
        </View>
      </ScrollView>
    </>
  );
}

function HeroStat({ label, value }: { label: string; value: string }) {
  return (
    <View style={{ flex: 1 }}>
      <Text style={s.heroStatLabel}>{label}</Text>
      <Text style={s.heroStatValue} numberOfLines={1}>
        {value}
      </Text>
    </View>
  );
}

function CrewRow({
  name,
  sub,
  onDuty,
}: {
  name: string;
  sub: string;
  onDuty: boolean;
}) {
  return (
    <View style={s.crewRow}>
      <Avatar name={name} size={44} />
      <View style={{ flex: 1, marginLeft: 12 }}>
        <Text style={s.crewName}>{name}</Text>
        <Text style={s.crewSub}>{sub}</Text>
      </View>
      <Badge
        label={onDuty ? 'On duty' : 'Off duty'}
        tone={onDuty ? 'success' : 'neutral'}
        size="sm"
      />
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F4F4F2' },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  errorText: { fontSize: 16, color: '#B91C1C' },
  hero: { backgroundColor: brand.navy, borderRadius: 16, padding: 16, marginBottom: 16 },
  heroTop: { flexDirection: 'row', alignItems: 'flex-start' },
  heroRoute: { color: '#BFDBFE', fontSize: 13, fontWeight: '600' },
  heroDep: { color: '#FFFFFF', fontSize: 22, fontWeight: '800', marginTop: 4 },
  heroArr: { color: '#BFDBFE', fontSize: 13, marginTop: 4 },
  heroStats: {
    flexDirection: 'row',
    marginTop: 16,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.2)',
  },
  heroStatLabel: { color: '#BFDBFE', fontSize: 11, fontWeight: '600' },
  heroStatValue: { color: '#FFFFFF', fontSize: 17, fontWeight: '800', marginTop: 2 },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#0F172A',
    marginBottom: 10,
    marginTop: 4,
  },
  crewCard: {
    backgroundColor: '#F8FAFC',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    padding: 14,
    marginBottom: 16,
  },
  crewRow: { flexDirection: 'row', alignItems: 'center' },
  crewDivider: { height: 1, backgroundColor: '#E2E8F0', marginVertical: 12 },
  crewName: { fontSize: 15, fontWeight: '700', color: '#0F172A' },
  crewSub: { fontSize: 12, color: '#64748B', marginTop: 2 },
  actionGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  actionBase: {
    width: '48%',
    borderRadius: 12,
    padding: 14,
    alignItems: 'center',
    marginBottom: 10,
  },
  actionBorder: {
    borderWidth: 1,
    borderColor: brand.navy,
    backgroundColor: '#FFFFFF',
  },
  actionText: {
    fontWeight: '700',
    fontSize: 13,
    marginTop: 6,
    textAlign: 'center',
  },
  manifestCard: {
    backgroundColor: '#F8FAFC',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    padding: 14,
  },
  emptyText: { color: '#64748B', fontSize: 13 },
  manifestRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
  },
  manifestName: { fontSize: 14, fontWeight: '700', color: '#0F172A' },
  manifestSub: { fontSize: 12, color: '#64748B', marginTop: 2 },
  manifestMore: { paddingVertical: 10 },
  manifestMoreText: { color: brand.navy, fontWeight: '600', fontSize: 13 },
});
