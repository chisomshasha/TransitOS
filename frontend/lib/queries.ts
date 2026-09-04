/**
 * Query / mutation hooks for Sprint A + Phase 6 report expansions.
 */
import {
  useMutation, useQuery, useQueryClient,
  type UseMutationResult, type UseQueryResult,
} from '@tanstack/react-query';
import { getPage, getSingle, deleteNoContent, patchNoContent, patchSingle, postNoContent, postSingle } from './api';
import type {
  Branch, CashUp, Conductor, Driver, Expense, FuelEfficiency, FuelLog,
  MaintenanceRecord, ManifestEntry, OperationsSummary, DailyTimeline,
  BranchPerformance, VehicleRoi, Page, Route, Trip, User, Vehicle,
} from './types';

// Phase 6 report types
export interface ProfitLoss {
  window: { from: string; to: string };
  revenue: number;
  expenses_breakdown: { trip_expenses: number; fuel: number; maintenance: number; standalone: number };
  total_expenses: number;
  net: number;
}

export interface CashFlowSeries {
  bucket: 'day' | 'week' | 'month';
  series: Array<{ label: string; revenue: number; expenses: number; net: number }>;
}

export interface TopRoute {
  route_id: string;
  name: string;
  origin_city?: string | null;
  destination_city?: string | null;
  trips: number;
  revenue: number;
  passengers: number;
  cargo_kg: number;
}

export interface DriverPerformance {
  driver_id: string;
  name: string;
  trips: number;
  completed: number;
  cancelled: number;
  completion_pct: number;
  revenue: number;
  passengers: number;
}

export interface VehicleUtilization {
  vehicle_id: string;
  reg_number?: string | null;
  trips: number;
  revenue: number;
  passengers: number;
  downtime_days: number;
  utilization_pct: number;
}

export interface IncidentsSummary {
  window: { from: string; to: string };
  total: number;
  by_severity: Record<string, number>;
  by_category: Record<string, number>;
  by_status: Record<string, number>;
}

export const qk = {
  branches: (params?: Record<string, unknown>) => ['branches', params ?? {}] as const,
  branch: (id: string) => ['branches', id] as const,
  users: (params?: Record<string, unknown>) => ['users', params ?? {}] as const,
  user: (id: string) => ['users', id] as const,
  vehicles: (params?: Record<string, unknown>) => ['vehicles', params ?? {}] as const,
  vehicle: (id: string) => ['vehicles', id] as const,
  drivers: (params?: Record<string, unknown>) => ['drivers', params ?? {}] as const,
  driver: (id: string) => ['drivers', id] as const,
  conductors: (params?: Record<string, unknown>) => ['conductors', params ?? {}] as const,
  conductor: (id: string) => ['conductors', id] as const,
  routes: (params?: Record<string, unknown>) => ['routes', params ?? {}] as const,
  trips: (params?: Record<string, unknown>) => ['trips', params ?? {}] as const,
  trip: (id: string) => ['trips', id] as const,
  manifest: (tripId: string) => ['manifest', tripId] as const,
  cashUps: (params?: Record<string, unknown>) => ['cash-ups', params ?? {}] as const,
  cashUp: (id: string) => ['cash-ups', id] as const,
  expenses: (params?: Record<string, unknown>) => ['expenses', params ?? {}] as const,
  fuelLogs: (params?: Record<string, unknown>) => ['fuel-logs', params ?? {}] as const,
  fuelEfficiency: (vehicleId: string) => ['fuel-logs', 'efficiency', vehicleId] as const,
  maintenance: (params?: Record<string, unknown>) => ['maintenance', params ?? {}] as const,
  me: ['me'] as const,
};

// ─── branches ────────────────────────────────────────────────────────────────
export function useBranches(params?: Record<string, unknown>): UseQueryResult<Page<Branch>> {
  return useQuery({ queryKey: qk.branches(params), queryFn: () => getPage<Branch>('/branches', params), staleTime: 30_000 });
}
export function useBranch(id: string): UseQueryResult<Branch> {
  return useQuery({ queryKey: qk.branch(id), queryFn: () => getSingle<Branch>(`/branches/${id}`), enabled: !!id });
}
export function useCreateBranch(): UseMutationResult<Branch, unknown, Partial<Branch>> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => postSingle<Branch, Partial<Branch>>('/branches', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['branches'] }),
  });
}
export function useUpdateBranch(id: string): UseMutationResult<Branch, unknown, Partial<Branch>> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => patchSingle<Branch, Partial<Branch>>(`/branches/${id}`, body),
    onSuccess: (data) => { qc.setQueryData(qk.branch(id), data); qc.invalidateQueries({ queryKey: ['branches'] }); },
  });
}

// ─── users ───────────────────────────────────────────────────────────────────
export function useUsers(params?: Record<string, unknown>): UseQueryResult<Page<User>> {
  return useQuery({ queryKey: qk.users(params), queryFn: () => getPage<User>('/users', params), staleTime: 30_000 });
}
export function useUsersByRole(role: string, params?: Record<string, unknown>): UseQueryResult<Page<User>> {
  return useUsers({ role, page: 1, page_size: 100, ...(params ?? {}) });
}
export function useUser(id: string): UseQueryResult<User> {
  return useQuery({ queryKey: qk.user(id), queryFn: () => getSingle<User>(`/users/${id}`), enabled: !!id });
}
export function useCreateUser(): UseMutationResult<User, unknown, Record<string, unknown>> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => postSingle<User>('/users', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  });
}
export function useUpdateUser(id: string): UseMutationResult<User, unknown, Partial<User> & { new_password?: string }> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => patchSingle<User, Partial<User>>(`/users/${id}`, body),
    onSuccess: (data) => { qc.setQueryData(qk.user(id), data); qc.invalidateQueries({ queryKey: ['users'] }); },
  });
}
export function useDeleteUser(): UseMutationResult<void, unknown, string> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id) => deleteNoContent(`/users/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  });
}

// ─── vehicles ────────────────────────────────────────────────────────────────
export function useVehicles(params?: Record<string, unknown>): UseQueryResult<Page<Vehicle>> {
  return useQuery({ queryKey: qk.vehicles(params), queryFn: () => getPage<Vehicle>('/vehicles', params), staleTime: 30_000 });
}
export function useVehicle(id: string): UseQueryResult<Vehicle> {
  return useQuery({ queryKey: qk.vehicle(id), queryFn: () => getSingle<Vehicle>(`/vehicles/${id}`), enabled: !!id });
}
export function useCreateVehicle(): UseMutationResult<Vehicle, unknown, Record<string, unknown>> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => postSingle<Vehicle>('/vehicles', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['vehicles'] }),
  });
}
export function useUpdateVehicle(id: string): UseMutationResult<Vehicle, unknown, Record<string, unknown>> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => patchSingle<Vehicle, Record<string, unknown>>(`/vehicles/${id}`, body),
    onSuccess: (data) => { qc.setQueryData(qk.vehicle(id), data); qc.invalidateQueries({ queryKey: ['vehicles'] }); },
  });
}

// ─── drivers ─────────────────────────────────────────────────────────────────
export function useDrivers(params?: Record<string, unknown>): UseQueryResult<Page<Driver>> {
  return useQuery({ queryKey: qk.drivers(params), queryFn: () => getPage<Driver>('/drivers', params), staleTime: 30_000 });
}
export function useDriver(id: string): UseQueryResult<Driver> {
  return useQuery({ queryKey: qk.driver(id), queryFn: () => getSingle<Driver>(`/drivers/${id}`), enabled: !!id });
}
export function useCreateDriver(): UseMutationResult<Driver, unknown, Record<string, unknown>> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => postSingle<Driver>('/drivers', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['drivers'] }),
  });
}
export function useUpdateDriver(id: string): UseMutationResult<Driver, unknown, Record<string, unknown>> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => patchSingle<Driver, Record<string, unknown>>(`/drivers/${id}`, body),
    onSuccess: (data) => { qc.setQueryData(qk.driver(id), data); qc.invalidateQueries({ queryKey: ['drivers'] }); },
  });
}

// ─── conductors ──────────────────────────────────────────────────────────────
export function useConductors(params?: Record<string, unknown>): UseQueryResult<Page<Conductor>> {
  return useQuery({ queryKey: qk.conductors(params), queryFn: () => getPage<Conductor>('/conductors', params), staleTime: 30_000 });
}
export function useConductor(id: string): UseQueryResult<Conductor> {
  return useQuery({ queryKey: qk.conductor(id), queryFn: () => getSingle<Conductor>(`/conductors/${id}`), enabled: !!id });
}
export function useCreateConductor(): UseMutationResult<Conductor, unknown, Record<string, unknown>> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => postSingle<Conductor>('/conductors', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['conductors'] }),
  });
}
export function useUpdateConductor(id: string): UseMutationResult<Conductor, unknown, Record<string, unknown>> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => patchSingle<Conductor, Record<string, unknown>>(`/conductors/${id}`, body),
    onSuccess: (data) => { qc.setQueryData(qk.conductor(id), data); qc.invalidateQueries({ queryKey: ['conductors'] }); },
  });
}

// ─── auth ────────────────────────────────────────────────────────────────────
export function useForgotPassword(): UseMutationResult<void, unknown, { email: string }> {
  return useMutation({ mutationFn: (body) => postNoContent('/auth/forgot-password', body) });
}
export function useResetPassword(): UseMutationResult<void, unknown, { token: string; new_password: string }> {
  return useMutation({ mutationFn: (body) => postNoContent('/auth/reset-password', body) });
}

// ─── cash-ups ────────────────────────────────────────────────────────────────
export function useRejectCashUp(id: string): UseMutationResult<CashUp, unknown, string> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (reason) => postSingle<CashUp>(`/cash-ups/${id}/reject?reason=${encodeURIComponent(reason)}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cash-ups'] });
      qc.invalidateQueries({ queryKey: ['cash-ups', id] });
      qc.invalidateQueries({ queryKey: ['trips'] });
    },
  });
}

// ─── routes ──────────────────────────────────────────────────────────────────
export function useRoutes(params?: Record<string, unknown>): UseQueryResult<Page<Route>> {
  return useQuery({ queryKey: qk.routes(params), queryFn: () => getPage<Route>('/routes', params), staleTime: 30_000 });
}
export function useRoute(id: string): UseQueryResult<Route> {
  return useQuery({ queryKey: ['routes', id], queryFn: () => getSingle<Route>(`/routes/${id}`), enabled: !!id });
}
export function useCreateRoute(): UseMutationResult<Route, unknown, Record<string, unknown>> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => postSingle<Route>('/routes', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['routes'] }),
  });
}

// ─── trips ───────────────────────────────────────────────────────────────────
export function useTrips(params?: Record<string, unknown>): UseQueryResult<Page<Trip>> {
  return useQuery({ queryKey: ['trips', params ?? {}], queryFn: () => getPage<Trip>('/trips', params), staleTime: 15_000 });
}
export function useTrip(id: string): UseQueryResult<Trip> {
  return useQuery({ queryKey: ['trips', id], queryFn: () => getSingle<Trip>(`/trips/${id}`), enabled: !!id });
}
export function useCreateTrip(): UseMutationResult<Trip, unknown, Record<string, unknown>> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => postSingle<Trip>('/trips', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['trips'] }),
  });
}
export function useChangeTripStatus(tripId: string): UseMutationResult<Trip, unknown, { status: string; cancelled_reason?: string }> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => patchSingle<Trip>(`/trips/${tripId}/status`, body),
    onSuccess: (data) => { qc.setQueryData(['trips', tripId], data); qc.invalidateQueries({ queryKey: ['trips'] }); },
  });
}

// ─── manifest ────────────────────────────────────────────────────────────────
export function useManifest(tripId: string, params?: Record<string, unknown>): UseQueryResult<Page<ManifestEntry>> {
  return useQuery({
    queryKey: ['manifest', tripId, params ?? {}],
    queryFn: () => getPage<ManifestEntry>(`/trips/${tripId}/manifest`, params),
    enabled: !!tripId,
    staleTime: 10_000,
  });
}
export function useAddManifestEntry(tripId: string): UseMutationResult<ManifestEntry, unknown, Record<string, unknown>> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => postSingle<ManifestEntry>(`/trips/${tripId}/manifest`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['manifest', tripId] });
      qc.invalidateQueries({ queryKey: ['trips', tripId] });
      qc.invalidateQueries({ queryKey: ['trips'] });
    },
  });
}
export function useDeleteManifestEntry(tripId: string): UseMutationResult<void, unknown, string> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (entryId) => deleteNoContent(`/trips/${tripId}/manifest/${entryId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['manifest', tripId] });
      qc.invalidateQueries({ queryKey: ['trips', tripId] });
      qc.invalidateQueries({ queryKey: ['trips'] });
    },
  });
}

// ─── cash-ups ────────────────────────────────────────────────────────────────
export function useCashUps(params?: Record<string, unknown>): UseQueryResult<Page<CashUp>> {
  return useQuery({ queryKey: ['cash-ups', params ?? {}], queryFn: () => getPage<CashUp>('/cash-ups', params), staleTime: 15_000 });
}
export function useCashUp(id: string): UseQueryResult<CashUp> {
  return useQuery({ queryKey: ['cash-ups', id], queryFn: () => getSingle<CashUp>(`/cash-ups/${id}`), enabled: !!id });
}
export function useCreateCashUp(): UseMutationResult<CashUp, unknown, Record<string, unknown>> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => postSingle<CashUp>('/cash-ups', body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['cash-ups'] }); qc.invalidateQueries({ queryKey: ['trips'] }); },
  });
}
export function useSubmitCashUp(id: string): UseMutationResult<CashUp, unknown, void> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => postSingle<CashUp>(`/cash-ups/${id}/submit`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cash-ups'] });
      qc.invalidateQueries({ queryKey: ['cash-ups', id] });
      qc.invalidateQueries({ queryKey: ['trips'] });
    },
  });
}
export function useApproveCashUp(id: string): UseMutationResult<CashUp, unknown, { notes?: string }> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => postSingle<CashUp>(`/cash-ups/${id}/approve`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cash-ups'] });
      qc.invalidateQueries({ queryKey: ['cash-ups', id] });
      qc.invalidateQueries({ queryKey: ['trips'] });
    },
  });
}

// ─── expenses ────────────────────────────────────────────────────────────────
export function useExpenses(params?: Record<string, unknown>): UseQueryResult<Page<Expense>> {
  return useQuery({ queryKey: ['expenses', params ?? {}], queryFn: () => getPage<Expense>('/expenses', params), staleTime: 15_000 });
}
export function useCreateExpense(): UseMutationResult<Expense, unknown, Record<string, unknown>> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => postSingle<Expense>('/expenses', body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['expenses'] }),
  });
}

// ─── fuel + maintenance ──────────────────────────────────────────────────────
export function useFuelLogs(params?: Record<string, unknown>): UseQueryResult<Page<FuelLog>> {
  return useQuery({ queryKey: ['fuel-logs', params ?? {}], queryFn: () => getPage<FuelLog>('/fuel-logs', params), staleTime: 15_000 });
}
export function useFuelEfficiency(vehicleId: string): UseQueryResult<FuelEfficiency> {
  return useQuery({
    queryKey: ['fuel-logs', 'efficiency', vehicleId],
    queryFn: () => getSingle<FuelEfficiency>(`/fuel-logs/vehicle/${vehicleId}/efficiency`),
    enabled: !!vehicleId,
  });
}
export function useCreateFuelLog(): UseMutationResult<FuelLog, unknown, Record<string, unknown>> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => postSingle<FuelLog>('/fuel-logs', body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['fuel-logs'] }); qc.invalidateQueries({ queryKey: ['vehicles'] }); },
  });
}
export function useMaintenance(params?: Record<string, unknown>): UseQueryResult<Page<MaintenanceRecord>> {
  return useQuery({ queryKey: ['maintenance', params ?? {}], queryFn: () => getPage<MaintenanceRecord>('/maintenance', params), staleTime: 15_000 });
}
export function useCreateMaintenance(): UseMutationResult<MaintenanceRecord, unknown, Record<string, unknown>> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => postSingle<MaintenanceRecord>('/maintenance', body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['maintenance'] }); qc.invalidateQueries({ queryKey: ['vehicles'] }); },
  });
}
export function useUpdateMaintenance(id: string): UseMutationResult<MaintenanceRecord, unknown, Record<string, unknown>> {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => patchSingle<MaintenanceRecord>(`/maintenance/${id}`, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['maintenance'] }); qc.invalidateQueries({ queryKey: ['vehicles'] }); },
  });
}

// ─── reports (Sprint C originals) ────────────────────────────────────────────
export function useOperationsSummary(params?: Record<string, unknown>): UseQueryResult<OperationsSummary> {
  return useQuery({
    queryKey: ['reports', 'summary', params ?? {}],
    queryFn: () => getSingle<OperationsSummary>('/reports/operations/summary', params),
    staleTime: 30_000,
  });
}
export function useDailyTimeline(params?: Record<string, unknown>): UseQueryResult<DailyTimeline> {
  return useQuery({
    queryKey: ['reports', 'daily', params ?? {}],
    queryFn: () => getSingle<DailyTimeline>('/reports/operations/daily', params),
    staleTime: 30_000,
  });
}
export function useBranchPerformance(params?: Record<string, unknown>): UseQueryResult<BranchPerformance> {
  return useQuery({
    queryKey: ['reports', 'branches', params ?? {}],
    queryFn: () => getSingle<BranchPerformance>('/reports/branches/performance', params),
    staleTime: 30_000,
  });
}
export function useVehicleRoi(params?: Record<string, unknown>): UseQueryResult<VehicleRoi> {
  return useQuery({
    queryKey: ['reports', 'vehicles', params ?? {}],
    queryFn: () => getSingle<VehicleRoi>('/reports/vehicles/roi', params),
    staleTime: 30_000,
  });
}
export function useFuelSummary(params?: Record<string, unknown>): UseQueryResult<{ total_liters: number; total_cost: number; samples: number; avg_cost_per_liter: number | null }> {
  return useQuery({
    queryKey: ['reports', 'fuel', params ?? {}],
    queryFn: () => getSingle<{ total_liters: number; total_cost: number; samples: number; avg_cost_per_liter: number | null }>('/reports/fuel/summary', params),
    staleTime: 30_000,
  });
}

// ─── Phase 6 expanded reports ────────────────────────────────────────────────
export function useProfitLoss(params?: Record<string, unknown>): UseQueryResult<ProfitLoss> {
  return useQuery({
    queryKey: ['reports', 'pl', params ?? {}],
    queryFn: () => getSingle<ProfitLoss>('/reports/financials/profit-loss', params),
    staleTime: 60_000,
  });
}

export function useCashFlow(params?: Record<string, unknown>): UseQueryResult<CashFlowSeries> {
  return useQuery({
    queryKey: ['reports', 'cashflow', params ?? {}],
    queryFn: () => getSingle<CashFlowSeries>('/reports/financials/cash-flow', params),
    staleTime: 60_000,
  });
}

export function useTopRoutes(params?: Record<string, unknown>): UseQueryResult<{ routes: TopRoute[] }> {
  return useQuery({
    queryKey: ['reports', 'top-routes', params ?? {}],
    queryFn: () => getSingle<{ routes: TopRoute[] }>('/reports/routes/top', params),
    staleTime: 60_000,
  });
}

export function useDriverPerformance(params?: Record<string, unknown>): UseQueryResult<{ drivers: DriverPerformance[] }> {
  return useQuery({
    queryKey: ['reports', 'driver-perf', params ?? {}],
    queryFn: () => getSingle<{ drivers: DriverPerformance[] }>('/reports/drivers/performance', params),
    staleTime: 60_000,
  });
}

export function useVehicleUtilization(params?: Record<string, unknown>): UseQueryResult<{ vehicles: VehicleUtilization[] }> {
  return useQuery({
    queryKey: ['reports', 'vehicle-util', params ?? {}],
    queryFn: () => getSingle<{ vehicles: VehicleUtilization[] }>('/reports/vehicles/utilization', params),
    staleTime: 60_000,
  });
}

export function useIncidentsSummary(params?: Record<string, unknown>): UseQueryResult<IncidentsSummary> {
  return useQuery({
    queryKey: ['reports', 'incidents', params ?? {}],
    queryFn: () => getSingle<IncidentsSummary>('/reports/incidents/summary', params),
    staleTime: 60_000,
  });
}
