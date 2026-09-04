import React, { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { useRouter } from 'expo-router';
import { ArrowLeft, KeyRound, ShieldCheck } from 'lucide-react-native';
import { getErrorMessage, postNoContent } from '@/lib/api';

type Mode = 'request' | 'reset';

export default function ForgotPasswordScreen() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>('request');

  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);

  const [token, setToken] = useState('');
  const [pw, setPw] = useState('');
  const [pw2, setPw2] = useState('');
  const [done, setDone] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const switchMode = (m: Mode) => { setError(null); setMode(m); };

  const onRequest = async () => {
    if (!email.trim()) return setError('Enter your account email.');
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) return setError('That email looks invalid.');
    setSubmitting(true); setError(null);
    try {
      await postNoContent('/auth/forgot-password', { email: email.trim().toLowerCase() });
      setSent(true);
    } catch (e) {
      setError(getErrorMessage(e, 'Could not send the reset request.'));
    } finally { setSubmitting(false); }
  };

  const onReset = async () => {
    if (!token.trim()) return setError('Paste the reset code from your email.');
    if (pw.length < 8) return setError('Password must be at least 8 characters.');
    if (pw !== pw2) return setError('Passwords do not match.');
    setSubmitting(true); setError(null);
    try {
      await postNoContent('/auth/reset-password', { token: token.trim(), new_password: pw });
      setDone(true);
    } catch (e) {
      setError(getErrorMessage(e, 'Could not reset the password.'));
    } finally { setSubmitting(false); }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: '#072A66' }}>
      <LinearGradient colors={['#0B3D91', '#072A66']} start={{ x: 0.5, y: 0 }} end={{ x: 0.5, y: 1 }} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={{ padding: 24 }} keyboardShouldPersistTaps="handled">
          <Pressable onPress={() => router.back()} style={s.backRow} accessibilityRole="link">
            <ArrowLeft size={16} color="#BFDBFE" />
            <Text style={s.backText}>Back to sign in</Text>
          </Pressable>

          <View style={s.iconWrap}>
            {mode === 'request' ? <KeyRound size={26} color="#0B3D91" /> : <ShieldCheck size={26} color="#0B3D91" />}
          </View>
          <Text style={s.title}>{mode === 'request' ? 'Reset your password' : 'Set a new password'}</Text>
          <Text style={s.subtitle}>
            {mode === 'request'
              ? "Enter your account email and we'll send a reset code."
              : 'Paste the reset code from your email and choose a new password.'}
          </Text>

          {mode === 'request' ? (
            sent ? (
              <View style={s.card}>
                <Text style={s.successTitle}>Request sent</Text>
                <Text style={s.successBody}>
                  If an account exists for {email.trim().toLowerCase()}, an email with your reset
                  code is on its way (it expires in 30 minutes).
                </Text>
                <Pressable style={s.primaryBtn} onPress={() => switchMode('reset')}>
                  <Text style={s.primaryBtnText}>I have my code</Text>
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
                <Pressable style={[s.primaryBtn, submitting && { opacity: 0.7 }]} onPress={onRequest} disabled={submitting}>
                  <Text style={s.primaryBtnText}>{submitting ? 'Sending…' : 'Send reset code'}</Text>
                </Pressable>
              </View>
            )
          ) : done ? (
            <View style={s.card}>
              <Text style={s.successTitle}>Password updated</Text>
              <Text style={s.successBody}>Your password has been changed. Sign in with your new password.</Text>
              <Pressable style={s.primaryBtn} onPress={() => router.replace('/(auth)/login')}>
                <Text style={s.primaryBtnText}>Sign in now</Text>
              </Pressable>
            </View>
          ) : (
            <View style={s.card}>
              <Text style={s.label}>RESET CODE</Text>
              <TextInput
                style={s.input}
                value={token}
                onChangeText={setToken}
                placeholder="Paste code from email"
                placeholderTextColor="#94A3B8"
                autoCapitalize="none"
                autoCorrect={false}
              />
              <Text style={[s.label, { marginTop: 14 }]}>NEW PASSWORD</Text>
              <TextInput
                style={s.input}
                value={pw}
                onChangeText={setPw}
                placeholder="At least 8 characters"
                placeholderTextColor="#94A3B8"
                secureTextEntry
                autoCapitalize="none"
              />
              <Text style={[s.label, { marginTop: 14 }]}>CONFIRM NEW PASSWORD</Text>
              <TextInput
                style={s.input}
                value={pw2}
                onChangeText={setPw2}
                placeholder="Repeat new password"
                placeholderTextColor="#94A3B8"
                secureTextEntry
                autoCapitalize="none"
              />
              {error ? <Text style={s.error}>{error}</Text> : null}
              <Pressable style={[s.primaryBtn, submitting && { opacity: 0.7 }]} onPress={onReset} disabled={submitting}>
                <Text style={s.primaryBtnText}>{submitting ? 'Saving…' : 'Set new password'}</Text>
              </Pressable>
            </View>
          )}

          <Pressable style={s.toggleRow} onPress={() => switchMode(mode === 'request' ? 'reset' : 'request')} accessibilityRole="link">
            <Text style={s.toggleText}>
              {mode === 'request' ? 'I already have a reset code' : 'I need a new reset code'}
            </Text>
          </Pressable>
        </ScrollView>
      </LinearGradient>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  backRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 20 },
  backText: { color: '#BFDBFE', fontSize: 13, fontWeight: '600', marginLeft: 6 },
  iconWrap: { width: 52, height: 52, borderRadius: 14, backgroundColor: '#FFCC00', alignItems: 'center', justifyContent: 'center', marginBottom: 14 },
  title: { fontSize: 26, fontWeight: '700', color: '#FFFFFF' },
  subtitle: { fontSize: 14, color: '#BFDBFE', marginTop: 6, marginBottom: 20, lineHeight: 20 },
  card: { backgroundColor: '#FFFFFF', borderRadius: 16, padding: 20 },
  label: { fontSize: 12, fontWeight: '600', letterSpacing: 0.5, color: '#475569', marginBottom: 6 },
  input: { height: 50, borderWidth: 1, borderColor: '#E2E8F0', borderRadius: 12, paddingHorizontal: 14, fontSize: 16, color: '#0F172A', backgroundColor: '#F8FAFC' },
  error: { color: '#B91C1C', fontSize: 13, marginTop: 8 },
  primaryBtn: { marginTop: 16, height: 50, borderRadius: 12, backgroundColor: '#FFCC00', alignItems: 'center', justifyContent: 'center' },
  primaryBtnText: { color: '#0B3D91', fontWeight: '700', fontSize: 16 },
  successTitle: { fontSize: 18, fontWeight: '700', color: '#047857', marginBottom: 8 },
  successBody: { fontSize: 14, color: '#475569', lineHeight: 20 },
  toggleRow: { alignItems: 'center', marginTop: 18, paddingVertical: 6 },
  toggleText: { color: '#BFDBFE', fontSize: 13, fontWeight: '600', textDecorationLine: 'underline' },
});
