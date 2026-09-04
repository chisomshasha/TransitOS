import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

export interface FieldProps {
  label: string;
  required?: boolean;
  error?: string;
  helperText?: string;
  children: React.ReactNode;
  className?: string;
}

export function Field({ label, required, error, helperText, children }: FieldProps) {
  return (
    <View style={styles.wrap}>
      <Text style={styles.label}>
        {label}
        {required ? <Text style={styles.req}> *</Text> : null}
      </Text>
      {children}
      {error ? (
        <Text style={styles.error}>{error}</Text>
      ) : helperText ? (
        <Text style={styles.helper}>{helperText}</Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginBottom: 16 },
  label: {
    fontSize: 12,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    color: '#475569',
    marginBottom: 4,
  },
  req: { color: '#EF4444' },
  error: { fontSize: 12, color: '#B91C1C', marginTop: 4 },
  helper: { fontSize: 12, color: '#64748B', marginTop: 4 },
});
