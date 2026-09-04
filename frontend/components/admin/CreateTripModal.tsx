import React, { useEffect, useMemo, useState } from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';
import { ClipboardCheck } from 'lucide-react-native';
import { useConductors, useCreateTrip, useDrivers, useRoutes, useVehicles } from '@/lib/queries';
import { useToast } from '@/components/ui/Toast';
import { Modal } from '@/components/ui/Modal';
import { Field } from '@/components/ui/Field';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { TRIP_STATUS_LABELS, type TripStatus } from '@/lib/types';

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
  const [fareOverride, setFareOverride] = useState('');
  const [cargoOverride, setCargoOverride] = useState('');
  const [status, setStatus] = useState<TripStatus>('planned');

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
  const statusOptions = (Object.keys(TRIP_STATUS_LABELS) as TripStatus[]).map((st) => ({
    label: TRIP_STATUS_LABELS[st],
    value: st,
  }));

  const selectedRoute = useMemo(
    () => (routesQ.data?.items ?? []).find((r) => r.id === routeId) ?? null,
    [routesQ.data, routeId],
  );

  useEffect(() => {
    if (!selectedRoute) return;
    if (!fareOverride) setFareOverride(String(selectedRoute.base_fare_passenger ?? ''));
    if (!cargoOverride) setCargoOverride(String(selectedRoute.base_fare_cargo_per_kg ?? ''));
  }, [selectedRoute, fareOverride, cargoOverride]);

  const reset = () => {
    setRouteId(null); setVehicleId(null); setDriverId(null); setConductorId(null);
    setDate(toDateInput(new Date())); setTime('08:00');
    setFareOverride(''); setCargoOverride(''); setStatus('planned');
  };
  const close = () => { reset(); onClose(); };

  const onSubmit = async () => {
    if (!routeId) return toast.error('Route is required');
    if (!vehicleId) return toast.error('Vehicle is required');
    if (!driverId) return toast.error('Driver is required');
    if (!conductorId) return toast.error('Conductor is required');
    const dt = new Date(`${date}T${time || '00:00'}`);
    if (Number.isNaN(dt.getTime())) return toast.error('Date/time is invalid');
    const fare = parseFloat(fareOverride);
    if (!Number.isFinite(fare) || fare < 0) return toast.error('Fare must be ≥ 0');
    const cargo = cargoOverride ? parseFloat(cargoOverride) : null;
    if (cargo !== null && (!Number.isFinite(cargo) || cargo < 0)) return toast.error('Cargo fare must be ≥ 0');
    try {
      await create.mutateAsync({
        route_id: routeId,
        vehicle_id: vehicleId,
        driver_id: driverId,
        conductor_id: conductorId,
        scheduled_departure: dt.toISOString(),
        fare_override: fare,
        cargo_rate_override: cargo,
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
      <View style={s.row}>
        <View style={s.col}>
          <Field label="Fare (₦)" required helperText="Pre-filled from the route">
            <TextInput style={s.input} value={fareOverride} onChangeText={setFareOverride} placeholder="0" placeholderTextColor="#94A3B8" keyboardType="decimal-pad" />
          </Field>
        </View>
        <View style={s.col}>
          <Field label="Cargo /kg (₦)">
            <TextInput style={s.input} value={cargoOverride} onChangeText={setCargoOverride} placeholder="optional" placeholderTextColor="#94A3B8" keyboardType="decimal-pad" />
          </Field>
        </View>
      </View>
      <Field label="Status" required>
        <Select value={status} onChange={setStatus} options={statusOptions} />
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
  spacerL: { height: 12 },
  spacerS: { height: 8 },
});
