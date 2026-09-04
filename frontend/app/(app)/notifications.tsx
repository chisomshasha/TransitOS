import React, { useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { Stack } from 'expo-router';
import { BellOff } from 'lucide-react-native';
import { Chip, type SevTone } from '@/components/ui/kit';

const FILTERS: { id: string; label: string; tone: SevTone }[] = [
  { id: 'all', label: 'All', tone: 'neutral' },
  { id: 'unread', label: 'Unread', tone: 'info' },
  { id: 'maintenance', label: 'Maintenance', tone: 'info' },
  { id: 'documents', label: 'Documents', tone: 'danger' },
  { id: 'licenses', label: 'Licenses', tone: 'warn' },
  { id: 'trips', label: 'Trips', tone: 'neutral' },
];

export default function NotificationsScreen() {
  const [filter, setFilter] = useState('all');

  return (
    <>
      <Stack.Screen
        options={{
          title: 'Notifications',
          headerRight: () => (
            <Text style={s.markAll} onPress={() => {/* wired in Phase 1 */}}>
              Mark all read
            </Text>
          ),
        }}
      />
      <ScrollView style={s.root} contentContainerStyle={{ padding: 16 }}>
        <View style={s.chipRow}>
          {FILTERS.map((f) => (
            <Chip key={f.id} label={f.label} tone={f.tone} active={filter === f.id} onPress={() => setFilter(f.id)} />
          ))}
        </View>

        <View style={s.emptyCard}>
          <BellOff size={28} color="#94A3B8" />
          <Text style={s.emptyTitle}>No notifications yet</Text>
          <Text style={s.emptyBody}>
            Alerts about expiring documents, licenses, maintenance and low fuel will appear here
            once the alerts engine is live (Phase 1).
          </Text>
        </View>
      </ScrollView>
    </>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F4F4F2' },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: 12 },
  markAll: { color: '#BFDBFE', fontSize: 13, fontWeight: '700', marginRight: 8 },
  emptyCard: {
    backgroundColor: '#F8FAFC', borderRadius: 16, borderWidth: 1, borderColor: '#E2E8F0',
    padding: 28, alignItems: 'center',
  },
  emptyTitle: { fontSize: 16, fontWeight: '700', color: '#0F172A', marginTop: 12 },
  emptyBody: { fontSize: 13, color: '#64748B', textAlign: 'center', marginTop: 6, lineHeight: 19 },
});
