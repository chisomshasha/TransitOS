/**
 * Design tokens as a typed object — mirror of design-tokens.md §1.
 * Screens rarely need this; it exists so a primitive that wants to
 * look up a color at runtime (e.g. for a chart) doesn't have to
 * stringify Tailwind classes.
 */

export const colors = {
  primary: {
    50: '#ECFEFF', 100: '#CFFAFE', 200: '#A5F3FC', 300: '#67E8F9',
    400: '#22D3EE', 500: '#06B6D4', 600: '#0891B2', 700: '#0E7490',
    800: '#155E75', 900: '#164E63',
  },
  secondary: {
    50: '#FFFBEB', 100: '#FEF3C7', 200: '#FDE68A', 300: '#FCD34D',
    400: '#FBBF24', 500: '#F59E0B', 600: '#D97706', 700: '#B45309',
  },
  success: {
    50: '#ECFDF5', 100: '#D1FAE5', 500: '#10B981', 700: '#047857',
  },
  warning: {
    50: '#FFFBEB', 100: '#FEF3C7', 500: '#F59E0B', 700: '#B45309',
  },
  danger: {
    50: '#FEF2F2', 100: '#FEE2E2', 500: '#EF4444', 700: '#B91C1C',
  },
  info: {
    50: '#EFF6FF', 500: '#3B82F6', 700: '#1D4ED8',
  },
  neutral: {
    0: '#FFFFFF', 50: '#F8FAFC', 100: '#F1F5F9', 200: '#E2E8F0',
    300: '#CBD5E1', 400: '#94A3B8', 500: '#64748B', 600: '#475569',
    700: '#334155', 800: '#1E293B', 900: '#0F172A',
  },
} as const;

export const spacing = {
  'space-1': 4, 'space-2': 8, 'space-3': 12, 'space-4': 16,
  'space-6': 24, 'space-8': 32, 'space-12': 48, 'space-16': 64,
} as const;

export const radius = { sm: 4, DEFAULT: 8, md: 12, lg: 16, full: 9999 } as const;

export const shadow = {
  sm: { shadowColor: '#0F172A', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 2, elevation: 1 },
  DEFAULT: { shadowColor: '#0F172A', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.08, shadowRadius: 4, elevation: 2 },
  lg: { shadowColor: '#0F172A', shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.12, shadowRadius: 24, elevation: 8 },
} as const;
