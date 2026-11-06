/**
 * What each role sees on the home screen.
 *
 * The dashboard used to render the platform administrator's view for
 * everybody: the same four company-wide figures, the same eight
 * counters, the same fleet map. Only the quick actions and the scan
 * button were role-gated, so a driver saw the whole company's revenue
 * and a conductor saw every cash-up in the business.
 *
 * Two things were wrong with that. The *screens* were wrong — a branch
 * manager's dashboard is their branch, not the company, and a driver's
 * dashboard is their next trip. And the *data* was wrong — the
 * endpoints behind those cards were not scoped to crew, so the app was
 * asking for company-wide figures it was never entitled to see.
 *
 * This table is the single place that says which view a role gets.
 * The screen renders it; it does not decide anything itself.
 */
import type { Role } from '@/lib/types';

/** The four big cards across the top. */
export type KpiId =
  | 'revenue'
  | 'trips_today'
  | 'active_fleet'
  | 'cash_variance'
  | 'your_trips'
  | 'on_duty'
  | 'passengers_recorded'
  | 'open_incidents'
  | 'in_maintenance'
  | 'docs_expiring'
  | 'licenses_expiring'
  | 'pending_cashups';

/** The small counters under "At a glance". */
export type GlanceId =
  | 'drivers_on_duty'
  | 'in_maintenance'
  | 'docs_expiring'
  | 'licenses_expiring'
  | 'open_incidents'
  | 'open_transfers'
  | 'pending_cashups'
  | 'total_vehicles';

export interface DashboardView {
  /** The line under the greeting. */
  subtitle: string;
  /** The big cards, in order. */
  kpis: KpiId[];
  /** The small counters. */
  glance: GlanceId[];
  /** The list of the trips that are running right now. */
  liveOperations: boolean;
  /** The map of branches and the fleet. */
  fleetMap: boolean;
  /**
   * Whether this view needs the fleet figures at all.
   *
   * ``GET /vehicles`` is closed to drivers and conductors, so asking
   * for it on their behalf is a request that is always refused.
   */
  needsFleet: boolean;
  /** Whether this view needs the branch list (for the map). */
  needsBranches: boolean;
  /** Whether this view shows the dashboard counters. */
  needsSummary: boolean;
}

const COMPANY_VIEW: DashboardView = {
  subtitle: "Here's what's happening with your fleet.",
  kpis: ['revenue', 'trips_today', 'active_fleet', 'cash_variance'],
  glance: [
    'drivers_on_duty',
    'in_maintenance',
    'docs_expiring',
    'licenses_expiring',
    'open_incidents',
    'open_transfers',
    'pending_cashups',
    'total_vehicles',
  ],
  liveOperations: true,
  fleetMap: true,
  needsFleet: true,
  needsBranches: true,
  needsSummary: true,
};

const OPERATIONS_VIEW: DashboardView = {
  subtitle: "Today's operations across the company.",
  kpis: ['trips_today', 'active_fleet', 'on_duty', 'open_incidents'],
  glance: [
    'drivers_on_duty',
    'in_maintenance',
    'licenses_expiring',
    'open_incidents',
    'open_transfers',
    'total_vehicles',
  ],
  liveOperations: true,
  fleetMap: true,
  needsFleet: true,
  needsBranches: true,
  needsSummary: true,
};

const FLEET_VIEW: DashboardView = {
  subtitle: 'Your vehicles, their servicing and their paperwork.',
  kpis: ['active_fleet', 'in_maintenance', 'docs_expiring', 'licenses_expiring'],
  glance: [
    'total_vehicles',
    'in_maintenance',
    'docs_expiring',
    'licenses_expiring',
    'open_transfers',
  ],
  liveOperations: false,
  fleetMap: true,
  needsFleet: true,
  needsBranches: true,
  needsSummary: true,
};

const BRANCH_VIEW: DashboardView = {
  subtitle: 'Your branch — today.',
  kpis: ['revenue', 'trips_today', 'active_fleet', 'cash_variance'],
  glance: [
    'drivers_on_duty',
    'in_maintenance',
    'docs_expiring',
    'licenses_expiring',
    'open_incidents',
    'pending_cashups',
  ],
  liveOperations: true,
  fleetMap: true,
  needsFleet: true,
  needsBranches: true,
  needsSummary: true,
};

const CHIEF_ACCOUNTANT_VIEW: DashboardView = {
  subtitle: "The company's money, and what is waiting on you.",
  kpis: ['revenue', 'cash_variance', 'pending_cashups', 'trips_today'],
  glance: ['pending_cashups'],
  liveOperations: false,
  fleetMap: false,
  needsFleet: false,
  needsBranches: false,
  needsSummary: true,
};

const BRANCH_ACCOUNTANT_VIEW: DashboardView = {
  subtitle: "Your branch's financial position.",
  kpis: ['revenue', 'cash_variance', 'pending_cashups'],
  glance: ['pending_cashups'],
  liveOperations: false,
  fleetMap: false,
  needsFleet: false,
  needsBranches: false,
  needsSummary: true,
};

const DRIVER_VIEW: DashboardView = {
  subtitle: 'Your trips, and the checks to run before you leave.',
  kpis: ['your_trips', 'on_duty', 'trips_today'],
  glance: [],
  liveOperations: true,
  fleetMap: false,
  needsFleet: false,
  needsBranches: false,
  needsSummary: false,
};

const CONDUCTOR_VIEW: DashboardView = {
  subtitle: 'Your trips, your manifest and your cash-up.',
  kpis: ['your_trips', 'on_duty', 'passengers_recorded'],
  glance: [],
  liveOperations: true,
  fleetMap: false,
  needsFleet: false,
  needsBranches: false,
  needsSummary: false,
};

export const DASHBOARD_VIEWS: Record<Role, DashboardView> = {
  super_admin: COMPANY_VIEW,
  owner: COMPANY_VIEW,
  general_manager: COMPANY_VIEW,
  operations_manager: OPERATIONS_VIEW,
  fleet_manager: FLEET_VIEW,
  branch_manager: BRANCH_VIEW,
  chief_accountant: CHIEF_ACCOUNTANT_VIEW,
  branch_accountant: BRANCH_ACCOUNTANT_VIEW,
  driver: DRIVER_VIEW,
  conductor: CONDUCTOR_VIEW,
};

/**
 * The roles whose dashboard may ask for money figures.
 *
 * The reports summary endpoint is closed to drivers and conductors, so
 * the app must not call it for them — a 403 on every dashboard load is
 * noise, and a card showing zero because the request failed is worse
 * than no card.
 */
export const MONEY_VISIBLE_ROLES: Role[] = [
  'super_admin',
  'owner',
  'general_manager',
  'operations_manager',
  'fleet_manager',
  'branch_manager',
  'chief_accountant',
  'branch_accountant',
];

export function dashboardViewFor(role: Role | null | undefined): DashboardView {
  if (!role) return COMPANY_VIEW;
  return DASHBOARD_VIEWS[role] ?? COMPANY_VIEW;
}

export function roleSeesMoney(role: Role | null | undefined): boolean {
  if (!role) return false;
  return MONEY_VISIBLE_ROLES.includes(role);
}
