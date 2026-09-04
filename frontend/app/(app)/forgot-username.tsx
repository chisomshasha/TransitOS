import React, { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { useRouter } from 'expo-router';
import { ArrowLeft, UserCircle } from 'lucide-react-native';
import { getErrorMessage, postNoContent } from '@/lib/api';

export default function ForgotUsernameScreen() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async () => {
    if (!email.trim()) return setError('Enter your account email.');
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) return setError('That email looks invalid.');
    setSubmitting(true);
    setError(null);
    try {
      await postNoContent('/auth/forgot-username', { email: email.trim().toLowerCase() });
      setSent(true);
    } catch (e) {
      setError(getErrorMessage(e, 'Could not send the username reminder.'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#072A66' }}>
      <LinearGradient
        colors={['#0B3D91', '#072A66']}
        start={{ x: 0.5, y: 0 }}
        end={{ x: 0.5, y: 1 }}
        style={{ flex: 1 }}
      >
        <ScrollView contentContainerStyle={{ padding: 24 }} keyboardShouldPersistTaps="handled">
          <Pressable onPress={() => router.back()} style={s.backRow} accessibilityRole="link">
            <ArrowLeft size={16} color="#BFDBFE" />
            <Text style={s.backText}>Back to sign in</Text>
          </Pressable>

          <View style={s.iconWrap}>
            <UserCircle size={26} color="#0B3D91" />
          </View>
          <Text style={s.title}>Forgot your username?</Text>
          <Text style={s.subtitle}>
            Enter your account email and we'll send you a reminder.
          </Text>

          {sent ? (
            <View style={s.card}>
              <Text style={s.successTitle}>Email sent</Text>
              <Text style={s.successBody}>
                If an account exists for {email.trim().toLowerCase()}, an email with your username is on its way.
              </Text>
              <Pressable style={s.primaryBtn} onPress={() => router.replace('/(auth)/login')}>
                <Text style={s.primaryBtnText}>Back to sign in</Text>
              </Pressable>
            </View>
          ) : (
            <View style={s.card}>
              <Text style={s.label}>EMAIL</Text>
              <TextInput
                style={s.input}
                value={email}
                onChangeText={setEmail}
                placeholder="you@company.com"
                placeholderTextColor="#94A3B8"
                keyboardType="email-address"
                autoCapitalize="none"
                autoCorrect={false}
              />
              {error ? <Text style={s.error}>{error}</Text> : null}
              <Pressable
                style={[s.primaryBtn, submitting && { opacity: 0.7 }]}
                onPress={onSubmit}
                disabled={submitting}
              >
                <Text style={s.primaryBtnText}>{submitting ? 'Sending…' : 'Send username'}</Text>
              </Pressable>
            </View>
          )}
        </ScrollView>
      </LinearGradient>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  backRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 20 },
  backText: { color: '#BFDBFE', fontSize: 13, fontWeight: '600', marginLeft: 6 },
  iconWrap: {
    width: 52,
    height: 52,
    borderRadius: 14,
    backgroundColor: '#FFCC00',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 14,
  },
  title: { fontSize: 26, fontWeight: '700', color: '#FFFFFF' },
  subtitle: { fontSize: 14, color: '#BFDBFE', marginTop: 6, marginBottom: 20, lineHeight: 20 },
  card: { backgroundColor: '#FFFFFF', borderRadius: 16, padding: 20 },
  label: { fontSize: 12, fontWeight: '600', letterSpacing: 0.5, color: '#475569', marginBottom: 6 },
  input: {
    height: 50,
    borderWidth: 1,
    borderColor: '#E2E8F0',
    borderRadius: 12,
    paddingHorizontal: 14,
    fontSize: 16,
    color: '#0F172A',
    backgroundColor: '#F8FAFC',
  },
  error: { color: '#B91C1C', fontSize: 13, marginTop: 8 },
  primaryBtn: {
    marginTop: 16,
    height: 50,
    borderRadius: 12,
    backgroundColor: '#FFCC00',
    alignItems: 'center',
    justifyContent: 'center',
  },
  primaryBtnText: { color: '#0B3D91', fontWeight: '700', fontSize: 16 },
  successTitle: { fontSize: 18, fontWeight: '700', color: '#047857', marginBottom: 8 },
  successBody: { fontSize: 14, color: '#475569', lineHeight: 20 },
});
