import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Bell } from 'lucide-react-native';

export type SevTone = 'ok' | 'warn' | 'danger' | 'info' | 'neutral';

export const SEV: Record<SevTone, { fg: string; bg: string; bar: string }> = {
  ok: { fg: '#047857', bg: '#D1FAE5', bar: '#10B981' },
  warn: { fg: '#B45309', bg: '#FEF3C7', bar: '#F59E0B' },
  danger: { fg: '#B91C1C', bg: '#FEE2E2', bar: '#DC2626' },
  info: { fg: '#1D4ED8', bg: '#DBEAFE', bar: '#2563EB' },
  neutral: { fg: '#475569', bg: '#E2E8F0', bar: '#94A3B8' },
};

/** Map "days until expiry" to a severity tone. */
export function daysTone(days: number): SevTone {
  if (days <= 0) return 'danger';
  if (days <= 30) return 'warn';
  return 'ok';
}

export function Chip({ label, tone = 'neutral', active, onPress }: {
  label: string;
  tone?: SevTone;
  active?: boolean;
  onPress?: () => void;
}) {
  const t = SEV[tone];
  const inner = (
    <View style={[styles.chip, { backgroundColor: active ? '#0B3D91' : t.bg }]}>
      <Text style={[styles.chipText, { color: active ? '#FFFFFF' : t.fg }]}>{label}</Text>
    </View>
  );
  if (!onPress) return inner;
  return (
    <Pressable onPress={onPress} accessibilityRole="button">
      {inner}
    </Pressable>
  );
}

export function StatCard({ label, value, sub, subColor, icon, iconBg }: {
  label: string;
  value: string;
  sub?: string;
  subColor?: string;
  icon: React.ReactNode;
  iconBg: string;
}) {
  return (
    <View style={styles.statWrap}>
      <View style={styles.statCard}>
        <View style={styles.statTop}>
          <Text style={styles.statLabel}>{label}</Text>
          <View style={[styles.iconChip, { backgroundColor: iconBg }]}>{icon}</View>
        </View>
        <Text style={styles.statValue} numberOfLines={1}>{value}</Text>
        {sub ? <Text style={[styles.statSub, subColor ? { color: subColor } : null]}>{sub}</Text> : null}
      </View>
    </View>
  );
}

/** Card with a colored left severity bar. */
export function BarCard({ tone = 'neutral', children, style }: {
  tone?: SevTone;
  children: React.ReactNode;
  style?: any;
}) {
  return (
    <View style={[styles.barCard, { borderLeftColor: SEV[tone].bar }, style]}>
      {children}
    </View>
  );
}

const AVATAR_COLORS = ['#0B3D91', '#2563EB', '#B45309', '#047857', '#7C3AED', '#475569'];

export function Avatar({ name, size = 44 }: { name: string; size?: number }) {
  const initials = (name || '??')
    .split(/\s+/)
    .map((p) => p[0])
    .filter(Boolean)
    .slice(0, 2)
    .join('')
    .toUpperCase() || '??';
  const color = AVATAR_COLORS[(name || '?').charCodeAt(0) % AVATAR_COLORS.length];
  return (
    <View style={[styles.avatar, { width: size, height: size, borderRadius: size / 2, backgroundColor: color }]}>
      <Text style={[styles.avatarText, { fontSize: size * 0.36 }]}>{initials}</Text>
    </View>
  );
}

export function HeaderBell({ count, onPress }: { count: number; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} style={styles.bell} accessibilityRole="button" accessibilityLabel="Notifications">
      <Bell size={22} color="#FFFFFF" />
      {count > 0 ? (
        <View style={styles.bellBadge}>
          <Text style={styles.bellBadgeText}>{count > 99 ? '99+' : String(count)}</Text>
        </View>
      ) : null}
    </Pressable>
  );
}

export function SectionCard({ title, right, children }: {
  title?: string;
  right?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <View style={styles.section}>
      {title ? (
        <View style={styles.sectionHead}>
          <Text style={styles.sectionTitle}>{title}</Text>
          {right}
        </View>
      ) : null}
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  chip: { paddingHorizontal: 12, paddingVertical: 7, borderRadius: 10, marginRight: 6, marginBottom: 6 },
  chipText: { fontSize: 13, fontWeight: '600' },
  statWrap: { width: '50%', padding: 6 },
  statCard: { backgroundColor: '#F8FAFC', borderRadius: 14, borderWidth: 1, borderColor: '#E2E8F0', padding: 14, minHeight: 118 },
  statTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  statLabel: { fontSize: 11, fontWeight: '600', letterSpacing: 0.6, color: '#64748B', textTransform: 'uppercase', flex: 1, paddingRight: 6 },
  iconChip: { width: 40, height: 40, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  statValue: { fontSize: 26, fontWeight: '800', color: '#0F172A', marginTop: 8 },
  statSub: { fontSize: 12, fontWeight: '600', marginTop: 4, color: '#64748B' },
  barCard: {
    backgroundColor: '#F8FAFC',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    borderLeftWidth: 5,
    padding: 14,
    marginBottom: 12,
  },
  avatar: { alignItems: 'center', justifyContent: 'center' },
  avatarText: { color: '#FFFFFF', fontWeight: '700' },
  bell: { width: 44, height: 44, borderRadius: 12, backgroundColor: 'rgba(255,255,255,0.15)', alignItems: 'center', justifyContent: 'center' },
  bellBadge: { position: 'absolute', top: -4, right: -4, backgroundColor: '#DC2626', borderRadius: 10, minWidth: 20, height: 20, alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: '#0B3D91' },
  bellBadgeText: { color: '#FFFFFF', fontSize: 11, fontWeight: '700' },
  section: { backgroundColor: '#F8FAFC', borderRadius: 16, borderWidth: 1, borderColor: '#E2E8F0', padding: 14, marginBottom: 14 },
  sectionHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: '#0F172A' },
});
