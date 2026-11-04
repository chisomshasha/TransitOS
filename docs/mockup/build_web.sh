#!/usr/bin/env bash
# Build the web export used for the User Manual mockups.
#
# resolveBaseURL() prefers EXPO_PUBLIC_API_URL over app.json's
# extra.apiUrl, so the env var alone is enough to redirect the build.
# We patch app.json as well so the checked-in file stays honest about
# what the capture ran against, and always restore it.
#
#   bash docs/mockup/build_web.sh [api_url]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FRONTEND="$ROOT/frontend"
API_URL="${1:-http://127.0.0.1:8000}"

cd "$FRONTEND"
cp app.json app.json.mockup-backup

restore() {
    if [ -f app.json.mockup-backup ]; then
        mv app.json.mockup-backup app.json
    fi
}
trap restore EXIT INT TERM

python3 - "$API_URL" <<'PY'
import json, sys
api = sys.argv[1]
with open('app.json') as fh:
    data = json.load(fh)
root = data.get('expo', data)
root.setdefault('extra', {})['apiUrl'] = api
with open('app.json', 'w') as fh:
    json.dump(data, fh, indent=2)
print(f"[mockup] app.json patched -> {api}")
PY

echo "[mockup] building web export..."
EXPO_PUBLIC_API_URL="$API_URL" npx expo export --platform web --clear

restore
trap - EXIT INT TERM

cp assets/transitos-logo.png dist/logo.png
echo "[mockup] done -> $FRONTEND/dist (real logo copied to dist/logo.png)"
