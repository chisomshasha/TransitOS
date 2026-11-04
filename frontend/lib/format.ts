/**
 * Formatters — Nigerian Naira, dates, odometer.
 * Numbers in the app use `font-variant-numeric: tabular-nums` (set
 * on `text-mono` / `font-mono` Tailwind utility) so columns line up.
 */

export function formatNGN(amount: number | null | undefined): string {
  const v = typeof amount === 'number' && Number.isFinite(amount) ? amount : 0;
  // Matches the convention used throughout the app: whole Naira, comma
  // thousands separator, no decimal places (e.g. ₦487,500).
  return `₦${v.toLocaleString('en-NG')}`;
}

const DATE_FMT = new Intl.DateTimeFormat('en-US', {
  year: 'numeric',
  month: 'short',
  day: 'numeric',
});

const DATETIME_FMT = new Intl.DateTimeFormat('en-US', {
  year: 'numeric',
  month: 'short',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
});

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return DATE_FMT.format(d);
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return DATETIME_FMT.format(d).replace(',', ' ·');
}

export function formatOdometer(km: number | null | undefined): string {
  const v = typeof km === 'number' && Number.isFinite(km) ? km : 0;
  return `${v.toLocaleString('en-NG')} km`;
}

export function initials(fullName: string | null | undefined): string {
  if (!fullName) return '?';
  const parts = fullName.trim().split(/\s+/).slice(0, 2);
  return parts.map((p) => p[0]?.toUpperCase() ?? '').join('') || '?';
}
