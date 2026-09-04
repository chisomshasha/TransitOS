import React from 'react';
import { KeyboardTypeOptions, StyleSheet, Text, TextInput, View } from 'react-native';

export interface InputProps {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  keyboardType?: KeyboardTypeOptions;
  autoCapitalize?: 'none' | 'sentences' | 'words' | 'characters';
  secureTextEntry?: boolean;
  autoCorrect?: boolean;
  testID?: string;
  accessibilityLabel?: string;
  error?: string;
  rightSlot?: React.ReactNode;
  className?: string;
}

export function Input({
  value,
  onChange,
  placeholder,
  keyboardType = 'default',
  autoCapitalize = 'sentences',
  secureTextEntry,
  autoCorrect = false,
  testID,
  accessibilityLabel,
  error,
  rightSlot,
}: InputProps) {
  return (
    <View>
      <View style={[styles.container, error ? styles.containerError : styles.containerNormal]}>
        <TextInput
          testID={testID}
          accessibilityLabel={accessibilityLabel}
          style={styles.input}
          placeholder={placeholder}
          placeholderTextColor="#94A3B8"
          keyboardType={keyboardType}
          autoCapitalize={autoCapitalize}
          autoCorrect={autoCorrect}
          secureTextEntry={secureTextEntry}
          value={value}
          onChangeText={onChange}
        />
        {rightSlot}
      </View>
      {error ? <Text style={styles.error}>{error}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    height: 48,
    paddingHorizontal: 12,
    borderRadius: 12,
    borderWidth: 1,
    backgroundColor: '#FFFFFF',
  },
  containerNormal: { borderColor: '#CBD5E1' },
  containerError: { borderColor: '#EF4444', backgroundColor: '#FEF2F2' },
  input: { flex: 1, fontSize: 16, color: '#0F172A', padding: 0 },
  error: { fontSize: 12, color: '#B91C1C', marginTop: 4 },
});
