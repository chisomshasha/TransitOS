import React, { useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { Building2, MapPin } from 'lucide-react-native';
import { useCreateBranch } from '@/lib/queries';
import { useToast } from '@/components/ui/Toast';
import { Modal } from '@/components/ui/Modal';
import { Field } from '@/components/ui/Field';
import { Button } from '@/components/ui/Button';
import { MapModal } from '@/components/ui/MapModal';

export interface CreateBranchModalProps {
  visible?: boolean;
  open?: boolean;
  onClose: () => void;
  onSaved?: () => void;
}

export function CreateBranchModal({ visible, open, onClose, onSaved }: CreateBranchModalProps) {
  const show = !!(visible ?? open);
  const create = useCreateBranch();
  const toast = useToast();
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [address, setAddress] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [picked, setPicked] = useState<{ lat: number; lng: number } | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);

  const reset = () => { setName(''); setCode(''); setCity(''); setState(''); setAddress(''); setPhone(''); setEmail(''); setPicked(null); };
  const close = () => { reset(); onClose(); };

  const onSubmit = async () => {
    if (!name.trim()) return toast.error('Branch name is required');
    if (!code.trim()) return toast.error('Branch code is required');
    if (!city.trim()) return toast.error('City is required');
    if (!state.trim()) return toast.error('State is required');
    if (!address.trim()) return toast.error('Address is required');
    if (email && !/^\S+@\S+.\S+$/.test(email)) return toast.error('Email looks invalid');
    try {
      await create.mutateAsync({
        name: name.trim(),
        code: code.trim().toUpperCase(),
        city: city.trim(),
        state: state.trim(),
        address: address.trim(),
        contact_phone: phone.trim() || null,
        contact_email: email.trim() || null,
        gps: picked ? { lat: picked.lat, lng: picked.lng } : null,
        status: 'active',
        is_active: true,
      } as any);
      toast.success(`Branch "${name.trim()}" created`);
      reset();
      onSaved?.();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not create branch');
    }
  };

  return (
    <>
      <Modal visible={show} onClose={close} title="New branch" variant="sheet">
        <View style={s.infoBanner}>
          <Building2 size={18} color="#0E7490" />
          <Text style={s.infoText}>
            Branches are the top-level operating unit. Vehicles, users, and routes are all scoped to a branch.
          </Text>
        </View>
        <Field label="Name" required>
          <TextInput style={s.input} value={name} onChangeText={setName} placeholder="e.g. Lagos Island Terminal" placeholderTextColor="#94A3B8" />
        </Field>
        <Field label="Code" required helperText="Short uppercase identifier (e.g. LOS)">
          <TextInput style={s.input} value={code} onChangeText={setCode} placeholder="LOS" placeholderTextColor="#94A3B8" autoCapitalize="characters" />
        </Field>
        <View style={s.row}>
          <View style={s.col}>
            <Field label="City" required>
              <TextInput style={s.input} value={city} onChangeText={setCity} placeholder="Lagos" placeholderTextColor="#94A3B8" />
            </Field>
          </View>
          <View style={s.col}>
            <Field label="State" required>
              <TextInput style={s.input} value={state} onChangeText={setState} placeholder="Lagos" placeholderTextColor="#94A3B8" />
            </Field>
          </View>
        </View>
        <Field label="Address" required>
          <TextInput style={s.input} value={address} onChangeText={setAddress} placeholder="123 Marina Road" placeholderTextColor="#94A3B8" />
        </Field>
        <View style={s.row}>
          <View style={s.col}>
            <Field label="Phone">
              <TextInput style={s.input} value={phone} onChangeText={setPhone} placeholder="+234…" placeholderTextColor="#94A3B8" keyboardType="phone-pad" />
            </Field>
          </View>
          <View style={s.col}>
            <Field label="Email">
              <TextInput style={s.input} value={email} onChangeText={setEmail} placeholder="branch@…" placeholderTextColor="#94A3B8" autoCapitalize="none" keyboardType="email-address" />
            </Field>
          </View>
        </View>
        <Field label="Location" helperText="Optional but recommended for the map view">
          <Pressable onPress={() => setPickerOpen(true)} style={s.input} accessibilityRole="button" accessibilityLabel="Pick branch location on map">
            <View style={{ flexDirection: 'row', alignItems: 'center', flex: 1 }}>
              <MapPin size={16} color={picked ? '#0E7490' : '#94A3B8'} />
              <Text style={{ fontSize: 16, marginLeft: 8, flex: 1, color: picked ? '#1E293B' : '#94A3B8' }} numberOfLines={1}>
                {picked ? `${picked.lat.toFixed(5)}, ${picked.lng.toFixed(5)}` : 'Tap to pick on map'}
              </Text>
              {picked ? (
                <Pressable onPress={() => setPicked(null)} hitSlop={8} style={{ paddingHorizontal: 8 }} accessibilityLabel="Clear location">
                  <Text style={{ fontSize: 12, color: '#64748B' }}>Clear</Text>
                </Pressable>
              ) : null}
            </View>
          </Pressable>
        </Field>
        <View style={s.spacerL} />
        <Button label="Create branch" onPress={onSubmit} loading={create.isPending} fullWidth />
        <View style={s.spacerS} />
        <Button label="Cancel" onPress={close} variant="ghost" fullWidth />
      </Modal>
      <MapModal
        visible={pickerOpen}
        onClose={() => setPickerOpen(false)}
        title="Pick branch location"
        points={[]}
        center={picked ?? { lat: 9.082, lng: 8.6753 }}
        zoom={picked ? 12 : 6}
        pickMode
        pickedPoint={picked}
        onPick={(pt) => setPicked(pt)}
      />
    </>
  );
}

const s = StyleSheet.create({
  infoBanner: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#ECFEFF', borderRadius: 12, padding: 12, marginBottom: 12 },
  infoText: { fontSize: 13, color: '#0B3D91', marginLeft: 8, flex: 1 },
  input: { height: 48, paddingHorizontal: 12, borderRadius: 12, borderWidth: 1, borderColor: '#E2E8F0', backgroundColor: '#FFFFFF', fontSize: 16, color: '#0F172A', justifyContent: 'center' },
  row: { flexDirection: 'row', marginHorizontal: -6 },
  col: { flex: 1, paddingHorizontal: 6 },
  spacerL: { height: 12 },
  spacerS: { height: 8 },
});
