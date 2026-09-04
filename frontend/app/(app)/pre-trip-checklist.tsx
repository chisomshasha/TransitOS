import React, { useEffect, useMemo, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { Stack, useLocalSearchParams, useRouter } from 'expo-router';
import { AlertTriangle, Check, PenLine } from 'lucide-react-native';
import { useTrips } from '@/lib/queries';
import {
  useCreateInspection,
  useInspections,
  useSubmitInspection,
  useUpdateInspection,
  type InspectionItem,
} from '@/lib/queries-p4';
import { Spinner } from '@/components/ui/Spinner';
import { useToast } from '@/components/ui/Toast';
import { BarCard, Chip, type SevTone } from '@/components/ui/kit';
import { brand } from '@/lib/theme';

export default function PreTripChecklistScreen() {
  const router = useRouter();
  const toast = useToast();
  const { tripId } = useLocalSearchParams<{ tripId: string }>();

  const tripsQ = useTrips({ page: 1, page_size: 200 });
  const inspectionsQ = useInspections(tripId);
  const createMut = useCreateInspection();
  const updateMut = useUpdateInspection();
  const submitMut = useSubmitInspection();

  const trip = (tripsQ.data?.items ?? []).find((t) => t.id === tripId);

  const [items, setItems] = useState<InspectionItem[]>([]);
  const [odometer, setOdometer] = useState('');
  const [signature, setSignature] = useState(false);
  const [inspectionId, setInspectionId] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  // Load or create the draft
  useEffect(() => {
    if (!trip || loaded) return;
    const existing = (inspectionsQ.data?.items ?? [])[0];
    if (existing) {
      setItems(existing.items ?? []);
      setOdometer(existing.odometer_reading ? String(existing.odometer_reading) : '');
      setSignature(!!existing.signature_confirmed);
      setInspectionId(existing.id);
    } else {
      // Build from template by creating a draft
      createMut.mutate(
        {
          trip_id: trip.id,
          vehicle_id: trip.vehicle_id,
          driver_id: trip.driver_id,
          items: [],
          signature_confirmed: false,
        },
        {
          onSuccess: (d) => {
            setItems(d.items ?? []);
            setInspectionId(d.id);
          },
        },
      );
    }
    setLoaded(true);
  }, [trip, inspectionsQ.data, loaded]);

  const setStatus = (key: string, status: string) => {
    setItems((prev) => prev.map((it) => (it.key === key ? { ...it, status } : it)));
  };

  const setNote = (key: string, note: string) => {
    setItems((prev) => prev.map((it) => (it.key === key ? { ...it, note } : it)));
  };

  const doneCount = items.filter((i) => i.status !== 'pending').length;
  const progress = items.length ? Math.round((doneCount / items.length) * 100) : 0;
  const hasFail = items.some((i) => i.status === 'fail');

  const buildPayload = () => ({
    trip_id: tripId,
    vehicle_id: trip?.vehicle_id,
    driver_id: trip?.driver_id,
    items,
    odometer_reading: odometer ? parseInt(odometer, 10) : null,
    fuel_level_pct: null,
    signature_confirmed: signature,
  });

  const onSaveDraft = async () => {
    if (!inspectionId) return;
    try {
      await updateMut.mutateAsync({ id: inspectionId, data: buildPayload() });
      toast.success('Draft saved');
    } catch {
      toast.error('Could not save draft');
    }
  };

  const onSubmit = async () => {
    if (!inspectionId) return;
    try {
      await updateMut.mutateAsync({ id: inspectionId, data: buildPayload() });
      await submitMut.mutateAsync(inspectionId);
      toast.success('Submitted — trip departed');
      router.back();
    } catch {
      toast.error('Could not submit checklist');
    }
  };

  if (tripsQ.isLoading || inspectionsQ.isLoading || !loaded) {
    return (
      <>
        <Stack.Screen options={{ title: 'Pre-trip checklist' }} />
        <View style={s.loading}><Spinner label="Loading checklist…" /></View>
      </>
    );
  }

  return (
    <>
      <Stack.Screen options={{ title: `Pre-trip · ${trip?.id?.slice(0, 8) ?? ''}` }} />
      <ScrollView style={s.root} contentContainerStyle={{ padding: 16, paddingBottom: 100 }}>
        <View style={s.headCard}>
          <View>
            <Text style={s.headTitle}>Pre-trip checklist</Text>
            <Text style={s.headSub}>{doneCount} of {items.length} complete</Text>
          </View>
          <Text style={[s.headPct, { color: progress === 100 ? '#047857' : brand.navy }]}>
            {progress}%
          </Text>
        </View>
        <View style={s.progressWrap}>
          <View style={[s.progressBar, { width: `${progress}%` }]} />
        </View>

        {items.map((item) => {
          const tone: SevTone =
            item.status === 'ok' ? 'ok' : item.status === 'low' ? 'warn' : item.status === 'fail' ? 'danger' : 'neutral';
          return (
            <BarCard key={item.key} tone={tone}>
              <View style={s.itemHeader}>
                <Text style={s.itemLabel}>{item.label}</Text>
                <View style={s.statusChips}>
                  <Chip label="OK" tone="ok" active={item.status === 'ok'} onPress={() => setStatus(item.key, 'ok')} />
                  <Chip label="Low" tone="warn" active={item.status === 'low'} onPress={() => setStatus(item.key, 'low')} />
                  <Chip label="Fail" tone="danger" active={item.status === 'fail'} onPress={() => setStatus(item.key, 'fail')} />
                </View>
              </View>
              {item.key === 'odometer_reading' ? (
                <TextInput
                  style={s.input}
                  value={odometer}
                  onChangeText={setOdometer}
                  placeholder="Odometer (km)"
                  placeholderTextColor="#94A3B8"
                  keyboardType="numeric"
                />
              ) : null}
              {item.key === 'driver_signature' ? (
                <Pressable style={s.sigRow} onPress={() => setSignature((v) => !v)}>
                  <PenLine size={16} color={signature ? '#047857' : '#94A3B8'} />
                  <Text style={[s.sigText, { color: signature ? '#047857' : '#64748B' }]}>
                    {signature ? 'Driver signature captured' : 'Capture driver signature'}
                  </Text>
                  {signature ? <Check size={16} color="#047857" /> : null}
                </Pressable>
              ) : null}
              {item.status === 'fail' ? (
                <TextInput
                  style={[s.input, { marginTop: 8 }]}
                  value={item.note ?? ''}
                  onChangeText={(v) => setNote(item.key, v)}
                  placeholder="Describe the issue…"
                  placeholderTextColor="#94A3B8"
                />
              ) : null}
            </BarCard>
          );
        })}

        {hasFail ? (
          <View style={s.failWarn}>
            <AlertTriangle size={16} color="#B91C1C" />
            <Text style={s.failWarnText}>A FAIL item was noted. The trip can still depart, but schedule maintenance.</Text>
          </View>
        ) : null}

        <View style={s.actions}>
          <Pressable style={s.draftBtn} onPress={onSaveDraft}>
            <Text style={s.draftBtnText}>Save draft</Text>
          </Pressable>
          <Pressable style={s.submitBtn} onPress={onSubmit}>
            <Text style={s.submitBtnText}>Submit & depart</Text>
          </Pressable>
        </View>
      </ScrollView>
    </>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F4F4F2' },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  headCard: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  headTitle: { fontSize: 18, fontWeight: '700', color: '#0F172A' },
  headSub: { fontSize: 13, color: '#64748B', marginTop: 2 },
  headPct: { fontSize: 26, fontWeight: '800' },
  progressWrap: { height: 8, backgroundColor: '#E2E8F0', borderRadius: 4, marginVertical: 14 },
  progressBar: { height: 8, borderRadius: 4, backgroundColor: '#10B981' },
  itemHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap' },
  itemLabel: { fontSize: 15, fontWeight: '700', color: '#0F172A', flex: 1, marginRight: 8 },
  statusChips: { flexDirection: 'row' },
  input: { height: 46, paddingHorizontal: 12, borderRadius: 10, borderWidth: 1, borderColor: '#E2E8F0', backgroundColor: '#FFFFFF', fontSize: 15, color: '#0F172A', marginTop: 10 },
  sigRow: { flexDirection: 'row', alignItems: 'center', marginTop: 10 },
  sigText: { fontSize: 14, fontWeight: '600', marginLeft: 8, flex: 1 },
  failWarn: { flexDirection: 'row', backgroundColor: '#FEF2F2', borderWidth: 1, borderColor: '#FECACA', borderRadius: 10, padding: 12, marginBottom: 12 },
  failWarnText: { fontSize: 13, color: '#B91C1C', marginLeft: 8, flex: 1 },
  actions: { flexDirection: 'row', marginTop: 8, gap: 10 },
  draftBtn: { flex: 1, borderWidth: 1, borderColor: brand.navy, borderRadius: 12, paddingVertical: 14, alignItems: 'center' },
  draftBtnText: { color: brand.navy, fontWeight: '700' },
  submitBtn: { flex: 1, backgroundColor: brand.navy, borderRadius: 12, paddingVertical: 14, alignItems: 'center' },
  submitBtnText: { color: '#FFFFFF', fontWeight: '700' },
});
