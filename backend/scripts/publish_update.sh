#!/usr/bin/env bash
# Publish an over-the-air update to the phones that already have TransitOS.
#
#   bash backend/scripts/publish_update.sh                       # production
#   bash backend/scripts/publish_update.sh preview "Fix the clock"
#
# What it does, in order:
#   1. makes sure Node and npm are available (a Codespace created
#      before the devcontainer existed has neither);
#   2. makes sure the EAS CLI is available;
#   3. checks that the CLI is signed in as the account that owns the
#      project — publishing as the wrong account fails with a confusing
#      "project not found";
#   4. publishes the update and prints the update-group id, which is
#      what `eas update:edit` needs to widen a staged rollout.
#
# Safe to re-run. Nothing here touches the database or the code.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

CHANNEL="${1:-production}"
MESSAGE="${2:-}"

say()  { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[33m    %s\033[0m\n' "$*"; }
die()  { printf '\033[31m    %s\033[0m\n' "$*" >&2; exit 1; }

# ── 1. node ────────────────────────────────────────────────────────────────
say "Node"
if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
  echo "    node $(node -v) · npm $(npm -v) ✓"
else
  echo "    not found — installing Node 20"
  # NodeSource's apt repository. The Codespace default image ships a
  # Node, but a Codespace created before the devcontainer existed does
  # not, and the old apt nodejs on Debian is too old for Expo.
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - \
      || die "could not add the NodeSource repository"
    sudo apt-get update -qq
    sudo apt-get install -y -qq nodejs || die "could not install nodejs"
  else
    die "curl is missing — install Node 20 by hand, then re-run this script"
  fi
  command -v node >/dev/null 2>&1 || die "node is still not on the PATH"
  echo "    node $(node -v) · npm $(npm -v) ✓"
fi

# ── 2. the EAS CLI ─────────────────────────────────────────────────────────
say "EAS CLI"
if command -v eas >/dev/null 2>&1; then
  echo "    $(eas --version) ✓"
else
  echo "    not found — installing eas-cli globally"
  npm install -g eas-cli >/dev/null 2>&1 || die "could not install eas-cli"
  command -v eas >/dev/null 2>&1 || die "eas is still not on the PATH"
  echo "    $(eas --version) ✓"
fi

# ── 3. the account ────────────────────────────────────────────────────────
say "Account"
OWNER="$(grep -oE '"owner"[[:space:]]*:[[:space:]]*"[^"]+"' frontend/app.json | head -1 | cut -d'"' -f4)"
WHOAMI="$(eas whoami 2>/dev/null | tail -1 | tr -d '\r')"
if [ -z "$WHOAMI" ] || echo "$WHOAMI" | grep -qiE "not logged|login"; then
  warn "you are not signed in to Expo. Run:"
  warn "    eas login"
  warn "It prints a URL and a code — open the URL, paste the code, and"
  warn "come back. Then run this script again."
  exit 1
fi
echo "    signed in as $WHOAMI"
if [ -n "$OWNER" ] && [ "$WHOAMI" != "$OWNER" ]; then
  warn "the project is owned by '$OWNER' but you are signed in as '$WHOAMI'."
  warn "Publishing as the wrong account fails with 'project not found'."
  warn "Sign in as $OWNER:  eas logout && eas login"
  exit 1
fi

# ── 4. publish ─────────────────────────────────────────────────────────────
if [ -z "$MESSAGE" ]; then
  MESSAGE="Update $(date +%Y-%m-%d)"
  warn "no message given — using: $MESSAGE"
fi

say "Publishing to the '$CHANNEL' channel"
( cd frontend && eas update --channel "$CHANNEL" --message "$MESSAGE" ) || die "the publish failed"

cat <<EOF

    The update is on the '$CHANNEL' channel now.

    It reaches the phones in the background and is applied the next
    time the app is opened — close the app fully and open it again
    (twice if needed).

    To widen a staged rollout, take the update-group id from the
    output above and run:

        eas update:edit <group-id> --rollout-percentage 100

    To undo it:

        eas update:rollback
EOF
echo
