/**
 * Money-loop rules shared by the screens.
 *
 * Everything in this file mirrors a rule the backend already enforces:
 *
 * | Front end                        | Backend                                  |
 * |----------------------------------|------------------------------------------|
 * | `TRIP_TRANSITIONS`                | `app/models/trip.py` → `TRIP_TRANSITIONS` |
 * | `TRIP_MUTATE_ROLES`               | `app/routers/trips.py` → `TRIPS_MUTATE`  |
 * | `TRIP_MANIFEST_MUTATE_ROLES`      | `app/routers/trips.py` → `TRIPS_MANIFEST_MUTATE` |
 * | `CASH_UP_MUTATE_ROLES`            | `app/routers/cash_ups.py` → `CASHUP_MUTATE` |
 * | `CASH_UP_APPROVE_ROLES`           | `app/routers/cash_ups.py` → `CASHUP_APPROVE` |
 *
 * Keeping the copy here (rather than sprinkling role arrays through the
 * screens) means one edit fixes every screen, and the guard in
 * `tools/contract/check.py` can prove the two lists still agree.
 */
import type { Role, TripStatus } from '@/lib/types';

/**
 * The trip state machine, exactly as the backend defines it.
 *
 * `closed → cashed_up` is deliberately *not* offered as a manual button:
 * the backend sets that status itself when a cash-up is approved, so a
 * manual "mark cashed up" would let a trip skip the money loop
 * entirely. It stays in the map because the backend allows it and the
 * map is a mirror of the server rule.
 */
export const TRIP_TRANSITIONS: Record<TripStatus, TripStatus[]> = {
  planned: ['boarding', 'cancelled'],
  boarding: ['departed', 'cancelled'],
  departed: ['arrived'],
  arrived: ['closed'],
  closed: ['cashed_up'],
  cashed_up: [],
  cancelled: [],
};

/** Statuses a user may advance a trip to from the trip screen. */
export const MANUAL_TRIP_TRANSITIONS: Record<TripStatus, TripStatus[]> = {
  planned: ['boarding', 'cancelled'],
  boarding: ['departed', 'cancelled'],
  departed: ['arrived'],
  arrived: ['closed'],
  closed: [],
  cashed_up: [],
  cancelled: [],
};

export interface TripStatusAction {
  status: TripStatus;
  label: string;
  hint: string;
  variant: 'primary' | 'outline' | 'danger';
}

/** The button copy for each manual transition. */
export const TRIP_STATUS_ACTIONS: Record<TripStatus, TripStatusAction> = {
  boarding: {
    status: 'boarding',
    label: 'Start boarding',
    hint: 'The vehicle is at the terminal and passengers are getting on.',
    variant: 'primary',
  },
  departed: {
    status: 'departed',
    label: 'Confirm departure',
    hint: 'The vehicle has left the terminal. The actual departure time is stamped now.',
    variant: 'primary',
  },
  arrived: {
    status: 'arrived',
    label: 'Confirm arrival',
    hint: 'The vehicle has reached its destination. The actual arrival time is stamped now.',
    variant: 'primary',
  },
  closed: {
    status: 'closed',
    label: 'Close trip',
    hint: 'The trip is complete. Cash-up can now be recorded.',
    variant: 'primary',
  },
  cancelled: {
    status: 'cancelled',
    label: 'Cancel trip',
    hint: 'A reason is required and is recorded on the trip and in the audit log.',
    variant: 'danger',
  },
  planned: { status: 'planned', label: 'Planned', hint: '', variant: 'outline' },
  cashed_up: { status: 'cashed_up', label: 'Cashed up', hint: '', variant: 'outline' },
};

/** The status a trip must be in before a cash-up can be created. */
export const CASH_UP_REQUIRES_TRIP_STATUS: TripStatus = 'closed';

/** Backend `TRIPS_MUTATE`. */
export const TRIP_MUTATE_ROLES: Role[] = [
  'super_admin',
  'owner',
  'general_manager',
  'branch_manager',
  'operations_manager',
];

/** Backend `TRIPS_MANIFEST_MUTATE`. */
export const TRIP_MANIFEST_MUTATE_ROLES: Role[] = [
  'super_admin',
  'owner',
  'general_manager',
  'branch_manager',
  'operations_manager',
  'conductor',
];

/** Backend `CASHUP_MUTATE`. */
export const CASH_UP_MUTATE_ROLES: Role[] = [
  'super_admin',
  'owner',
  'general_manager',
  'chief_accountant',
  'branch_accountant',
  'branch_manager',
  'conductor',
];

/** Backend `CASHUP_APPROVE`. */
export const CASH_UP_APPROVE_ROLES: Role[] = [
  'super_admin',
  'owner',
  'general_manager',
  'chief_accountant',
  'branch_accountant',
];

/** The next manual statuses available from a given status. */
export function tripStatusActions(from: TripStatus): TripStatus[] {
  return MANUAL_TRIP_TRANSITIONS[from] ?? [];
}
