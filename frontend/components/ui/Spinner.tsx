import React from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

export interface SpinnerProps {
  label?: string;
  size?: 'small' | 'large';
}

export function Spinner({ label, size = 'small' }: SpinnerProps) {
  return (
    <View style={styles.container}>
      <ActivityIndicator size={size} color="#0E7490" />
      {label ? <Text style={styles.label}>{label}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: 'center', justifyContent: 'center' },
  label: { fontSize: 14, color: '#64748B', marginTop: 8 },
});
