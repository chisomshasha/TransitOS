/**
 * Sprint D — financial record lifecycle hooks.
 *
 * Expenses, fuel logs and maintenance records were create-only in the
 * app: the list screens could record a new entry but there was no way
 * to read one back, correct a typo, or remove a mistake. The backend
 * has had full CRUD on all three since Sprint B/C — these hooks are the
 * missing client side.
 *
 * Note the payloads here are the ones the backend actually accepts.
 * The original create forms sent `note` / `cost` and omitted
 * `vehicle_id` / `scope` / `occurred_at`, which the API rejects with a
 * 422. See `app/(app)/expenses.tsx`, `fuel.tsx` and `maintenance.tsx`.
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from '@tanstack/react-query';
import { deleteNoContent, getSingle, patchSingle } from '@/lib/api';
import type { Expense, FuelLog, MaintenanceRecord } from '@/lib/types';

// ─── Expenses ───────────────────────────────────────────────────────────────
export function useExpense(id: string): UseQueryResult<Expense> {
  return useQuery({
    queryKey: ['expenses', id],
    queryFn: () => getSingle<Expense>(`/expenses/${id}`),
    enabled: !!id,
  });
}

export function useUpdateExpense(id: string): UseMutationResult<
  Expense,
  unknown,
  Record<string, unknown>
> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => patchSingle<Expense>(`/expenses/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['expenses'] });
      qc.invalidateQueries({ queryKey: ['trips'] });
    },
  });
}

export function useDeleteExpense(): UseMutationResult<void, unknown, string> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteNoContent(`/expenses/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['expenses'] });
      qc.invalidateQueries({ queryKey: ['trips'] });
    },
  });
}

// ─── Fuel logs ──────────────────────────────────────────────────────────────
export function useFuelLog(id: string): UseQueryResult<FuelLog> {
  return useQuery({
    queryKey: ['fuel-logs', id],
    queryFn: () => getSingle<FuelLog>(`/fuel-logs/${id}`),
    enabled: !!id,
  });
}

export function useUpdateFuelLog(id: string): UseMutationResult<
  FuelLog,
  unknown,
  Record<string, unknown>
> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => patchSingle<FuelLog>(`/fuel-logs/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['fuel-logs'] });
      qc.invalidateQueries({ queryKey: ['vehicles'] });
    },
  });
}

export function useDeleteFuelLog(): UseMutationResult<void, unknown, string> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteNoContent(`/fuel-logs/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['fuel-logs'] });
      qc.invalidateQueries({ queryKey: ['vehicles'] });
    },
  });
}

/** km/L efficiency for a vehicle — powers the fuel screen's summary. */
export function useVehicleFuelEfficiency(vehicleId: string): UseQueryResult<{
  km_per_liter: number | null;
  total_liters: number;
  total_cost: number;
}> {
  return useQuery({
    queryKey: ['fuel-logs', 'efficiency', vehicleId],
    queryFn: () =>
      getSingle(`/fuel-logs/vehicle/${vehicleId}/efficiency`) as Promise<{
        km_per_liter: number | null;
        total_liters: number;
        total_cost: number;
      }>,
    enabled: !!vehicleId,
  });
}

// ─── Maintenance records ────────────────────────────────────────────────────
export function useMaintenanceRecord(id: string): UseQueryResult<MaintenanceRecord> {
  return useQuery({
    queryKey: ['maintenance', id],
    queryFn: () => getSingle<MaintenanceRecord>(`/maintenance/${id}`),
    enabled: !!id,
  });
}

export function useUpdateMaintenanceRecord(id: string): UseMutationResult<
  MaintenanceRecord,
  unknown,
  Record<string, unknown>
> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => patchSingle<MaintenanceRecord>(`/maintenance/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['maintenance'] });
      qc.invalidateQueries({ queryKey: ['vehicles'] });
    },
  });
}

export function useDeleteMaintenanceRecord(): UseMutationResult<void, unknown, string> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteNoContent(`/maintenance/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['maintenance'] });
      qc.invalidateQueries({ queryKey: ['vehicles'] });
    },
  });
}

/** Upcoming scheduled maintenance for one vehicle. */
export function useUpcomingMaintenance(vehicleId: string): UseQueryResult<
  MaintenanceRecord[]
> {
  return useQuery({
    queryKey: ['maintenance', 'upcoming', vehicleId],
    queryFn: () =>
      getSingle<MaintenanceRecord[]>(
        `/maintenance/vehicle/${vehicleId}/upcoming`
      ) as Promise<MaintenanceRecord[]>,
    enabled: !!vehicleId,
  });
}
