import React from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { useRoute } from 'expo-router';
import { useRoutes } from '@/lib/queries';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { ArrowRight, MapPin, Route as RouteIcon } from 'lucide-react-native';
import { formatNGN } from '@/lib/format';

export default function RouteDetailScreen() {
  const route = useRoute();
  const id = (route.params as { id: string })?.id;
  const { data, isLoading } = useRoutes({ page: 1, page_size: 100 });
  const r = (data?.items ?? []).find((x) => x.id === id);

  if (isLoading) return <View style={s.loading}><Spinner label="Loading route…" /></View>;
  if (!r) return <View style={s.loading}><Text style={s.errorText}>Route not found</Text></View>;

  return (
    <ScrollView style={s.root} contentContainerStyle={{ padding: 16 }}>
      <Card>
        <View style={s.header}>
          <View style={s.iconBox}><RouteIcon size={24} color="#047857" /></View>
          <View style={{ flex: 1 }}>
            <Text style={s.name}>{r.name}</Text>
            <Badge
              label={r.type === 'interstate' ? 'interstate' : 'intrastate'}
              tone={r.type === 'interstate' ? 'info' : 'neutral'}
            />
          </View>
          <Badge
            label={r.is_active ? 'active' : 'inactive'}
            tone={r.is_active ? 'success' : 'neutral'}
          />
        </View>
        <View style={s.divider} />
        <View style={s.cities}>
          <View style={s.cityBox}>
            <MapPin size={16} color="#0E7490" />
            <Text style={s.cityLabel}>From</Text>
            <Text style={s.cityName}>{r.origin_city}</Text>
          </View>
          <ArrowRight size={20} color="#94A3B8" />
          <View style={s.cityBox}>
            <MapPin size={16} color="#047857" />
            <Text style={s.cityLabel}>To</Text>
            <Text style={s.cityName}>{r.destination_city}</Text>
          </View>
        </View>
        <View style={s.divider} />
        <InfoRow label="Distance" value={`${r.distance_km} km`} />
        <InfoRow label="Duration" value={`${r.estimated_duration_hours} h`} />
        <InfoRow label="Passenger fare" value={formatNGN(r.base_fare_passenger ?? 0)} />
        <InfoRow label="Cargo fare /kg" value={formatNGN(r.base_fare_cargo_per_kg ?? 0)} />
        {r.intermediate_stops?.length ? (
          <>
            <View style={s.divider} />
            <Text style={s.sectionTitle}>Intermediate stops ({r.intermediate_stops.length})</Text>
            {r.intermediate_stops.map((stop, i) => (
              <View key={i} style={s.stopRow}>
                <View style={s.stopDot} />
                <Text style={s.stopText}>{stop.name ?? `Stop ${i + 1}`}</Text>
              </View>
            ))}
          </>
        ) : null}
      </Card>
    </ScrollView>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={s.infoRow}>
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
  iconBox: { width: 48, height: 48, borderRadius: 8, backgroundColor: '#ECFDF5', alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  name: { fontSize: 18, fontWeight: '700', color: '#171717', marginBottom: 4 },
  divider: { height: 1, backgroundColor: '#E5E7EB', marginVertical: 16 },
  cities: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  cityBox: { flex: 1, alignItems: 'center' },
  cityLabel: { fontSize: 11, color: '#64748B', textTransform: 'uppercase', marginTop: 4 },
  cityName: { fontSize: 15, fontWeight: '600', color: '#171717', marginTop: 2, textAlign: 'center' },
  infoRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6 },
  infoLabel: { fontSize: 13, color: '#64748B' },
  infoValue: { fontSize: 13, fontWeight: '600', color: '#171717' },
  sectionTitle: { fontSize: 14, fontWeight: '600', color: '#171717', marginBottom: 8 },
  stopRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 4 },
  stopDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: '#0E7490', marginRight: 10 },
  stopText: { fontSize: 13, color: '#404040' },
});
