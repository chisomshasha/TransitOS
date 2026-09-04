/**
 * Domain types — mirror of /workspace/transitos/specs/data-model.md
 * and api-contract.md. Kept in one file for ease of import; the
 * real implementation would split these per-entity.
 */

export const ROLES = [
  'super_admin',
  'owner',
  'general_manager',
  'branch_manager',
  'operations_manager',
  'fleet_manager',
  'chief_accountant',
  'branch_accountant',
  'driver',
  'conductor',
] as const;
export type Role = (typeof ROLES)[number];

export const ROLE_LABELS: Record<Role, string> = {
  super_admin: 'Super Admin',
  owner: 'Owner',
  general_manager: 'General Manager',
  branch_manager: 'Branch Manager',
  operations_manager: 'Operations Manager',
  fleet_manager: 'Fleet Manager',
  chief_accountant: 'Chief Accountant',
  branch_accountant: 'Branch Accountant',
  driver: 'Driver',
  conductor: 'Conductor',
};

export const BRANCH_SCOPED_ROLES: Role[] = [
  'branch_manager',
  'branch_accountant',
  'driver',
  'conductor',
];

export const BRANCH_STATUSES = ['active', 'suspended'] as const;
export type BranchStatus = (typeof BRANCH_STATUSES)[number];

export const USER_STATUSES = ['active', 'suspended', 'pending'] as const;
export type UserStatus = (typeof USER_STATUSES)[number];

export const VEHICLE_TYPES = ['bus', 'minibus', 'truck'] as const;
export type VehicleType = (typeof VEHICLE_TYPES)[number];

export const VEHICLE_STATUSES = [
  'available',
  'on_trip',
  'maintenance',
  'grounded',
] as const;
export type VehicleStatus = (typeof VEHICLE_STATUSES)[number];

export const ROUTE_TYPES = ['intrastate', 'interstate'] as const;
export type RouteType = (typeof ROUTE_TYPES)[number];

export const STAFF_STATUSES = ['active', 'suspended', 'on_leave'] as const;
export type StaffStatus = (typeof STAFF_STATUSES)[number];

// ---- Entity shapes (response variants) ----

export interface GPS {
  lat: number;
  lng: number;
}

export interface BankAccount {
  bank: string;
  number: string;
  name: string;
}

export interface Branch {
  id: string;
  name: string;
  code: string;
  city: string;
  state: string;
  address: string;
  contact_phone?: string | null;
  contact_email?: string | null;
  gps?: GPS | null;
  bank_account?: BankAccount | null;
  status: BranchStatus;
  manager_id?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  phone?: string | null;
  role: Role;
  branch_id?: string | null;
  status: UserStatus;
  hire_date?: string | null;
  photo_url?: string | null;
  is_active: boolean;
  last_login_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Vehicle {
  id: string;
  reg_number: string;
  type: VehicleType;
  capacity_seats: number;
  capacity_kg: number;
  branch_id: string;
  home_terminal_id?: string | null;
  status: VehicleStatus;
  current_odometer_km: number;
  current_fuel_level: number;
  documents: unknown[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Driver {
  id: string;
  user_id: string;
  branch_id: string;
  license_no: string;
  license_expiry: string;
  years_experience: number;
  status: StaffStatus;
  // denormalized from linked User
  full_name: string;
  email: string;
  phone?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Conductor {
  id: string;
  user_id: string;
  branch_id: string;
  badge_no: string;
  status: StaffStatus;
  full_name: string;
  email: string;
  phone?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RouteStop {
  name: string;
  lat: number;
  lng: number;
  eta_minutes: number;
}

export interface Route {
  id: string;
  name: string;
  branch_id: string;
  type: RouteType;
  origin_branch_id: string;
  destination_branch_id: string;
  origin_city: string;
  destination_city: string;
  distance_km: number;
  base_fare_passenger: number;
  base_fare_cargo_per_kg: number;
  estimated_duration_hours: number;
  intermediate_stops: RouteStop[];
  required_permits: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ---- API list/pagination ----

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  totalPages: number;
  hasMore: boolean;
}

export interface SingleResponse<T> {
  data: T;
}

export interface ApiError {
  detail: string;
  type:
    | 'validation_error'
    | 'unauthorized'
    | 'forbidden'
    | 'not_found'
    | 'conflict'
    | 'rate_limited'
    | 'internal_error';
}

// ---- Sprint B: Trip lifecycle ----

export const TRIP_STATUSES = [
  'planned',
  'boarding',
  'departed',
  'arrived',
  'closed',
  'cashed_up',
  'cancelled',
] as const;
export type TripStatus = (typeof TRIP_STATUSES)[number];

export const TRIP_STATUS_LABELS: Record<TripStatus, string> = {
  planned: 'Planned',
  boarding: 'Boarding',
  departed: 'Departed',
  arrived: 'Arrived',
  closed: 'Closed',
  cashed_up: 'Cashed up',
  cancelled: 'Cancelled',
};

export const TRIP_STATUS_TONE: Record<TripStatus, 'neutral' | 'info' | 'warning' | 'success' | 'danger' | 'primary'> = {
  planned: 'neutral',
  boarding: 'info',
  departed: 'primary',
  arrived: 'info',
  closed: 'warning',
  cashed_up: 'success',
  cancelled: 'danger',
};

export interface Trip {
  id: string;
  route_id: string;
  vehicle_id: string;
  driver_id: string;
  conductor_id: string;
  branch_id: string;
  scheduled_departure: string;
  scheduled_arrival: string;
  actual_departure?: string | null;
  actual_arrival?: string | null;
  origin_terminal?: string | null;
  destination_terminal?: string | null;
  notes?: string | null;
  status: TripStatus;
  passenger_count: number;
  cargo_weight_kg: number;
  total_revenue: number;
  total_expenses: number;
  cash_up_id?: string | null;
  cancelled_reason?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export const MANIFEST_TYPES = ['passenger', 'cargo'] as const;
export type ManifestType = (typeof MANIFEST_TYPES)[number];

export const MANIFEST_PAYMENT_STATUSES = ['paid', 'on_board', 'cancelled'] as const;
export type ManifestPaymentStatus = (typeof MANIFEST_PAYMENT_STATUSES)[number];

export interface ManifestEntry {
  id: string;
  trip_id: string;
  branch_id?: string | null;
  type: ManifestType;
  passenger_name?: string | null;
  passenger_phone?: string | null;
  passenger_id_number?: string | null;
  seat_number?: string | null;
  cargo_description?: string | null;
  cargo_weight_kg?: number | null;
  cargo_sender_name?: string | null;
  cargo_receiver_name?: string | null;
  cargo_receiver_phone?: string | null;
  fare: number;
  payment_status: ManifestPaymentStatus;
  payment_method?: string | null;
  boarded: boolean;
  created_at: string;
  updated_at: string;
}

export const CASHUP_STATUSES = ['draft', 'submitted', 'approved', 'rejected'] as const;
export type CashUpStatus = (typeof CASHUP_STATUSES)[number];

export interface PaymentMethodBreakdown {
  method: string;
  amount: number;
  reference?: string | null;
}

export interface CashUp {
  id: string;
  trip_id: string;
  conductor_id: string;
  branch_id: string;
  breakdown: PaymentMethodBreakdown[];
  declared_total: number;
  expected_total: number;
  variance: number;
  status: CashUpStatus;
  notes?: string | null;
  approved_by_id?: string | null;
  approved_at?: string | null;
  rejection_reason?: string | null;
  created_at: string;
  updated_at: string;
}

// ---- Sprint B: Expenses ----

export const EXPENSE_CATEGORIES = [
  'fuel',
  'toll',
  'maintenance',
  'permit',
  'meal',
  'accommodation',
  'other',
] as const;
export type ExpenseCategory = (typeof EXPENSE_CATEGORIES)[number];

export const EXPENSE_CATEGORY_LABELS: Record<ExpenseCategory, string> = {
  fuel: 'Fuel',
  toll: 'Toll',
  maintenance: 'Maintenance',
  permit: 'Permit',
  meal: 'Meal',
  accommodation: 'Accommodation',
  other: 'Other',
};

export const EXPENSE_SCOPES = ['on_trip', 'standalone'] as const;
export type ExpenseScope = (typeof EXPENSE_SCOPES)[number];

export interface Expense {
  id: string;
  vehicle_id: string;
  branch_id: string;
  scope: ExpenseScope;
  trip_id?: string | null;
  category: ExpenseCategory;
  amount: number;
  occurred_at: string;
  vendor_name?: string | null;
  receipt_url?: string | null;
  odometer_km?: number | null;
  notes?: string | null;
  recorded_by_id?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ---- Sprint C: Fuel + Maintenance ----

export interface FuelLog {
  id: string;
  vehicle_id: string;
  branch_id: string;
  occurred_at: string;
  liters: number;
  cost_total: number;
  cost_per_liter: number;
  odometer_km: number;
  station_name?: string | null;
  station_location?: string | null;
  receipt_url?: string | null;
  notes?: string | null;
  recorded_by_id?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface FuelEfficiency {
  km_per_liter: number | null;
  total_liters: number;
  total_cost: number;
  samples: number;
}

export const MAINTENANCE_TYPES = ['routine', 'repair', 'inspection', 'recall'] as const;
export type MaintenanceType = (typeof MAINTENANCE_TYPES)[number];

export const MAINTENANCE_STATUSES = ['scheduled', 'in_progress', 'completed', 'cancelled'] as const;
export type MaintenanceStatus = (typeof MAINTENANCE_STATUSES)[number];

export interface MaintenanceRecord {
  id: string;
  vehicle_id: string;
  branch_id: string;
  type: MaintenanceType;
  status: MaintenanceStatus;
  title: string;
  description?: string | null;
  scheduled_for?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  odometer_km?: number | null;
  vendor_name?: string | null;
  cost_parts: number;
  cost_labor: number;
  cost_total: number;
  next_due_km?: number | null;
  next_due_date?: string | null;
  notes?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ---- Sprint C: Reports ----

export interface OperationsSummary {
  window: { from: string; to: string };
  totals: {
    trips: number;
    revenue: number;
    expenses: number;
    net: number;
    variance: number;
    passengers: number;
    cargo_kg: number;
  };
  by_status: Array<{
    status: string;
    count: number;
    revenue: number;
    expenses: number;
    passengers: number;
  }>;
}

export interface DailyTimeline {
  bucket: 'day' | 'week';
  series: Array<{
    label: string;
    revenue: number;
    expenses: number;
    net: number;
    trips: number;
  }>;
}

export interface BranchPerformance {
  branches: Array<{
    branch_id: string;
    branch_name: string | null;
    trips: number;
    revenue: number;
    expenses: number;
    net: number;
    passengers: number;
  }>;
}

export interface VehicleRoi {
  vehicles: Array<{
    vehicle_id: string;
    reg_number: string | null;
    type: string | null;
    trips: number;
    revenue: number;
    expenses: number;
    net: number;
    passengers: number;
    cargo_kg: number;
  }>;
}

export const VEHICLE_STATUS_LABELS: Record<VehicleStatus, string> = {
  available: 'Available',
  on_trip: 'On trip',
  maintenance: 'Maintenance',
  grounded: 'Grounded',
};
