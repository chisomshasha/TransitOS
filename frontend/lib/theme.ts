/**
 * TransitOS design tokens — navy + yellow system (approved mockups).
 */
export const brand = {
  navy: '#0B3D91',
  navyDeep: '#072A66',
  navySoft: '#1A4FAD',
  yellow: '#FFCC00',
  yellowDark: '#E5B800',
  yellowSoft: '#FFF6CC',
  bg: '#F8F7F4',
  card: '#FFFFFF',
  slate: '#0F172A',
  muted: '#64748B',
  border: '#E2E8F0',
  fieldBg: '#F1F5F9',
  success: '#047857',
  successBg: '#ECFDF5',
  warning: '#B45309',
  warningBg: '#FFFBEB',
  danger: '#B91C1C',
  dangerBg: '#FEF2F2',
  info: '#1D4ED8',
  infoBg: '#EFF6FF',
} as const;

export const tripStatusColor: Record<string, { bg: string; text: string; border: string }> = {
  planned: { bg: '#EFF6FF', text: '#1D4ED8', border: '#BFDBFE' },
  boarding: { bg: '#FFFBEB', text: '#B45309', border: '#FDE68A' },
  departed: { bg: '#ECFDF5', text: '#047857', border: '#A7F3D0' },
  arrived: { bg: '#ECFEFF', text: '#0E7490', border: '#A5F3FC' },
  closed: { bg: '#F1F5F9', text: '#475569', border: '#E2E8F0' },
  cashed_up: { bg: '#EEF2FF', text: '#0B3D91', border: '#C7D2FE' },
  cancelled: { bg: '#FEF2F2', text: '#B91C1C', border: '#FECACA' },
};

export const vehicleStatusColor: Record<string, { bg: string; text: string }> = {
  available: { bg: '#ECFDF5', text: '#047857' },
  on_trip: { bg: '#EFF6FF', text: '#1D4ED8' },
  maintenance: { bg: '#FFFBEB', text: '#B45309' },
  offline: { bg: '#F1F5F9', text: '#64748B' },
  retired: { bg: '#FEF2F2', text: '#B91C1C' },
};
