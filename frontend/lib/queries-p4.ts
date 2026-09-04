import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getPage, getSingle, postSingle, postNoContent, patchSingle } from '@/lib/api';

export interface InspectionItem {
  key: string;
  label: string;
  status: string;
  note?: string | null;
}

export interface Inspection {
  id: string;
  trip_id: string;
  vehicle_id?: string | null;
  driver_id?: string | null;
  items: InspectionItem[];
  odometer_reading?: number | null;
  fuel_level_pct?: number | null;
  signature_confirmed: boolean;
  status: string;
  submitted_at?: string | null;
}

export interface InspectionUpsert {
  trip_id: string;
  vehicle_id?: string | null;
  driver_id?: string | null;
  items: InspectionItem[];
  odometer_reading?: number | null;
  fuel_level_pct?: number | null;
  signature_confirmed: boolean;
}

export interface Incident {
  id: string;
  trip_id?: string | null;
  vehicle_id?: string | null;
  branch_id?: string | null;
  severity: string;
  category: string;
  description: string;
  photos: string[];
  status: string;
  reported_by?: string | null;
  notified: string[];
  created_at: string;
}

export interface IncidentSummary {
  severe: number;
  moderate: number;
  minor: number;
  closed: number;
}

export function useInspections(tripId?: string) {
  return useQuery({
    queryKey: ['inspections', tripId],
    queryFn: () =>
      getPage<Inspection>('/inspections', tripId ? { trip_id: tripId } : {}),
    enabled: !!tripId,
  });
}

export function useCreateInspection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: InspectionUpsert) => postSingle<Inspection, InspectionUpsert>('/inspections', data),
    onSuccess: (d) => {
      qc.invalidateQueries({ queryKey: ['inspections', d.trip_id] });
    },
  });
}

export function useUpdateInspection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: InspectionUpsert }) =>
      patchSingle<Inspection, InspectionUpsert>(`/inspections/${id}`, data),
    onSuccess: (d) => {
      qc.invalidateQueries({ queryKey: ['inspections', d.trip_id] });
    },
  });
}

export function useSubmitInspection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => postSingle<Inspection>(`/inspections/${id}/submit`),
    onSuccess: (d) => {
      qc.invalidateQueries({ queryKey: ['inspections', d.trip_id] });
      qc.invalidateQueries({ queryKey: ['trips'] });
    },
  });
}

export function useIncidents(params?: { status?: string; severity?: string }) {
  return useQuery({
    queryKey: ['incidents', params],
    queryFn: () => getPage<Incident>('/incidents', (params ?? {}) as Record<string, unknown>),
  });
}

export function useIncidentSummary() {
  return useQuery({
    queryKey: ['incidents', 'summary'],
    queryFn: () => getSingle<IncidentSummary>('/incidents/summary'),
  });
}

export function useCreateIncident() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<Incident>) => postSingle<Incident, Partial<Incident>>('/incidents', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['incidents'] });
      qc.invalidateQueries({ queryKey: ['incidents', 'summary'] });
      qc.invalidateQueries({ queryKey: ['notifications'] });
    },
  });
}

export function useAcknowledgeIncident() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => postSingle<Incident>(`/incidents/${id}/acknowledge`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['incidents'] });
      qc.invalidateQueries({ queryKey: ['incidents', 'summary'] });
    },
  });
}

export function useResolveIncident() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, note }: { id: string; note?: string }) =>
      postSingle<Incident>(`/incidents/${id}/resolve${note ? `?resolution_note=${encodeURIComponent(note)}` : ''}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['incidents'] });
      qc.invalidateQueries({ queryKey: ['incidents', 'summary'] });
    },
  });
}
