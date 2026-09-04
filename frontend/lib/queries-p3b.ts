import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, getSingle } from '@/lib/api';

export interface RolePermissionItem {
  id: string;
  role: string;
  permissions: Record<string, string[]>;
  scope: string;
  updated_at?: string | null;
  updated_by?: string | null;
}

export interface PermissionsMeta {
  resources: string[];
  actions: string[];
  scopes: string[];
  roles: string[];
}

export function useRolePermissions() {
  return useQuery({
    queryKey: ['role-permissions'],
    queryFn: async () => {
      const resp = await api.get<RolePermissionItem[]>('/role-permissions');
      return resp.data;
    },
  });
}

export function usePermissionsMeta() {
  return useQuery({
    queryKey: ['role-permissions', 'meta'],
    queryFn: () => getSingle<PermissionsMeta>('/role-permissions/meta'),
    staleTime: 300_000,
  });
}

export function useRolePermission(roleName: string) {
  return useQuery({
    queryKey: ['role-permissions', roleName],
    queryFn: () => getSingle<RolePermissionItem>(`/role-permissions/${roleName}`),
    enabled: !!roleName,
  });
}

export function useUpdateRolePermission() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      roleName,
      permissions,
      scope,
    }: {
      roleName: string;
      permissions: Record<string, string[]>;
      scope?: string;
    }) => {
      const resp = await api.put<RolePermissionItem>(
        `/role-permissions/${roleName}`,
        { permissions, ...(scope ? { scope } : {}) },
      );
      return resp.data;
    },
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ['role-permissions'] });
      qc.invalidateQueries({ queryKey: ['role-permissions', vars.roleName] });
    },
  });
}

export function useResetRolePermission() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (roleName: string) => {
      const resp = await api.post<RolePermissionItem>(
        `/role-permissions/${roleName}/reset`,
      );
      return resp.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['role-permissions'] });
    },
  });
}

export function useResetAllRolePermissions() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await api.post('/role-permissions/reset-all');
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['role-permissions'] });
    },
  });
}
