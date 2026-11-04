import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getPage, postJson, patchJson, deleteJson } from '@/lib/api';

export interface VehicleDocument {
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

export interface VehicleDocumentCreate {
  doc_type: string;
  issuer?: string | null;
  ref_number: string;
  issued_at?: string | null;
  expires_at: string;
  alert_days: number;
  file_url?: string | null;
}

export function useVehicleDocuments(vehicleId: string) {
  return useQuery({
    queryKey: ['vehicles', vehicleId, 'documents'],
    queryFn: () => getPage<VehicleDocument>(`/vehicles/${vehicleId}/documents`, {}),
    enabled: !!vehicleId,
  });
}

export function useCreateVehicleDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ vehicleId, data }: { vehicleId: string; data: VehicleDocumentCreate }) =>
      postJson(`/vehicles/${vehicleId}/documents`, data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ['vehicles', vars.vehicleId, 'documents'] });
      qc.invalidateQueries({ queryKey: ['vehicle-documents', 'expiring'] });
      qc.invalidateQueries({ queryKey: ['notifications'] });
    },
  });
}

export function useUpdateVehicleDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ vehicleId, docId, data }: { vehicleId: string; docId: string; data: Partial<VehicleDocumentCreate> }) =>
      patchJson(`/vehicles/${vehicleId}/documents/${docId}`, data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ['vehicles', vars.vehicleId, 'documents'] });
      qc.invalidateQueries({ queryKey: ['vehicle-documents', 'expiring'] });
      qc.invalidateQueries({ queryKey: ['notifications'] });
    },
  });
}

export function useDeleteVehicleDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ vehicleId, docId }: { vehicleId: string; docId: string }) =>
      deleteJson(`/vehicles/${vehicleId}/documents/${docId}`, {}),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ['vehicles', vars.vehicleId, 'documents'] });
      qc.invalidateQueries({ queryKey: ['vehicle-documents', 'expiring'] });
      qc.invalidateQueries({ queryKey: ['notifications'] });
    },
  });
}
