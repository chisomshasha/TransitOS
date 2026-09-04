import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

export type BadgeTone = 'neutral' | 'success' | 'warning' | 'danger' | 'info' | 'primary';
export interface BadgeProps {
  label: string;
  tone?: BadgeTone;
  size?: 'sm' | 'md';
  className?: string;
}

const TONE = {
  neutral: { bg: '#F1F5F9', text: '#334155' },
  success: { bg: '#ECFDF5', text: '#047857' },
  warning: { bg: '#FFFBEB', text: '#B45309' },
  danger: { bg: '#FEF2F2', text: '#B91C1C' },
  info: { bg: '#EFF6FF', text: '#1D4ED8' },
  primary: { bg: '#ECFEFF', text: '#0E7490' },
} as const;

export function Badge({ label, tone = 'neutral', size = 'md' }: BadgeProps) {
  const t = TONE[tone];
  return (
    <View style={[styles.base, size === 'sm' ? styles.sm : styles.md, { backgroundColor: t.bg }]}>
      <Text style={[styles.text, size === 'sm' ? styles.textSm : styles.textMd, { color: t.text }]}>
        {label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  base: { borderRadius: 9999, alignSelf: 'flex-start' },
  sm: { paddingHorizontal: 8, paddingVertical: 2 },
  md: { paddingHorizontal: 10, paddingVertical: 4 },
  text: { fontWeight: '500' },
  textSm: { fontSize: 11 },
  textMd: { fontSize: 12 },
});
