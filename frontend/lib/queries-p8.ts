/**
 * Phase 8 query hooks — QR lookup + dashboard summary.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getSingle, postSingle } from '@/lib/api';

export interface QrGenerateResponse {
  token: string;
  entity_type: string;
  entity_id: string;
  deeplink: string;
}

export interface QrLookupResponse {
  entity_type: string;
  entity_id: string;
  deeplink: string;
}

export interface DashboardSummary {
  vehicles_maintenance: number;
  drivers_on_duty: number;
  documents_expiring_30d: number;
  licenses_expiring_30d: number;
  open_incidents: number;
  open_transfers: number;
  pending_cash_ups: number;
}

/**
 * Generate a signed QR token for an entity. The backend validates
 * that the entity exists and is active before issuing the token.
 */
export function useQrGenerate(entityType: string, entityId: string) {
  return useQuery({
    queryKey: ['qr', 'generate', entityType, entityId],
    queryFn: () =>
      getSingle<QrGenerateResponse>(`/qr/generate/${entityType}/${entityId}`),
    enabled: !!entityId,
    staleTime: 5 * 60_000, // tokens are valid 30 days; 5min cache is plenty
  });
}

/**
 * Look up a scanned QR token. Returns the entity type + id so the
 * scanner screen can navigate to the correct detail view.
 */
export function useQrLookup() {
  return useMutation({
    mutationFn: (token: string) =>
      getSingle<QrLookupResponse>('/qr/lookup', { token }),
  });
}

/**
 * Aggregated dashboard counters — single call replaces 7 separate queries.
 * Refetches every 60 seconds when the dashboard is mounted.
 */
export function useDashboardSummary() {
  return useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: () => getSingle<DashboardSummary>('/dashboard/summary'),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
}
