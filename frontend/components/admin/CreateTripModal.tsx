import React, { useMemo, useState } from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';
import { ClipboardCheck } from 'lucide-react-native';
import { useConductors, useCreateTrip, useDrivers, useRoutes, useVehicles } from '@/lib/queries';
import { useToast } from '@/components/ui/Toast';
import { Modal } from '@/components/ui/Modal';
import { Field } from '@/components/ui/Field';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';

export interface CreateTripModalProps {
  visible?: boolean;
  open?: boolean;
  onClose: () => void;
  onSaved?: () => void;
}

const pad2 = (n: number) => String(n).padStart(2, '0');
const toDateInput = (d: Date) => `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;

export function CreateTripModal({ visible, open, onClose, onSaved }: CreateTripModalProps) {
  const show = !!(visible ?? open);
  const create = useCreateTrip();
  const toast = useToast();
  const routesQ = useRoutes({ page: 1, page_size: 100 });
  const vehiclesQ = useVehicles({ page: 1, page_size: 200 });
  const driversQ = useDrivers({ page: 1, page_size: 200 });
  const conductorsQ = useConductors({ page: 1, page_size: 200 });

  const [routeId, setRouteId] = useState<string | null>(null);
  const [vehicleId, setVehicleId] = useState<string | null>(null);
  const [driverId, setDriverId] = useState<string | null>(null);
  const [conductorId, setConductorId] = useState<string | null>(null);
  const [date, setDate] = useState(() => toDateInput(new Date()));
  const [time, setTime] = useState('08:00');

  const routeOptions = (routesQ.data?.items ?? []).map((r) => ({ label: r.name, value: r.id }));
  const vehicleOptions = (vehiclesQ.data?.items ?? [])
    .filter((v) => v.status === 'available')
    .map((v) => ({ label: `${v.reg_number} · ${v.type}`, value: v.id }));
  const driverOptions = (driversQ.data?.items ?? [])
    .filter((d) => d.status === 'active')
    .map((d) => ({ label: d.full_name ?? d.id, value: d.id }));
  const conductorOptions = (conductorsQ.data?.items ?? [])
    .filter((c) => c.status === 'active')
    .map((c) => ({ label: c.full_name ?? c.id, value: c.id }));
  const selectedRoute = useMemo(
    () => (routesQ.data?.items ?? []).find((r) => r.id === routeId) ?? null,
    [routesQ.data, routeId],
  );

  // The API requires `scheduled_arrival` and rejects one that is not after
  // the departure, so it is derived from the route's estimated duration.
  const durationH = Math.max(1, Math.ceil(selectedRoute?.estimated_duration_hours ?? 1));
  const departure = useMemo(() => {
    const d = new Date(`${date}T${time || '00:00'}`);
    return Number.isNaN(d.getTime()) ? null : d;
  }, [date, time]);
  const arrival = useMemo(
    () => (departure ? new Date(departure.getTime() + durationH * 60 * 60 * 1000) : null),
    [departure, durationH],
  );
  const arrivalPreview = arrival
    ? arrival.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })
    : '—';

  const reset = () => {
    setRouteId(null); setVehicleId(null); setDriverId(null); setConductorId(null);
    setDate(toDateInput(new Date())); setTime('08:00');
  };
  const close = () => { reset(); onClose(); };

  const onSubmit = async () => {
    if (!routeId) return toast.error('Route is required');
    if (!vehicleId) return toast.error('Vehicle is required');
    if (!driverId) return toast.error('Driver is required');
    if (!conductorId) return toast.error('Conductor is required');
    if (!departure) return toast.error('Date/time is invalid');
    if (!arrival) return toast.error('Date/time is invalid');
    try {
      await create.mutateAsync({
        route_id: routeId,
        vehicle_id: vehicleId,
        driver_id: driverId,
        conductor_id: conductorId,
        scheduled_departure: departure.toISOString(),
        scheduled_arrival: arrival.toISOString(),
      });
      toast.success('Trip created');
      reset();
      onSaved?.();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not create trip');
    }
  };

  return (
    <Modal visible={show} onClose={close} title="New trip" variant="sheet">
      <View style={s.infoBanner}>
        <ClipboardCheck size={18} color="#0E7490" />
        <Text style={s.infoText}>
          A trip needs an active route, an available vehicle, and an active driver and conductor.
        </Text>
      </View>
      <Field label="Route" required>
        <Select value={routeId} onChange={setRouteId} options={routeOptions} placeholder="Select route" />
      </Field>
      <Field label="Vehicle" required helperText="Only vehicles with status Available are listed">
        <Select value={vehicleId} onChange={setVehicleId} options={vehicleOptions} placeholder="Select vehicle" />
      </Field>
      <View style={s.row}>
        <View style={s.col}>
          <Field label="Driver" required>
            <Select value={driverId} onChange={setDriverId} options={driverOptions} placeholder="Select driver" />
          </Field>
        </View>
        <View style={s.col}>
          <Field label="Conductor" required>
            <Select value={conductorId} onChange={setConductorId} options={conductorOptions} placeholder="Select conductor" />
          </Field>
        </View>
      </View>
      <View style={s.row}>
        <View style={s.col}>
          <Field label="Date" required>
            <TextInput style={s.input} value={date} onChangeText={setDate} placeholder="2026-01-15" placeholderTextColor="#94A3B8" autoCapitalize="none" />
          </Field>
        </View>
        <View style={s.col}>
          <Field label="Departure time" required>
            <TextInput style={s.input} value={time} onChangeText={setTime} placeholder="08:00" placeholderTextColor="#94A3B8" autoCapitalize="none" />
          </Field>
        </View>
      </View>
      <Field
        label="Scheduled arrival"
        helperText={
          selectedRoute
            ? `Derived from the route: departure + ${durationH}h. The trip starts in the Planned state.`
            : 'Derived from the selected route once one is chosen.'
        }
      >
        <View style={s.readOnly}>
          <Text style={s.readOnlyText}>
            {selectedRoute ? arrivalPreview : '—'}
          </Text>
        </View>
      </Field>
      <View style={s.spacerL} />
      <Button label="Create trip" onPress={onSubmit} loading={create.isPending} fullWidth />
      <View style={s.spacerS} />
      <Button label="Cancel" onPress={close} variant="ghost" fullWidth />
    </Modal>
  );
}

const s = StyleSheet.create({
  infoBanner: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#ECFEFF', borderRadius: 12, padding: 12, marginBottom: 12 },
  infoText: { fontSize: 13, color: '#0B3D91', marginLeft: 8, flex: 1 },
  input: { height: 48, paddingHorizontal: 12, borderRadius: 12, borderWidth: 1, borderColor: '#E2E8F0', backgroundColor: '#FFFFFF', fontSize: 16, color: '#0F172A' },
  row: { flexDirection: 'row', marginHorizontal: -6 },
  col: { flex: 1, paddingHorizontal: 6 },
  readOnly: { height: 48, paddingHorizontal: 12, borderRadius: 12, borderWidth: 1, borderColor: '#E2E8F0', backgroundColor: '#F8FAFC', justifyContent: 'center' },
  readOnlyText: { fontSize: 16, color: '#475569' },
  spacerL: { height: 12 },
  spacerS: { height: 8 },
});
