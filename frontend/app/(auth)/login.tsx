import React, { useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
  ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { Bus, Eye, EyeOff } from 'lucide-react-native';

import { useAuth } from '@/lib/auth-context';
import { getErrorMessage } from '@/lib/api';

// Brand palette — matches approved mockup
const NAVY = '#0B3D91';
const NAVY_DEEP = '#072A66';
const YELLOW = '#FFCC00';
const YELLOW_DARK = '#E5B800';
const SLATE = '#0F172A';
const MUTED = '#64748B';
const FIELD_BG = '#F1F5F9';
const FIELD_BORDER = '#E2E8F0';

export default function LoginScreen() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async () => {
    setError(null);
    if (!email || !password) {
      setError('Please enter both email and password.');
      return;
    }
    setSubmitting(true);
    try {
      await login(email.trim().toLowerCase(), password);
      router.replace('/(app)');
    } catch (e) {
      setError(getErrorMessage(e, 'Could not log in.'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: NAVY_DEEP }}>
      <LinearGradient
        colors={[NAVY, NAVY_DEEP]}
        start={{ x: 0.5, y: 0 }}
        end={{ x: 0.5, y: 1 }}
        style={{ flex: 1 }}
      >
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={{ flex: 1 }}
        >
          <ScrollView
            contentContainerStyle={{
              flexGrow: 1,
              justifyContent: 'center',
              paddingHorizontal: 24,
              paddingVertical: 32,
            }}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
            bounces={false}
          >
            <View style={{ width: '100%', maxWidth: 400, alignSelf: 'center' }}>
              {/* Brand header — no white circle */}
              <View style={{ alignItems: 'center', marginBottom: 28 }}>
                <Bus color={YELLOW} size={48} strokeWidth={2.25} />
                <Text
                  style={{
                    marginTop: 12,
                    fontSize: 32,
                    fontWeight: '700',
                    color: '#FFFFFF',
                    letterSpacing: -0.5,
                  }}
                >
                  TransitOS
                </Text>
                <View
                  style={{
                    width: 48,
                    height: 3,
                    borderRadius: 2,
                    backgroundColor: YELLOW,
                    marginTop: 8,
                  }}
                />
                <Text
                  style={{
                    marginTop: 10,
                    fontSize: 13,
                    fontWeight: '500',
                    color: 'rgba(255,255,255,0.65)',
                    letterSpacing: 0.3,
                  }}
                >
                  Transport Operations · Unified
                </Text>
              </View>

              {/* Compact login card */}
              <View
                style={{
                  backgroundColor: '#FFFFFF',
                  borderRadius: 16,
                  paddingHorizontal: 22,
                  paddingTop: 24,
                  paddingBottom: 22,
                  shadowColor: '#000',
                  shadowOffset: { width: 0, height: 8 },
                  shadowOpacity: 0.18,
                  shadowRadius: 24,
                  elevation: 10,
                }}
              >
                <Text
                  style={{
                    fontSize: 20,
                    fontWeight: '700',
                    color: SLATE,
                    marginBottom: 4,
                  }}
                >
                  Welcome back
                </Text>
                <Text
                  style={{
                    fontSize: 13,
                    color: MUTED,
                    marginBottom: 20,
                  }}
                >
                  Sign in to continue
                </Text>

                {/* Email */}
                <Text
                  style={{
                    fontSize: 13,
                    fontWeight: '600',
                    color: SLATE,
                    marginBottom: 6,
                  }}
                >
                  Email
                </Text>
                <View
                  style={{
                    backgroundColor: FIELD_BG,
                    borderWidth: 1,
                    borderColor: error && !email ? '#EF4444' : FIELD_BORDER,
                    borderRadius: 10,
                    height: 48,
                    paddingHorizontal: 14,
                    justifyContent: 'center',
                    marginBottom: 14,
                  }}
                >
                  <TextInput
                    value={email}
                    onChangeText={setEmail}
                    placeholder="you@company.com"
                    placeholderTextColor="#94A3B8"
                    autoCapitalize="none"
                    autoCorrect={false}
                    keyboardType="email-address"
                    autoComplete="email"
                    returnKeyType="next"
                    testID="login-email"
                    style={{
                      fontSize: 15,
                      color: SLATE,
                      padding: 0,
                      margin: 0,
                    }}
                  />
                </View>

                {/* Password */}
                <Text
                  style={{
                    fontSize: 13,
                    fontWeight: '600',
                    color: SLATE,
                    marginBottom: 6,
                  }}
                >
                  Password
                </Text>
                <View
                  style={{
                    backgroundColor: FIELD_BG,
                    borderWidth: 1,
                    borderColor: error && !password ? '#EF4444' : FIELD_BORDER,
                    borderRadius: 10,
                    height: 48,
                    paddingHorizontal: 14,
                    flexDirection: 'row',
                    alignItems: 'center',
                    marginBottom: 8,
                  }}
                >
                  <TextInput
                    value={password}
                    onChangeText={setPassword}
                    placeholder="••••••••"
                    placeholderTextColor="#94A3B8"
                    secureTextEntry={!showPassword}
                    autoCapitalize="none"
                    autoComplete="password"
                    returnKeyType="go"
                    onSubmitEditing={onSubmit}
                    testID="login-password"
                    style={{
                      flex: 1,
                      fontSize: 15,
                      color: SLATE,
                      padding: 0,
                      margin: 0,
                    }}
                  />
                  <Pressable
                    onPress={() => setShowPassword((v) => !v)}
                    hitSlop={12}
                    accessibilityLabel={showPassword ? 'Hide password' : 'Show password'}
                    style={{ paddingLeft: 8 }}
                  >
                    {showPassword ? (
                      <EyeOff size={20} color={MUTED} />
                    ) : (
                      <Eye size={20} color={MUTED} />
                    )}
                  </Pressable>
                </View>

                {/* Forgot password */}
                <Pressable
                  onPress={() => router.push('/(auth)/forgot-password' as never)}
                  hitSlop={10}
                  style={{ alignSelf: 'flex-end', marginBottom: 16 }}
                >
                  <Text style={{ fontSize: 13, fontWeight: '600', color: NAVY }}>
                    Forgot password?
                  </Text>
                </Pressable>
				
				<Pressable
                  onPress={() => router.push('/(auth)/forgot-username' as never)}
                  hitSlop={10}
                  style={{ alignSelf: 'flex-end', marginBottom: 16 }}
                >
                  <Text style={{ fontSize: 13, fontWeight: '600', color: NAVY }}>
                    Forgot username?
                  </Text>
                </Pressable>

                {/* Error */}
                {error ? (
                  <View
                    style={{
                      backgroundColor: '#FEF2F2',
                      borderWidth: 1,
                      borderColor: '#FECACA',
                      borderRadius: 10,
                      paddingVertical: 10,
                      paddingHorizontal: 12,
                      marginBottom: 14,
                    }}
                  >
                    <Text style={{ fontSize: 13, color: '#B91C1C', textAlign: 'center' }}>
                      {error}
                    </Text>
                  </View>
                ) : null}

                {/* Sign In button */}
                <Pressable
                  onPress={onSubmit}
                  disabled={submitting}
                  testID="login-submit"
                  style={({ pressed }) => ({
                    backgroundColor: pressed ? YELLOW_DARK : YELLOW,
                    opacity: submitting ? 0.75 : 1,
                    borderRadius: 10,
                    height: 50,
                    alignItems: 'center',
                    justifyContent: 'center',
                    shadowColor: YELLOW,
                    shadowOffset: { width: 0, height: 4 },
                    shadowOpacity: 0.35,
                    shadowRadius: 10,
                    elevation: 4,
                  })}
                >
                  {submitting ? (
                    <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                      <ActivityIndicator size="small" color={NAVY} style={{ marginRight: 8 }} />
                      <Text style={{ fontSize: 16, fontWeight: '700', color: NAVY }}>
                        Signing in...
                      </Text>
                    </View>
                  ) : (
                    <Text style={{ fontSize: 16, fontWeight: '700', color: NAVY }}>
                      Sign In
                    </Text>
                  )}
                </Pressable>
              </View>

              {/* Footer */}
              <Text
                style={{
                  marginTop: 28,
                  textAlign: 'center',
                  fontSize: 12,
                  color: 'rgba(255,255,255,0.45)',
                }}
              >
                v1.1.0 · Secure login
              </Text>
            </View>
          </ScrollView>
        </KeyboardAvoidingView>
      </LinearGradient>
    </SafeAreaView>
  );
}
