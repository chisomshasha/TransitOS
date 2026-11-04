import React, { useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  ShieldAlert,
} from 'lucide-react-native';
import { ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { Stack, useLocalSearchParams } from 'expo-router';
import {
  useAcknowledgeIncident,
  useIncident,
  useResolveIncident,
} from '@/lib/queries-p4';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Spinner } from '@/components/ui/Spinner';
import { Button } from '@/components/ui/Button';
import { Field } from '@/components/ui/Field';
import { Modal } from '@/components/ui/Modal';
import { useToast } from '@/components/ui/Toast';
import { useAuth } from '@/lib/auth-context';
import { canAccess } from '@/lib/rbac';
import type { Role } from '@/lib/types';

const SEVERITY_TONE: Record<string, 'danger' | 'warning' | 'info'> = {
  severe: 'danger',
  moderate: 'warning',
  minor: 'info',
};

const STATUS_TONE: Record<string, 'danger' | 'warning' | 'info' | 'success' | 'neutral'> = {
  open: 'danger',
  acknowledged: 'warning',
  resolved: 'success',
  closed: 'neutral',
};

const CATEGORY_LABELS: Record<string, string> = {
  mechanical: 'Mechanical issue',
  accident: 'Accident',
  theft: 'Theft',
  passenger_dispute: 'Passenger dispute',
  cargo_damage: 'Cargo damage',
  weather: 'Weather',
  other: 'Other',
};

/** Roles allowed to acknowledge / resolve an incident. */
const OPS_ROLES: Role[] = [
  'super_admin', 'owner', 'general_manager', 'operations_manager',
  'fleet_manager', 'branch_manager',
];

export default function IncidentDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const toast = useToast();
  const { user } = useAuth();

  const incidentQ = useIncident(id ?? '');
  const acknowledge = useAcknowledgeIncident();
  const resolve = useResolveIncident();

  const [resolveOpen, setResolveOpen] = useState(false);
  const [note, setNote] = useState('');

  const incident = incidentQ.data;
  const canAct = canAccess(user?.role, OPS_ROLES);

  const onAcknowledge = async () => {
    try {
      await acknowledge.mutateAsync(id);
      toast.success('Incident acknowledged');
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not acknowledge the incident');
    }
  };

  const onResolve = async () => {
    try {
      await resolve.mutateAsync({ id, note: note.trim() || undefined });
      toast.success('Incident resolved');
      setResolveOpen(false);
      setNote('');
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not resolve the incident');
    }
  };

  if (incidentQ.isLoading) {
    return (
      <>
        <Stack.Screen options={{ title: 'Incident' }} />
        <View style={s.loading}><Spinner label="Loading incident…" /></View>
      </>
    );
  }

  if (!incident) {
    return (
      <>
        <Stack.Screen options={{ title: 'Incident' }} />
        <View style={s.loading}><Text style={s.errorText}>Incident not found</Text></View>
      </>
    );
  }

  return (
    <>
      <Stack.Screen options={{ title: 'Incident' }} />
      <ScrollView style={s.root} contentContainerStyle={{ padding: 16, paddingBottom: 60 }}>
        <Card>
          <View style={s.hero}>
            <View style={s.iconBox}>
              <AlertTriangle size={20} color="#B91C1C" />
            </View>
            <View style={{ flex: 1 }}>
              <Text style={s.heroTitle}>
                {CATEGORY_LABELS[incident.category] ?? incident.category.replace(/_/g, ' ')}
              </Text>
              <Text style={s.heroSub}>
                Reported {new Date(incident.created_at).toLocaleString()}
              </Text>
            </View>
          </View>
          <View style={s.badges}>
            <Badge label={incident.severity.toUpperCase()} tone={SEVERITY_TONE[incident.severity] ?? 'info'} />
            <Badge label={incident.status.toUpperCase()} tone={STATUS_TONE[incident.status] ?? 'neutral'} />
          </View>
        </Card>

        <View style={{ height: 12 }} />
        <Card>
          <Text style={s.sectionTitle}>What happened</Text>
          <Text style={s.description}>{incident.description || 'No description recorded.'}</Text>
        </Card>

        <View style={{ height: 12 }} />
        <Card>
          <Text style={s.sectionTitle}>Details</Text>
          {incident.trip_id ? <Row label="Trip" value={incident.trip_id} /> : null}
          {incident.vehicle_id ? <Row label="Vehicle" value={incident.vehicle_id} /> : null}
          {incident.branch_id ? <Row label="Branch" value={incident.branch_id} /> : null}
          {incident.notified?.length ? (
            <Row label="Notified" value={`${incident.notified.length} staff`} />
          ) : null}
          {incident.acknowledged_at ? (
            <Row label="Acknowledged" value={new Date(incident.acknowledged_at).toLocaleString()} />
          ) : null}
          {incident.resolved_at ? (
            <Row label="Resolved" value={new Date(incident.resolved_at).toLocaleString()} />
          ) : null}
          {incident.resolution_note ? <Row label="Resolution" value={incident.resolution_note} /> : null}
        </Card>

        {canAct ? (
          <>
            <View style={{ height: 16 }} />
            {incident.status === 'open' ? (
              <Button
                label="Acknowledge"
                icon={<ShieldAlert size={16} color="#FFFFFF" />}
                onPress={onAcknowledge}
                loading={acknowledge.isPending}
                fullWidth
              />
            ) : null}
            {incident.status === 'open' || incident.status === 'acknowledged' ? (
              <View style={{ height: 8 }} />
            ) : null}
            {incident.status === 'open' || incident.status === 'acknowledged' ? (
              <Button
                label="Resolve incident"
                icon={<CheckCircle2 size={16} color="#FFFFFF" />}
                variant="secondary"
                onPress={() => setResolveOpen(true)}
                fullWidth
              />
            ) : null}
          </>
        ) : null}
      </ScrollView>

      <Modal visible={resolveOpen} onClose={() => setResolveOpen(false)} title="Resolve incident" variant="sheet">
        <Field label="Resolution note" helperText="What was done about it?">
          <TextInput
            style={s.input}
            value={note}
            onChangeText={setNote}
            placeholder="optional"
            placeholderTextColor="#94A3B8"
            multiline
          />
        </Field>
        <View style={{ height: 12 }} />
        <Button label="Mark resolved" onPress={onResolve} loading={resolve.isPending} fullWidth />
        <View style={{ height: 8 }} />
        <Button label="Cancel" onPress={() => setResolveOpen(false)} variant="ghost" fullWidth />
      </Modal>
    </>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={s.row}>
      <Text style={s.rowLabel}>{label}</Text>
      <Text style={s.rowValue} numberOfLines={2}>{value}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F4F4F2' },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  errorText: { fontSize: 16, color: '#B91C1C' },
  hero: { flexDirection: 'row', alignItems: 'center' },
  iconBox: { width: 44, height: 44, borderRadius: 12, backgroundColor: '#FEE2E2', alignItems: 'center', justifyContent: 'center', marginRight: 12 },
  heroTitle: { fontSize: 17, fontWeight: '800', color: '#0F172A' },
  heroSub: { fontSize: 12, color: '#64748B', marginTop: 2 },
  badges: { flexDirection: 'row', gap: 8, marginTop: 14 },
  sectionTitle: { fontSize: 12, fontWeight: '700', color: '#64748B', letterSpacing: 0.6, textTransform: 'uppercase', marginBottom: 8 },
  description: { fontSize: 14, color: '#0F172A', lineHeight: 21 },
  row: { flexDirection: 'row', alignItems: 'flex-start', paddingVertical: 7 },
  rowLabel: { fontSize: 13, color: '#64748B', width: 104 },
  rowValue: { fontSize: 13, fontWeight: '500', color: '#0F172A', flex: 1 },
  input: { minHeight: 88, paddingHorizontal: 12, paddingVertical: 11, borderRadius: 12, borderWidth: 1, borderColor: '#E2E8F0', backgroundColor: '#FFFFFF', fontSize: 15, color: '#0F172A', textAlignVertical: 'top' },
});
