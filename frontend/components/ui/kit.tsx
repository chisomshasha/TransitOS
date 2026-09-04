/**
 * Shared small primitives used across several screens: a filter/selector
 * Chip, a colored-accent BarCard wrapper, and an initials Avatar.
 *
 * Colors mirror `lib/theme.ts` (`brand`) so tone usage stays consistent
 * with Badge.tsx and the rest of the navy/yellow design system.
 */

import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { brand } from '@/lib/theme';

export type SevTone = 'neutral' | 'ok' | 'warn' | 'danger' | 'info';

const TONE: Record<SevTone, { text: string; bg: string; border: string; solid: string }> = {
  neutral: { text: '#475569', bg: '#F1F5F9', border: brand.border, solid: brand.navy },
  ok: { text: brand.success, bg: brand.successBg, border: '#A7F3D0', solid: brand.success },
  warn: { text: brand.warning, bg: brand.warningBg, border: '#FDE68A', solid: brand.warning },
  danger: { text: brand.danger, bg: brand.dangerBg, border: '#FECACA', solid: brand.danger },
  info: { text: brand.info, bg: brand.infoBg, border: '#BFDBFE', solid: brand.info },
};

// ─── Chip ──────────────────────────────────────────────────────────────────
export interface ChipProps {
  label: string;
  tone?: SevTone;
  active?: boolean;
  onPress?: () => void;
}

export function Chip({ label, tone = 'neutral', active = false, onPress }: ChipProps) {
  const t = TONE[tone];
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityState={{ selected: active }}
      style={({ pressed }) => [
        styles.chip,
        {
          backgroundColor: active ? t.solid : t.bg,
          borderColor: active ? t.solid : t.border,
          opacity: pressed ? 0.85 : 1,
        },
      ]}
    >
      <Text style={[styles.chipText, { color: active ? '#FFFFFF' : t.text }]} numberOfLines={1}>
        {label}
      </Text>
    </Pressable>
  );
}

// ─── BarCard ─────────────────────────────────────────────────────────────
export interface BarCardProps {
  tone?: SevTone;
  children: React.ReactNode;
}

export function BarCard({ tone = 'neutral', children }: BarCardProps) {
  const t = TONE[tone];
  return <View style={[styles.barCard, { borderLeftColor: t.solid }]}>{children}</View>;
}

// ─── Avatar ──────────────────────────────────────────────────────────────
export interface AvatarProps {
  name?: string | null;
  size?: number;
}

export function Avatar({ name, size = 40 }: AvatarProps) {
  return (
    <View
      style={[
        styles.avatar,
        { width: size, height: size, borderRadius: size / 2, backgroundColor: brand.navy },
      ]}
    >
      <Text style={{ color: '#FFFFFF', fontSize: size * 0.4, fontWeight: '700' }}>
        {getInitials(name)}
      </Text>
    </View>
  );
}

function getInitials(name?: string | null): string {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

const styles = StyleSheet.create({
  chip: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 9999,
    borderWidth: 1,
    marginRight: 8,
  },
  chipText: {
    fontSize: 13,
    fontWeight: '600',
  },
  barCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    borderLeftWidth: 4,
    padding: 14,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
    elevation: 2,
  },
  avatar: {
    alignItems: 'center',
    justifyContent: 'center',
  },
});
