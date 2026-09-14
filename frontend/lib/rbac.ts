/**
 * RBAC helpers + TABS_BY_ROLE + SCREEN_ACCESS.
 */
import type { Role } from '@/lib/types';

export type TabId = 'home' | 'trips' | 'vehicles' | 'more' | 'reports' | 'profile';

const ALL_TAB_IDS: TabId[] = ['home', 'trips', 'vehicles', 'more', 'reports', 'profile'];
const ALL_ROLES: Role[] = [
  'super_admin', 'owner', 'general_manager', 'branch_manager',
  'operations_manager', 'fleet_manager', 'chief_accountant',
  'branch_accountant', 'driver', 'conductor',
];

export const TABS_BY_ROLE: Record<Role, TabId[]> = {
  super_admin: ALL_TAB_IDS,
  owner: ALL_TAB_IDS,
  general_manager: ALL_TAB_IDS,
  branch_manager: ALL_TAB_IDS,
  operations_manager: ALL_TAB_IDS,
  fleet_manager: ALL_TAB_IDS,
  chief_accountant: ['home', 'more', 'reports', 'profile'],
  branch_accountant: ['home', 'trips', 'more', 'reports', 'profile'],
  driver: ['home', 'trips', 'more', 'profile'],
  conductor: ['home', 'trips', 'more', 'profile'],
};

export const SCREEN_ACCESS: { prefix: string; roles: Role[] }[] = [
  { prefix: '/branches', roles: ['super_admin', 'owner', 'general_manager', 'branch_manager', 'operations_manager'] },
  { prefix: '/users', roles: ['super_admin', 'owner', 'general_manager', 'branch_manager', 'branch_accountant'] },
  { prefix: '/vehicles', roles: ['super_admin', 'owner', 'general_manager', 'branch_manager', 'operations_manager', 'fleet_manager'] },
  { prefix: '/drivers', roles: ['super_admin', 'owner', 'general_manager', 'branch_manager', 'operations_manager', 'fleet_manager'] },
  { prefix: '/conductors', roles: ['super_admin', 'owner', 'general_manager', 'branch_manager', 'operations_manager', 'fleet_manager'] },
  { prefix: '/routes', roles: ['super_admin', 'owner', 'general_manager', 'branch_manager', 'operations_manager', 'fleet_manager'] },
  { prefix: '/trips', roles: ['super_admin', 'owner', 'general_manager', 'branch_manager', 'operations_manager', 'fleet_manager', 'branch_accountant', 'driver', 'conductor'] },
  { prefix: '/fuel', roles: ['super_admin', 'owner', 'general_manager', 'branch_manager', 'fleet_manager'] },
  { prefix: '/maintenance', roles: ['super_admin', 'owner', 'general_manager', 'branch_manager', 'fleet_manager'] },
  { prefix: '/expenses', roles: ['super_admin', 'owner', 'general_manager', 'branch_manager', 'chief_accountant', 'branch_accountant'] },
  { prefix: '/cash-ups', roles: ['super_admin', 'owner', 'general_manager', 'branch_manager', 'chief_accountant', 'branch_accountant', 'conductor'] },
  { prefix: '/reports', roles: ['super_admin', 'owner', 'general_manager', 'branch_manager', 'operations_manager', 'fleet_manager', 'chief_accountant', 'branch_accountant'] },
  { prefix: '/audit-log', roles: ['super_admin', 'owner', 'general_manager'] },
  { prefix: '/role-permissions', roles: ['super_admin', 'owner', 'general_manager'] },
  { prefix: '/map', roles: ['super_admin', 'owner', 'general_manager', 'operations_manager', 'branch_manager', 'fleet_manager'] },
  { prefix: '/transfers', roles: ['super_admin', 'owner', 'general_manager', 'operations_manager', 'branch_manager', 'fleet_manager'] },
  { prefix: '/incidents', roles: ['super_admin', 'owner', 'general_manager', 'operations_manager', 'branch_manager', 'fleet_manager'] },
  { prefix: '/pre-trip-checklist', roles: ['super_admin', 'owner', 'general_manager', 'operations_manager', 'branch_manager', 'fleet_manager', 'driver'] },
  // Phase 8 — QR scanner: available to all operational roles + crew
  {
    prefix: '/scan',
    roles: [
      'super_admin', 'owner', 'general_manager', 'branch_manager',
      'operations_manager', 'fleet_manager', 'driver', 'conductor',
    ],
  },
];

export function canAccess(userRole: Role | null | undefined, required: Role[]): boolean {
  if (!userRole) return false;
  return required.includes(userRole);
}

export function tabsForRole(role: Role | null | undefined): TabId[] {
  if (!role) return ['home', 'profile'];
  return TABS_BY_ROLE[role] ?? ['home', 'profile'];
}

export function canAccessScreen(role: Role | null | undefined, pathname: string): boolean {
  if (!role) return false;
  let path = pathname || '/';
  if (!path.startsWith('/')) path = '/' + path;
  if (path.length > 1 && path.endsWith('/')) path = path.slice(0, -1);

  let matched: { prefix: string; roles: Role[] } | null = null;
  for (const entry of SCREEN_ACCESS) {
    if (path === entry.prefix || path.startsWith(entry.prefix + '/')) {
      if (!matched || entry.prefix.length > matched.prefix.length) {
        matched = entry;
      }
    }
  }
  if (!matched) return true;
  return matched.roles.includes(role);
}

export function defaultHomeForRole(role: Role | null | undefined): string {
  const tabs = tabsForRole(role);
  if (tabs.includes('home')) return '/';
  if (tabs.includes('trips')) return '/trips';
  if (tabs.includes('profile')) return '/profile';
  return '/';
}

// ─── Role-assignment hierarchy ──────────────────────────────────────────────
// Mirrors the backend's app/core/roles.py ROLE_RANK / can_assign_role: an
// actor may only grant a role at their own seniority tier or below. This is
// used to populate role pickers with sensible choices client-side; the
// backend enforces the same rule regardless, so this is UX only, not the
// security boundary.
const ROLE_RANK: Record<Role, number> = {
  super_admin: 0,
  owner: 1,
  general_manager: 2,
  operations_manager: 3,
  fleet_manager: 3,
  chief_accountant: 3,
  branch_manager: 4,
  branch_accountant: 5,
  driver: 6,
  conductor: 6,
};

export function assignableRoles(actorRole: Role | null | undefined): Role[] {
  if (!actorRole) return [];
  if (actorRole === 'branch_manager') {
    // Mirrors the backend's extra, narrower allow-list for Branch Manager.
    return ['branch_accountant', 'driver', 'conductor'];
  }
  const actorRank = ROLE_RANK[actorRole];
  return ALL_ROLES.filter((r) => ROLE_RANK[r] >= actorRank);
}

export { ALL_ROLES };
