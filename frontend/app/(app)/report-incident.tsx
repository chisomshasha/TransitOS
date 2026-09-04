import React, { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { Stack, useRouter } from 'expo-router';
import { Camera, Image as ImageIcon, X } from 'lucide-react-native';
import * as ImagePicker from 'expo-image-picker';
import * as FileSystem from 'expo-file-system/legacy';
import { useCreateIncident } from '@/lib/queries-p4';
import { useTrips, useUsers } from '@/lib/queries';
import { Chip, Avatar, type SevTone } from '@/components/ui/kit';
import { Field } from '@/components/ui/Field';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';
import { useToast } from '@/components/ui/Toast';
import { useAuth } from '@/lib/auth-context';
import { brand } from '@/lib/theme';

const SEVERITIES: Array<{ id: string; label: string; tone: SevTone }> = [
  { id: 'minor', label: 'Minor', tone: 'info' },
  { id: 'moderate', label: 'Moderate', tone: 'warn' },
  { id: 'severe', label: 'Severe', tone: 'danger' },
];

const CATEGORIES = [
  { label: 'Mechanical issue', value: 'mechanical' },
  { label: 'Accident', value: 'accident' },
  { label: 'Theft', value: 'theft' },
  { label: 'Passenger dispute', value: 'passenger_dispute' },
  { label: 'Cargo damage', value: 'cargo_damage' },
  { label: 'Weather', value: 'weather' },
  { label: 'Other', value: 'other' },
];

export default function ReportIncidentScreen() {
  const router = useRouter();
  const toast = useToast();
  const { user } = useAuth();
  const createMut = useCreateIncident();
  const tripsQ = useTrips({ page: 1, page_size: 100 });
  const usersQ = useUsers({ page: 1, page_size: 200 });

  const [tripId, setTripId] = useState<string | null>(null);
  const [severity, setSeverity] = useState('minor');
  const [category, setCategory] = useState('mechanical');
  const [description, setDescription] = useState('');
  const [photos, setPhotos] = useState<string[]>([]);
  const [notify, setNotify] = useState<Record<string, boolean>>({});

  const tripOptions = (tripsQ.data?.items ?? []).map((t) => ({ label: t.id.slice(0, 12), value: t.id }));
  const staff = (usersQ.data?.items ?? []).filter((u) => u.id !== user?.id).slice(0, 10);

  const pickPhotos = async () => {
    const res = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsMultipleSelection: true,
      base64: false,
      quality: 0.6,
    });
    if (res.canceled) return;
    const uris = res.assets.map((a) => a.uri);
    // Convert to base64 so it can be stored server-side
    const b64s: string[] = [];
    for (const uri of uris) {
      try {
        const b64 = await FileSystem.readAsStringAsync(uri, { encoding: FileSystem.EncodingType.Base64 });
        b64s.push(`data:image/jpeg;base64,${b64}`);
      } catch {
        // skip unreadable asset
      }
    }
    setPhotos((prev) => [...prev, ...b64s].slice(0, 5));
  };

  const onSubmit = async () => {
    if (!description.trim()) return toast.error('Describe what happened');
    try {
      await createMut.mutateAsync({
        trip_id: tripId,
        severity,
        category,
        description: description.trim(),
        photos,
        notified: Object.keys(notify).filter((k) => notify[k]),
      });
      toast.success('Incident reported');
      router.back();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not report incident');
    }
  };

  return (
    <>
      <Stack.Screen options={{ title: 'Report incident' }} />
      <ScrollView style={s.root} contentContainerStyle={{ padding: 16, paddingBottom: 100 }}>
        <Field label="Trip (optional)">
          <Select value={tripId} onChange={setTripId} options={tripOptions} placeholder="Select trip" />
        </Field>

        <Text style={s.label}>Severity</Text>
        <View style={s.chipRow}>
          {SEVERITIES.map((sv) => (
            <Chip key={sv.id} label={sv.label} tone={sv.tone} active={severity === sv.id} onPress={() => setSeverity(sv.id)} />
          ))}
        </View>

        <Field label="Category">
          <Select value={category} onChange={setCategory} options={CATEGORIES} placeholder="Select category" />
        </Field>

        <Text style={s.label}>What happened?</Text>
        <TextInput
          style={s.textarea}
          value={description}
          onChangeText={setDescription}
          placeholder="Describe the incident…"
          placeholderTextColor="#94A3B8"
          multiline
          numberOfLines={6}
          textAlignVertical="top"
        />

        <Text style={s.label}>Photos</Text>
        <View style={s.photoRow}>
          {photos.map((p, i) => (
            <View key={i} style={s.photoBox}>
              <ImageIcon size={20} color={brand.navy} />
              <Pressable style={s.photoRemove} onPress={() => setPhotos((prev) => prev.filter((_, x) => x !== i))}>
                <X size={14} color="#B91C1C" />
              </Pressable>
            </View>
          ))}
          <Pressable style={s.photoAdd} onPress={pickPhotos}>
            <Camera size={20} color="#94A3B8" />
            <Text style={s.photoAddText}>+ Add</Text>
          </Pressable>
        </View>

        <Text style={s.label}>Notify</Text>
        <View style={s.notifyCard}>
          {staff.map((u) => (
            <View key={u.id} style={s.notifyRow}>
              <Avatar name={u.full_name} size={36} />
              <Text style={s.notifyName}>{u.full_name}</Text>
              <Pressable
                style={[s.notifyBtn, notify[u.id] && { backgroundColor: '#D1FAE5' }]}
                onPress={() => setNotify((prev) => ({ ...prev, [u.id]: !prev[u.id] }))}
              >
                <Text style={[s.notifyBtnText, notify[u.id] && { color: '#047857' }]}>
                  {notify[u.id] ? 'Notify' : 'Skip'}
                </Text>
              </Pressable>
            </View>
          ))}
        </View>

        <View style={{ height: 16 }} />
        <Button label="Submit incident" onPress={onSubmit} loading={createMut.isPending} fullWidth />
      </ScrollView>
    </>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F4F4F2' },
  label: { fontSize: 13, fontWeight: '600', color: '#475569', marginBottom: 6, marginTop: 12 },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap' },
  textarea: { backgroundColor: '#FFFFFF', borderWidth: 1, borderColor: '#E2E8F0', borderRadius: 12, padding: 12, fontSize: 15, color: '#0F172A', minHeight: 120 },
  photoRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  photoBox: { width: 84, height: 84, borderRadius: 10, backgroundColor: '#DBEAFE', alignItems: 'center', justifyContent: 'center' },
  photoRemove: { position: 'absolute', top: 4, right: 4, backgroundColor: '#FEE2E2', borderRadius: 8, padding: 2 },
  photoAdd: { width: 84, height: 84, borderRadius: 10, borderWidth: 1, borderColor: '#CBD5E1', borderStyle: 'dashed', alignItems: 'center', justifyContent: 'center' },
  photoAddText: { fontSize: 11, color: '#94A3B8', marginTop: 4 },
  notifyCard: { backgroundColor: '#F8FAFC', borderRadius: 14, borderWidth: 1, borderColor: '#E2E8F0', padding: 12 },
  notifyRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 8 },
  notifyName: { flex: 1, fontSize: 14, fontWeight: '600', color: '#0F172A', marginLeft: 10 },
  notifyBtn: { backgroundColor: '#DBEAFE', borderRadius: 10, paddingHorizontal: 12, paddingVertical: 6 },
  notifyBtnText: { fontSize: 12, fontWeight: '700', color: '#1D4ED8' },
});
