import React from 'react';
import { StyleSheet, TextInput, View } from 'react-native';
import { Search } from 'lucide-react-native';

export interface SearchBarProps {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  className?: string;
}

export function SearchBar({ value, onChange, placeholder = 'Search…' }: SearchBarProps) {
  return (
    <View style={styles.container}>
      <Search size={18} color="#94A3B8" />
      <TextInput
        style={styles.input}
        placeholder={placeholder}
        placeholderTextColor="#94A3B8"
        value={value}
        onChangeText={onChange}
        autoCapitalize="none"
        autoCorrect={false}
        returnKeyType="search"
      />
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
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
  input: { flex: 1, marginLeft: 8, fontSize: 16, color: '#0F172A', padding: 0 },
});
