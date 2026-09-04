import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getPage, getSingle, postNoContent } from '@/lib/api';

export interface NotificationItem {
  id: string;
  type: string;
  severity: 'info' | 'warn' | 'danger' | 'success';
  title: string;
  body: string;
  branch_id?: string | null;
  entity_type?: string | null;
  entity_id?: string | null;
  source?: string;
  read_by: string[];
  created_at: string;
}

export interface VehicleDocumentItem {
  id: string;
  vehicle_id: string;
  doc_type: string;
  issuer?: string | null;
  ref_number: string;
  issued_at?: string | null;
  expires_at: string;
  alert_days: number;
  file_url?: string | null;
}

export function useNotifications(params?: { page?: number; page_size?: number; type?: string; unread?: boolean }) {
  return useQuery({
    queryKey: ['notifications', params ?? {}],
    queryFn: () => getPage<NotificationItem>('/notifications', params as Record<string, unknown>),
  });
}

export function useUnreadCount() {
  return useQuery({
    queryKey: ['notifications', 'unread-count'],
    queryFn: async () => (await getSingle<{ count: number }>('/notifications/unread-count')).count,
  });
}

export function useMarkAllRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => postNoContent('/notifications/mark-all-read', {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  });
}

export function useMarkRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => postNoContent(`/notifications/${id}/mark-read`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  });
}

export function useScanAlerts() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => postNoContent('/alerts/scan', {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  });
}

export function useExpiringDocs(days = 30) {
  return useQuery({
    queryKey: ['vehicle-documents', 'expiring', days],
    queryFn: () => getPage<VehicleDocumentItem>('/vehicle-documents/expiring', { days } as Record<string, unknown>),
  });
}
