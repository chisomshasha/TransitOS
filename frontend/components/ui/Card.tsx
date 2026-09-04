import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

export interface CardProps {
  children: React.ReactNode;
  onPress?: () => void;
  variant?: 'default' | 'outlined' | 'elevated';
  padding?: 'sm' | 'md' | 'lg';
  className?: string;
  testID?: string;
}

const PADDING = { sm: 12, md: 16, lg: 24 } as const;

export function Card({ children, onPress, variant = 'default', padding = 'md', testID }: CardProps) {
  const style = [
    styles.base,
    { padding: PADDING[padding] },
    variant === 'outlined' ? styles.outlined : null,
    variant === 'elevated' ? styles.elevated : styles.shadow,
  ];
  if (onPress) {
    return (
      <Pressable
        testID={testID}
        onPress={onPress}
        style={({ pressed }) => [...style, { opacity: pressed ? 0.8 : 1 }]}
        android_ripple={{ color: 'rgba(8, 145, 178, 0.08)' }}
      >
        {children}
      </Pressable>
    );
  }
  return (
    <View testID={testID} style={style}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  base: { backgroundColor: '#FFFFFF', borderRadius: 12 },
  outlined: { borderWidth: 1, borderColor: '#E5E7EB' },
  shadow: { shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 3, elevation: 2 },
  elevated: { shadowColor: '#000', shadowOffset: { width: 0, height: 10 }, shadowOpacity: 0.1, shadowRadius: 15, elevation: 6 },
});
