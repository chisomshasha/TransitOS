# Fixing `expo doctor` warnings

The previous package.json had version pins from **mixed Expo SDK releases** —
some packages from SDK 54, some from SDK 56, some stuck on very old versions.
This is a common situation when `npx create-expo-app` is run with outdated
defaults or packages are installed ad-hoc.

## What was wrong (and what we changed)

| Package | Before | After | Why |
|---|---|---|---|
| `expo-linking` | `^56.0.13` | `~8.0.12` | The `56.x` line is for SDK 56; SDK 54 needs `~8.x` |
| `expo-splash-screen` | `~0.29.0` | `~31.0.13` | The `0.29.x` is years old; SDK 54 needs `~31.x` |
| `expo-constants` | (missing) | `~18.0.0` | Required peer dep of `expo-router` |
| `babel-preset-expo` | `~13.0.0` | `~54.0.10` | Must match the Expo SDK major (54) |
| `react-native-worklets` | `^0.9.1` | `0.5.1` | `0.9.x` is SDK 56 territory |
| `react-native-svg` | `~15.13.0` | `15.12.1` | Strict pin to match doctor |
| `react-native-webview` | `~13.16.0` | `13.15.0` | Strict pin to match doctor |
| `typescript` | `~5.7.0` | `~5.9.2` | Strict pin to match doctor |

## How to apply

From the `frontend/` directory:

```bash
rm -rf node_modules package-lock.json yarn.lock
npm install
npx expo install --check       # verify everything resolves
npx expo doctor                # should now show 18/18 ✓
```

If `npx expo install --check` still suggests upgrades, accept them — but
**do not let it bump `expo` to a different SDK major** (staying on SDK 54 is
intentional for the JSC engine lock-in we did in Sprint A).

## Why this matters for EAS builds

If `expo doctor` fails locally, **EAS cloud builds will also fail or warn**.
Cloud builds run in a clean environment with no chance to interactively
resolve issues, so resolving them locally first is essential.

The duplicate `expo-constants@18.0.13` vs `56.0.17` warning was caused by
`expo-linking@^56.x` pulling in the SDK 56 version of `expo-constants`. By
pinning `expo-linking` to `~8.0.12`, the SDK 54 version of `expo-constants`
(~18.x) is now used consistently — no more duplicates.
