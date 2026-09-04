import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getPage, getSingle, postSingle } from '@/lib/api';

export interface VehiclePosition {
  id?: string;
  vehicle_id: string;
  branch_id?: string | null;
  lat: number;
  lng: number;
  speed_kph: number;
  heading_deg?: number | null;
  status: string;
  reg_number?: string | null;
  driver_name?: string | null;
  trip_id?: string | null;
  recorded_at?: string | null;
}

export interface FleetPositionsResponse {
  items: VehiclePosition[];
  total: number;
  generated_at: string;
}

export interface VehicleTransfer {
  id: string;
  vehicle_id: string;
  from_branch_id: string;
  to_branch_id: string;
  initiated_by?: string | null;
  confirmed_by?: string | null;
  returned_by?: string | null;
  cancelled_by?: string | null;
  status: 'initiated' | 'confirmed' | 'returned' | 'cancelled';
  reason?: string | null;
  notes?: string | null;
  expected_return_at?: string | null;
  initiated_at?: string | null;
  confirmed_at?: string | null;
  returned_at?: string | null;
  cancelled_at?: string | null;
  created_at: string;
  updated_at: string;
}

export function useFleetPositions(params?: { branch_id?: string; status?: string }) {
  return useQuery({
    queryKey: ['fleet', 'positions', params ?? {}],
    queryFn: () =>
      getSingle<FleetPositionsResponse>('/fleet/positions', (params ?? {}) as Record<string, unknown>),
    refetchInterval: 30_000,
    staleTime: 15_000,
  });
}

export function useVehicleTransfers(params?: { status?: string }) {
  return useQuery({
    queryKey: ['vehicle-transfers', params ?? {}],
    queryFn: () => getPage<VehicleTransfer>('/vehicle-transfers', (params ?? {}) as Record<string, unknown>),
    staleTime: 15_000,
  });
}

export function useVehicleTransfer(id: string) {
  return useQuery({
    queryKey: ['vehicle-transfers', id],
    queryFn: () => getSingle<VehicleTransfer>(`/vehicle-transfers/${id}`),
    enabled: !!id,
  });
}

export function useCreateTransfer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      vehicle_id: string;
      to_branch_id: string;
      reason?: string | null;
      notes?: string | null;
      expected_return_at?: string | null;
    }) => postSingle<VehicleTransfer>('/vehicle-transfers', body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['vehicle-transfers'] });
      qc.invalidateQueries({ queryKey: ['vehicles'] });
    },
  });
}

export function useAdvanceTransfer(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ action, notes }: { action: 'confirm' | 'return' | 'cancel'; notes?: string }) =>
      postSingle<VehicleTransfer>(`/vehicle-transfers/${id}/${action}`, { notes }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['vehicle-transfers'] });
      qc.invalidateQueries({ queryKey: ['vehicle-transfers', id] });
      qc.invalidateQueries({ queryKey: ['vehicles'] });
    },
  });
}queries-p5.ts
