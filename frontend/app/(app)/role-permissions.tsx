import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
} from 'react-native';
import { Stack } from 'expo-router';
import {
  Check,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  Save,
  Shield,
  ShieldAlert,
  ShieldCheck,
  X,
} from 'lucide-react-native';
import {
  usePermissionsMeta,
  useRolePermissions,
  useUpdateRolePermission,
  useResetRolePermission,
  useResetAllRolePermissions,
  type RolePermissionItem,
} from '@/lib/queries-p3b';
import { Chip, type SevTone } from '@/components/ui/kit';
import { Spinner } from '@/components/ui/Spinner';
import { useToast } from '@/components/ui/Toast';
import { brand } from '@/lib/theme';

const ROLE_DISPLAY: Record<string, { label: string; tone: SevTone }> = {
  super_admin: { label: 'Super Admin', tone: 'danger' },
  owner: { label: 'Owner', tone: 'danger' },
  general_manager: { label: 'General Manager', tone: 'warn' },
  branch_manager: { label: 'Branch Manager', tone: 'warn' },
  operations_manager: { label: 'Operations Mgr', tone: 'info' },
  fleet_manager: { label: 'Fleet Manager', tone: 'info' },
  chief_accountant: { label: 'Chief Accountant', tone: 'ok' },
  branch_accountant: { label: 'Branch Accountant', tone: 'ok' },
  driver: { label: 'Driver', tone: 'neutral' },
  conductor: { label: 'Conductor', tone: 'neutral' },
};

const RESOURCE_DISPLAY: Record<string, string> = {
  branches: 'Branches',
  users: 'Users',
  vehicles: 'Vehicles',
  drivers: 'Drivers',
  conductors: 'Conductors',
  routes: 'Routes',
  trips: 'Trips',
  fuel: 'Fuel logs',
  maintenance: 'Maintenance',
  expenses: 'Expenses',
  cash_ups: 'Cash-ups',
  reports: 'Reports',
  audit_log: 'Audit log',
  notifications: 'Notifications',
  transfers: 'Transfers',
  incidents: 'Incidents',
  inspections: 'Inspections',
  vehicle_documents: 'Vehicle docs',
  role_permissions: 'Role permissions',
};

const ACTION_DISPLAY: Record<string, string> = {
  read: 'View',
  create: 'Create',
  update: 'Edit',
  delete: 'Delete',
  approve: 'Approve',
  export: 'Export',
};

const SCOPE_DISPLAY: Record<string, { label: string; color: string }> = {
  all: { label: 'All branches', color: '#047857' },
  branch: { label: 'Own branch only', color: '#B45309' },
  own: { label: 'Own records only', color: '#B91C1C' },
};

export default function RolePermissionsScreen() {
  const toast = useToast();
  const metaQ = usePermissionsMeta();
  const permissionsQ = useRolePermissions();
  const updateMut = useUpdateRolePermission();
  const resetOneMut = useResetRolePermission();
  const resetAllMut = useResetAllRolePermissions();

  const [selectedRole, setSelectedRole] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [dirty, setDirty] = useState(false);
  const [localPerms, setLocalPerms] = useState<Record<string, string[]>>({});
  const [localScope, setLocalScope] = useState<string>('all');

  const meta = metaQ.data;
  const allPerms = permissionsQ.data ?? [];

  // When role selection changes, load that role's permissions into local state
  const currentRoleData = useMemo(
    () => allPerms.find((p) => p.role === selectedRole),
    [allPerms, selectedRole],
  );

  useEffect(() => {
    if (currentRoleData) {
      setLocalPerms(JSON.parse(JSON.stringify(currentRoleData.permissions)));
      setLocalScope(currentRoleData.scope || 'all');
      setDirty(false);
    }
  }, [currentRoleData]);

  // Auto-select first role
  useEffect(() => {
    if (!selectedRole && allPerms.length > 0) {
      setSelectedRole(allPerms[0].role);
    }
  }, [allPerms, selectedRole]);

  const toggleExpand = useCallback((resource: string) => {
    setExpanded((prev) => ({ ...prev, [resource]: !prev[resource] }));
  }, []);

  const toggleAction = useCallback(
    (resource: string, action: string) => {
      setLocalPerms((prev) => {
        const next = { ...prev };
        const current = next[resource] ? [...next[resource]] : [];
        const idx = current.indexOf(action);
        if (idx >= 0) {
          current.splice(idx, 1);
        } else {
          current.push(action);
        }
        next[resource] = current;
        return next;
      });
      setDirty(true);
    },
    [],
  );

  const toggleAllForResource = useCallback(
    (resource: string) => {
      if (!meta) return;
      setLocalPerms((prev) => {
        const next = { ...prev };
        const current = next[resource] ?? [];
        if (current.length === meta.actions.length) {
          next[resource] = [];
        } else {
          next[resource] = [...meta.actions];
        }
        return next;
      });
      setDirty(true);
    },
    [meta],
  );

  const changeScope = useCallback((scope: string) => {
    setLocalScope(scope);
    setDirty(true);
  }, []);

  const onSave = async () => {
    if (!selectedRole) return;
    try {
      await updateMut.mutateAsync({
        roleName: selectedRole,
        permissions: localPerms,
        scope: localScope,
      });
      setDirty(false);
      toast.success(`Permissions saved for ${ROLE_DISPLAY[selectedRole]?.label ?? selectedRole}`);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Could not save permissions');
    }
  };

  const onReset = () => {
    if (!selectedRole) return;
    Alert.alert(
      'Reset to defaults?',
      `This will reset ${ROLE_DISPLAY[selectedRole]?.label ?? selectedRole} permissions to the built-in defaults.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Reset',
          style: 'destructive',
          onPress: async () => {
            try {
              await resetOneMut.mutateAsync(selectedRole);
              setDirty(false);
              toast.success('Permissions reset to defaults');
            } catch {
              toast.error('Could not reset permissions');
            }
          },
        },
      ],
    );
  };

  const onResetAll = () => {
    Alert.alert(
      'Reset ALL roles?',
      'This will reset every role to built-in defaults. This cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Reset all',
          style: 'destructive',
          onPress: async () => {
            try {
              await resetAllMut.mutateAsync();
              setDirty(false);
              toast.success('All role permissions reset to defaults');
            } catch {
              toast.error('Could not reset permissions');
            }
          },
        },
      ],
    );
  };

  if (metaQ.isLoading || permissionsQ.isLoading) {
    return (
      <>
        <Stack.Screen options={{ title: 'Role permissions' }} />
        <View style={s.loading}>
          <Spinner label="Loading permissions matrix…" />
        </View>
      </>
    );
  }

  const resources = meta?.resources ?? [];
  const actions = meta?.actions ?? [];

  // Count granted actions for the summary row
  const grantedCount = Object.values(localPerms).reduce((sum, acts) => sum + acts.length, 0);
  const totalPossible = resources.length * actions.length;

  return (
    <>
      <Stack.Screen
        options={{
          title: 'Role permissions',
          headerRight: () => (
            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
              <Pressable onPress={onResetAll} hitSlop={10} style={s.headerBtn}>
                <RefreshCw size={16} color="#FFFFFF" />
              </Pressable>
            </View>
          ),
        }}
      />
      <ScrollView style={s.root} contentContainerStyle={{ padding: 16, paddingBottom: 100 }}>
        {/* ── Role selector ── */}
        <Text style={s.sectionLabel}>SELECT ROLE</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.roleScroll}>
          {allPerms.map((rp) => {
            const display = ROLE_DISPLAY[rp.role];
            return (
              <Chip
                key={rp.role}
                label={display?.label ?? rp.role}
                tone={display?.tone ?? 'neutral'}
                active={selectedRole === rp.role}
                onPress={() => {
                  if (dirty) {
                    Alert.alert('Unsaved changes', 'Save or discard before switching roles.', [
                      { text: 'OK' },
                    ]);
                    return;
                  }
                  setSelectedRole(rp.role);
                  setExpanded({});
                }}
              />
            );
          })}
        </ScrollView>

        {selectedRole ? (
          <>
            {/* ── Summary ── */}
            <View style={s.summaryCard}>
              <View style={s.summaryLeft}>
                <ShieldCheck size={20} color={brand.navy} />
                <Text style={s.summaryTitle}>
                  {ROLE_DISPLAY[selectedRole]?.label ?? selectedRole}
                </Text>
              </View>
              <View style={s.summaryRight}>
                <Text style={s.summaryCount}>
                  {grantedCount}/{totalPossible}
                </Text>
                <Text style={s.summaryCountLabel}>permissions</Text>
              </View>
            </View>

            {/* ── Scope selector ── */}
            <Text style={s.sectionLabel}>DATA SCOPE</Text>
            <View style={s.scopeRow}>
              {(meta?.scopes ?? ['all', 'branch', 'own']).map((scope) => {
                const display = SCOPE_DISPLAY[scope] ?? { label: scope, color: '#475569' };
                const active = localScope === scope;
                return (
                  <Pressable
                    key={scope}
                    style={[
                      s.scopeChip,
                      { borderColor: active ? display.color : '#E2E8F0' },
                      active && { backgroundColor: display.color + '15' },
                    ]}
                    onPress={() => changeScope(scope)}
                  >
                    {active ? (
                      <Check size={14} color={display.color} />
                    ) : (
                      <Shield size={14} color="#94A3B8" />
                    )}
                    <Text
                      style={[
                        s.scopeLabel,
                        { color: active ? display.color : '#64748B' },
                      ]}
                    >
                      {display.label}
                    </Text>
                  </Pressable>
                );
              })}
            </View>

            {/* ── Resource rows ── */}
            <Text style={s.sectionLabel}>PERMISSIONS</Text>
            {resources.map((resource) => {
              const isExpanded = expanded[resource] ?? false;
              const granted = localPerms[resource] ?? [];
              const allGranted = granted.length === actions.length;
              const noneGranted = granted.length === 0;
              return (
                <View key={resource} style={s.resourceCard}>
                  <Pressable
                    style={s.resourceHeader}
                    onPress={() => toggleExpand(resource)}
                  >
                    <View style={{ flex: 1 }}>
                      <Text style={s.resourceName}>
                        {RESOURCE_DISPLAY[resource] ?? resource}
                      </Text>
                      <Text style={s.resourceCount}>
                        {granted.length}/{actions.length} actions
                      </Text>
                    </View>
                    <Pressable
                      onPress={() => toggleAllForResource(resource)}
                      hitSlop={10}
                      style={[
                        s.toggleAllBtn,
                        allGranted
                          ? { backgroundColor: '#D1FAE5' }
                          : noneGranted
                          ? { backgroundColor: '#FEE2E2' }
                          : { backgroundColor: '#FEF3C7' },
                      ]}
                    >
                      {allGranted ? (
                        <Check size={14} color="#047857" />
                      ) : noneGranted ? (
                        <X size={14} color="#B91C1C" />
                      ) : (
                        <ShieldAlert size={14} color="#B45309" />
                      )}
                    </Pressable>
                    {isExpanded ? (
                      <ChevronDown size={18} color="#94A3B8" style={{ marginLeft: 8 }} />
                    ) : (
                      <ChevronRight size={18} color="#94A3B8" style={{ marginLeft: 8 }} />
                    )}
                  </Pressable>

                  {isExpanded ? (
                    <View style={s.actionsGrid}>
                      {actions.map((action) => {
                        const isGranted = granted.includes(action);
                        return (
                          <View key={action} style={s.actionRow}>
                            <Text style={s.actionLabel}>
                              {ACTION_DISPLAY[action] ?? action}
                            </Text>
                            <Switch
                              value={isGranted}
                              onValueChange={() => toggleAction(resource, action)}
                              trackColor={{ false: '#E2E8F0', true: '#86EFAC' }}
                              thumbColor={isGranted ? '#047857' : '#94A3B8'}
                              style={{ transform: [{ scaleX: 0.85 }, { scaleY: 0.85 }] }}
                            />
                          </View>
                        );
                      })}
                    </View>
                  ) : null}
                </View>
              );
            })}

            {/* ── Action buttons ── */}
            <View style={s.actions}>
              <Pressable
                style={[s.saveBtn, !dirty && { opacity: 0.5 }]}
                onPress={onSave}
                disabled={!dirty || updateMut.isPending}
              >
                <Save size={16} color="#FFFFFF" />
                <Text style={s.saveBtnText}>
                  {updateMut.isPending ? 'Saving…' : 'Save changes'}
                </Text>
              </Pressable>
              <Pressable style={s.resetBtn} onPress={onReset}>
                <RefreshCw size={16} color={brand.navy} />
                <Text style={s.resetBtnText}>Reset this role</Text>
              </Pressable>
            </View>

            {/* ── Last updated ── */}
            {currentRoleData?.updated_at ? (
              <Text style={s.lastUpdated}>
                Last updated: {new Date(currentRoleData.updated_at).toLocaleString()}
                {currentRoleData.updated_by ? ` by ${currentRoleData.updated_by}` : ''}
              </Text>
            ) : null}
          </>
        ) : (
          <View style={s.emptyCard}>
            <Shield size={32} color="#94A3B8" />
            <Text style={s.emptyTitle}>Select a role</Text>
            <Text style={s.emptyBody}>
              Choose a role above to view and edit its permissions.
            </Text>
          </View>
        )}
      </ScrollView>
    </>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: '#F4F4F2' },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  headerBtn: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.15)',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 4,
  },
  sectionLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: '#64748B',
    letterSpacing: 0.6,
    textTransform: 'uppercase',
    marginBottom: 8,
    marginTop: 16,
  },
  roleScroll: { marginBottom: 8 },
  summaryCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#F8FAFC',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    padding: 14,
  },
  summaryLeft: { flexDirection: 'row', alignItems: 'center' },
  summaryTitle: { fontSize: 16, fontWeight: '700', color: '#0F172A', marginLeft: 10 },
  summaryRight: { alignItems: 'flex-end' },
  summaryCount: { fontSize: 22, fontWeight: '800', color: brand.navy },
  summaryCountLabel: { fontSize: 11, color: '#64748B' },
  scopeRow: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: 4 },
  scopeChip: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1.5,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginRight: 8,
    marginBottom: 8,
  },
  scopeLabel: { fontSize: 13, fontWeight: '600', marginLeft: 6 },
  resourceCard: {
    backgroundColor: '#F8FAFC',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    marginBottom: 8,
    overflow: 'hidden',
  },
  resourceHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 14,
  },
  resourceName: { fontSize: 15, fontWeight: '700', color: '#0F172A' },
  resourceCount: { fontSize: 12, color: '#64748B', marginTop: 2 },
  toggleAllBtn: {
    width: 32,
    height: 32,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  actionsGrid: {
    paddingHorizontal: 14,
    paddingBottom: 14,
    borderTopWidth: 1,
    borderTopColor: '#E2E8F0',
  },
  actionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#F1F5F9',
  },
  actionLabel: { fontSize: 14, color: '#475569', fontWeight: '500' },
  actions: { marginTop: 20, gap: 10 },
  saveBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: brand.navy,
    borderRadius: 12,
    paddingVertical: 14,
  },
  saveBtnText: { color: '#FFFFFF', fontWeight: '700', fontSize: 15, marginLeft: 8 },
  resetBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: brand.navy,
    borderRadius: 12,
    paddingVertical: 14,
  },
  resetBtnText: { color: brand.navy, fontWeight: '700', fontSize: 15, marginLeft: 8 },
  lastUpdated: { fontSize: 12, color: '#94A3B8', textAlign: 'center', marginTop: 12 },
  emptyCard: {
    backgroundColor: '#F8FAFC',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    padding: 28,
    alignItems: 'center',
    marginTop: 20,
  },
  emptyTitle: { fontSize: 16, fontWeight: '700', color: '#0F172A', marginTop: 10 },
  emptyBody: {
    fontSize: 13,
    color: '#64748B',
    textAlign: 'center',
    marginTop: 6,
    lineHeight: 19,
  },
});
