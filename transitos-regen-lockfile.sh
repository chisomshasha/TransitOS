#!/usr/bin/env bash
# TransitOS — regenerate package-lock.json to match the new package.json.
# EAS runs `npm ci` which is strict: the lockfile MUST be in sync with
# package.json. This script regenerates the lock and verifies it.
# ----------------------------------------------------------------
set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

step()  { echo -e "\n${CYAN}${BOLD}━━━ $1 ━━━${RESET}"; }
ok()    { echo -e "${GREEN}✓${RESET} $1"; }
warn()  { echo -e "${YELLOW}!${RESET} $1"; }
fail()  { echo -e "${RED}✗${RESET} $1"; exit 1; }

# ─── go to frontend/ ──────────────────────────────────────────────
if [ -d "./frontend" ] && [ -f "./frontend/package.json" ]; then
  cd ./frontend
  ok "Working in: $(pwd)"
elif [ -f "./package.json" ]; then
  ok "Working in: $(pwd)"
else
  fail "No package.json found. Run from repo root or frontend/."
fi

step "Step 1/5  —  Remove old lockfile + node_modules"
rm -f package-lock.json yarn.lock pnpm-lock.yaml
rm -rf node_modules .expo
ok "old lockfile and caches purged"

step "Step 2/5  —  Regenerate lockfile (this is the key step)"
echo "Running: npm install --legacy-peer-deps"
echo "(takes 1-3 minutes depending on network)"
npm install --legacy-peer-deps --no-audit --no-fund 2>&1 | tail -15
[ -f "package-lock.json" ] && ok "package-lock.json created" || fail "lockfile not created"

step "Step 3/5  —  Verify lockfile matches package.json"
echo "This is exactly what EAS checks with 'npm ci'."
if npm ci --dry-run --legacy-peer-deps >/tmp/npm-ci-dryrun.log 2>&1; then
  ok "lockfile is in sync — 'npm ci' would succeed"
else
  cat /tmp/npm-ci-dryrun.log | tail -20
  fail "lockfile STILL out of sync. See errors above."
fi

step "Step 4/5  —  Spot-check the key package versions in the lockfile"
for pkg in expo babel-preset-expo expo-router lucide-react-native react react-native nativewind; do
  ver=$(node -e "const lock = require('./package-lock.json'); const pkgs = lock.packages || {}; const entry = pkgs['node_modules/$pkg']; console.log(entry ? entry.version : 'NOT IN LOCK');" 2>/dev/null || echo "ERR")
  printf "  %-22s %s\n" "$pkg" "$ver"
done

step "Step 5/5  —  Run expo doctor as a final check"
npx --yes expo doctor 2>&1 | tail -10 || warn "expo doctor had warnings (review above)"

cat <<'NOTE'

━━━━━━━━━━━━━━━━ ✅  Lockfile regenerated ━━━━━━━━━━━━━━━━━━━━

  NEXT: commit and push the new lockfile:
        cd ..
        git add frontend/package.json frontend/package-lock.json frontend/.npmrc .npmrc
        git commit -m "fix: regenerate lockfile to match SDK 54 versions"
        git push

  Then re-trigger the EAS build:
        cd frontend
        eas build --profile preview --platform android

  EAS will now run `npm ci` against the fresh lockfile and succeed.

NOTE
echo -e "${GREEN}${BOLD}Ready to push.${RESET}"
