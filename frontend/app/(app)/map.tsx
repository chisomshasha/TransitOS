import React, { useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Stack, useRouter } from 'expo-router';
import { WebView } from 'react-native-webview';
import { Bus, Gauge, MapPin, Search, Truck } from 'lucide-react-native';
import { useFleetPositions } from '@/lib/queries-p5';
import { useBranches } from '@/lib/queries';
import { SearchBar } from '@/components/ui/SearchBar';
import { Spinner } from '@/components/ui/Spinner';
import { Badge } from '@/components/ui/Badge';
import { brand } from '@/lib/theme';

const STATUS_COLORS: Record<string, string> = {
  available: '#047857',
  on_trip: '#1D4ED8',
  maintenance: '#B45309',
  grounded: '#B91C1C',
  offline: '#475569',
};

const STATUS_LABELS: Record<string, string> = {
  available: 'Available',
  on_trip: 'On trip',
  maintenance: 'Maintenance',
  grounded: 'Grounded',
  offline: 'Offline',
};

export default function LiveMapScreen() {
  const router = useRouter();
  const { data, isLoading } = useFleetPositions();
  const branchesQ = useBranches({ page: 1, page_size: 200 });
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<string | null>(null);

  const positions = data?.items ?? [];
  const filtered = useMemo(
    () =>
      positions.filter(
        (p) =>
          !search.trim() ||
          (p.reg_number ?? '').toLowerCase().includes(search.trim().toLowerCase()) ||
          (p.driver_name ?? '').toLowerCase().includes(search.trim().toLowerCase()),
      ),
    [positions, search],
  );

  const branchName = (id?: string | null) =>
    branchesQ.data?.items.find((b) => b.id === id)?.name ?? '—';

  const points = filtered.map((p) => ({
    id: p.vehicle_id,
    lat: p.lat,
    lng: p.lng,
    label: p.reg_number ?? 'Vehicle',
    color:
      p.status === 'available'
        ? 'success'
        : p.status === 'on_trip'
        ? 'info'
        : p.status === 'maintenance'
        ? 'warning'
        : 'neutral',
    description:
      `${p.speed_kph.toFixed(0)} km/h` +
      (p.driver_name ? ` · ${p.driver_name}` : '') +
      (p.branch_id ? ` · ${branchName(p.branch_id)}` : ''),
  }));

  const html = useMemo(() => buildLiveMapHtml(points), [points]);

  const selectedPos = selected ? positions.find((p) => p.vehicle_id === selected) : null;

  const counts = useMemo(() => {
    const c: Record<string, number> = { available: 0, on_trip: 0, maintenance: 0, grounded: 0 };
    positions.forEach((p) => {
      if (p.status in c) c[p.status] += 1;
    });
    return c;
  }, [positions]);

  return (
    <>
      <Stack.Screen options={{ title: 'Live fleet map', headerShown: false }} />
      <View style={s.root}>
        {/* Overlay header */}
        <View style={s.overlayTop}>
          <View style={s.headerRow}>
            <Text style={s.headerTitle}>Live fleet</Text>
            <Text style={s.headerCount}>{positions.length} vehicles</Text>
          </View>
          <View style={s.searchWrap}>
            <SearchBar
              value={search}
              onChange={setSearch}
              placeholder="Search registration or driver"
            />
          </View>
          <View style={s.legendRow}>
            <LegendDot color={STATUS_COLORS.available} label={`Available (${counts.available})`} />
            <LegendDot color={STATUS_COLORS.on_trip} label={`On trip (${counts.on_trip})`} />
            <LegendDot color={STATUS_COLORS.maintenance} label={`Maintenance (${counts.maintenance})`} />
            <LegendDot color={STATUS_COLORS.grounded} label={`Grounded (${counts.grounded})`} />
          </View>
        </View>

        {/* Map */}
        {isLoading ? (
          <View style={s.loadingWrap}>
            <Spinner label="Loading fleet positions…" />
          </View>
        ) : positions.length === 0 ? (
          <View style={s.emptyWrap}>
            <Truck size={36} color={brand.navy} />
            <Text style={s.emptyTitle}>No active vehicles</Text>
            <Text style={s.emptyBody}>Vehicles with GPS-anchored branches will appear here.</Text>
          </View>
        ) : (
          <WebView
            originWhitelist={['*']}
            source={{ html }}
            style={s.webview}
            onMessage={(e) => {
              try {
                const data = JSON.parse(e.nativeEvent.data);
                if (data.type === 'select') setSelected(data.id);
              } catch {
                /* ignore */
              }
            }}
            startInLoadingState
            renderLoading={() => (
              <View style={s.webviewLoading}>
                <ActivityIndicator size="large" color={brand.navy} />
              </View>
            )}
          />
        )}

        {/* Selected vehicle bottom sheet */}
        {selectedPos ? (
          <View style={s.sheet}>
            <View style={s.sheetRow}>
              <View style={s.sheetIcon}>
                <Bus size={22} color={brand.navy} />
              </View>
              <View style={{ flex: 1 }}>
                <View style={s.sheetHeader}>
                  <Text style={s.sheetReg}>{selectedPos.reg_number ?? 'Vehicle'}</Text>
                  <Badge
                    label={STATUS_LABELS[selectedPos.status] ?? selectedPos.status}
                    tone={
                      selectedPos.status === 'available'
                        ? 'success'
                        : selectedPos.status === 'on_trip'
                        ? 'info'
                        : selectedPos.status === 'maintenance'
                        ? 'warning'
                        : 'neutral'
                    }
                    size="sm"
                  />
                </View>
                <Text style={s.sheetSub}>
                  {branchName(selectedPos.branch_id)}
                  {selectedPos.driver_name ? ` · ${selectedPos.driver_name}` : ''}
                </Text>
                <View style={s.speedRow}>
                  <Gauge size={12} color={brand.muted} />
                  <Text style={s.speedText}>{selectedPos.speed_kph.toFixed(0)} km/h</Text>
                  <Text style={s.coordText}>
                    {selectedPos.lat.toFixed(4)}, {selectedPos.lng.toFixed(4)}
                  </Text>
                </View>
              </View>
              <Pressable style={s.viewBtn} onPress={() => router.push(`/vehicles/${selectedPos.vehicle_id}` as never)}>
                <Text style={s.viewBtnText}>View</Text>
              </Pressable>
            </View>
          </View>
        ) : null}
      </View>
    </>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <View style={s.legendItem}>
      <View style={[s.legendDot, { backgroundColor: color }]} />
      <Text style={s.legendLabel}>{label}</Text>
    </View>
  );
}

function buildLiveMapHtml(points: Array<{ id: string; lat: number; lng: number; label: string; color: string; description?: string }>): string {
  const colorMap: Record<string, string> = {
    primary: '#0E7490',
    success: '#047857',
    danger: '#B91C1C',
    warning: '#B45309',
    info: '#1D4ED8',
    neutral: '#475569',
  };
  const enriched = points.map((p) => ({ ...p, color: colorMap[p.color] || colorMap.primary }));
  const pointsJson = JSON.stringify(enriched);

  return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html, body { margin: 0; padding: 0; height: 100%; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
  #map { width: 100%; height: 100%; background: #E5E7EB; }
  .leaflet-popup-content { font-size: 13px; line-height: 1.4; }
  .leaflet-popup-content strong { font-size: 14px; color: #0F172A; }
</style>
</head>
<body>
<div id="map"></div>
<script>
  var points = ${pointsJson};
  var map = L.map('map', { zoomControl: true });
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap'
  }).addTo(map);
  points.forEach(function (p) {
    var m = L.circleMarker([p.lat, p.lng], {
      radius: 10,
      color: p.color,
      weight: 2,
      fillColor: p.color,
      fillOpacity: 0.9
    }).addTo(map);
    var desc = p.description ? '<br/><span style="color:#64748B;font-size:12px;">' + p.description + '</span>' : '';
    m.bindPopup('<strong>' + (p.label || 'Vehicle') + '</strong>' + desc);
    m.on('click', function () {
      window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'select', id: p.id }));
    });
  });
  if (points.length > 0) {
    var bounds = L.latLngBounds(points.map(function (p) { return [p.lat, p.lng]; }));
    map.fitBounds(bounds, { padding: [60, 60], maxZoom: 10 });
  } else {
    map.setView([9.082, 8.6753], 6);
  }
</script>
</body>
</html>`;
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F4F4F2' },
  loadingWrap: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  emptyWrap: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32 },
  emptyTitle: { fontSize: 17, fontWeight: '700', color: brand.slate, marginTop: 10 },
  emptyBody: { fontSize: 13, color: brand.muted, textAlign: 'center', marginTop: 6, lineHeight: 19 },
  overlayTop: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    paddingTop: 50,
    paddingHorizontal: 16,
    paddingBottom: 12,
    backgroundColor: 'rgba(255,255,255,0.95)',
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
    zIndex: 10,
  },
  headerRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 },
  headerTitle: { fontSize: 18, fontWeight: '800', color: brand.navy },
  headerCount: { fontSize: 13, fontWeight: '700', color: brand.muted },
  searchWrap: { marginBottom: 10 },
  legendRow: { flexDirection: 'row', flexWrap: 'wrap' },
  legendItem: { flexDirection: 'row', alignItems: 'center', marginRight: 14, marginBottom: 4 },
  legendDot: { width: 10, height: 10, borderRadius: 5, marginRight: 6 },
  legendLabel: { fontSize: 11, fontWeight: '600', color: '#475569' },
  webview: { flex: 1, backgroundColor: '#E5E7EB' },
  webviewLoading: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#E5E7EB' },
  sheet: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 18,
    borderTopRightRadius: 18,
    padding: 16,
    paddingBottom: 32,
    borderTopWidth: 1,
    borderTopColor: '#E2E8F0',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -4 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 10,
  },
  sheetRow: { flexDirection: 'row', alignItems: 'center' },
  sheetIcon: {
    width: 48,
    height: 48,
    borderRadius: 12,
    backgroundColor: '#DBEAFE',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  sheetHeader: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  sheetReg: { fontSize: 17, fontWeight: '800', color: '#0F172A' },
  sheetSub: { fontSize: 13, color: '#64748B', marginTop: 4 },
  speedRow: { flexDirection: 'row', alignItems: 'center', marginTop: 6 },
  speedText: { fontSize: 13, fontWeight: '700', color: brand.navy, marginLeft: 4 },
  coordText: { fontSize: 11, color: '#94A3B8', marginLeft: 10 },
  viewBtn: {
    backgroundColor: brand.navy,
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  viewBtnText: { color: '#FFFFFF', fontWeight: '700', fontSize: 13 },
});
