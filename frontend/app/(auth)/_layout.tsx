import { Stack } from 'expo-router';

export default function AuthLayout() {
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: '#0B3D91' },
      }}
    >
      <Stack.Screen name="login" />
      <Stack.Screen name="forgot-password" />
      <Stack.Screen name="forgot-username" />
      {/* NOTE: there is no separate `reset-password` route — the
          forgot-password screen handles both "request a code" and
          "set a new password" via an internal mode switch. Declaring
          a Stack.Screen for a non-existent file makes expo-router
          warn (and can throw on some versions), so it is omitted. */}
    </Stack>
  );
}
