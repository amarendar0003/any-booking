#!/usr/bin/env bash
# One-time write of the iOS/TestFlight GitHub Actions secrets the `ios` job
# in .github/workflows/deploy.yml needs to stop being a no-op (it's disabled
# separately via `if: false` — see the comment on that job).
#
# Apple's certificate/profile/API-key creation itself is portal-only and not
# scriptable (see README.md#ios-app-testflight for the manual steps), so this
# script only handles the last mile: reading the files and IDs you collected
# from those steps out of a local JSON config and pushing them to `gh secret
# set`. It never prints secret values.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
step() { echo -e "\n${GREEN}▶ $*${NC}"; }
warn() { echo -e "${YELLOW}⚠ $*${NC}"; }
die()  { echo -e "${RED}✗ $*${NC}" >&2; exit 1; }

usage() {
  cat <<EOF
Usage: $0 [--config PATH] [--github-repo OWNER/REPO]

Options:
  --config       Path to the JSON credentials file (default: .private/credentials)
                 See .private/credentials.example.json for the expected shape.
  --github-repo  OWNER/REPO to write secrets to (default: current repo via \`gh repo view\`)

Example:
  $0 --config .private/credentials --github-repo josetonyin/any-booking-flutter
EOF
  exit 1
}

CONFIG="$ROOT_DIR/.private/credentials"
GITHUB_REPO=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config) CONFIG="$2"; shift 2 ;;
    --github-repo) GITHUB_REPO="$2"; shift 2 ;;
    -h|--help) usage ;;
    *) die "Unknown argument: $1" ;;
  esac
done

for command_name in gh python3; do
  command -v "$command_name" >/dev/null || die "$command_name is required"
done

[[ -f "$CONFIG" ]] || die "Config file not found: $CONFIG (see .private/credentials.example.json)"

if [[ -z "$GITHUB_REPO" ]]; then
  GITHUB_REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || true)"
  [[ -n "$GITHUB_REPO" ]] || die "Could not infer the GitHub repo; pass --github-repo OWNER/REPO"
fi

cd "$ROOT_DIR"

# ── 1. Read and validate the config ─────────────────────────────────────────
step "Reading $CONFIG"

CONFIG_JSON="$(python3 -c "
import json, sys

with open(sys.argv[1]) as f:
    data = json.load(f)

required = [
    'teamId',
    'appstoreApiKeyId',
    'appstoreApiIssuerId',
    'appstoreApiPrivateKeyFile',
    'distributionCertificateFile',
    'distributionCertificatePassword',
    'provisioningProfileFile',
    'provisioningProfileName',
]
missing = [k for k in required if not str(data.get(k, '')).strip()]
if missing:
    sys.stderr.write('Missing/empty fields in config: ' + ', '.join(missing) + '\n')
    sys.exit(1)

placeholders = ['REPLACE_ME', 'CHANGE_ME']
still_placeholder = [
    k for k in required
    if any(p in str(data.get(k, '')).upper() for p in placeholders)
]
if still_placeholder:
    sys.stderr.write('Fields still have placeholder values: ' + ', '.join(still_placeholder) + '\n')
    sys.exit(1)

print(json.dumps(data))
" "$CONFIG")" || die "Fix the config above (see .private/credentials.example.json) and re-run"

get_field() {
  python3 -c "import json,sys; print(json.loads(sys.argv[1]).get(sys.argv[2], ''))" "$CONFIG_JSON" "$1"
}

TEAM_ID="$(get_field teamId)"
API_KEY_ID="$(get_field appstoreApiKeyId)"
API_ISSUER_ID="$(get_field appstoreApiIssuerId)"
API_KEY_FILE="$(get_field appstoreApiPrivateKeyFile)"
CERT_FILE="$(get_field distributionCertificateFile)"
CERT_PASSWORD="$(get_field distributionCertificatePassword)"
PROFILE_FILE="$(get_field provisioningProfileFile)"
PROFILE_NAME="$(get_field provisioningProfileName)"
KEYCHAIN_PASSWORD="$(get_field keychainPassword)"

for path_var in API_KEY_FILE CERT_FILE PROFILE_FILE; do
  path="${!path_var}"
  [[ -f "$ROOT_DIR/$path" ]] || die "File referenced by config not found: $path"
done

if [[ -z "$KEYCHAIN_PASSWORD" ]]; then
  warn "keychainPassword not set in config; generating a throwaway one"
  KEYCHAIN_PASSWORD="$(openssl rand -base64 32)"
fi

# ── 2. Stage secret values in a private temp dir ────────────────────────────
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

b64() {
  python3 -c "
import base64, sys
sys.stdout.write(base64.b64encode(open(sys.argv[1], 'rb').read()).decode())
" "$1"
}

b64 "$ROOT_DIR/$CERT_FILE" > "$TMP_DIR/IOS_DIST_CERTIFICATE_BASE64"
printf '%s' "$CERT_PASSWORD" > "$TMP_DIR/IOS_DIST_CERTIFICATE_PASSWORD"
b64 "$ROOT_DIR/$PROFILE_FILE" > "$TMP_DIR/IOS_PROVISIONING_PROFILE_BASE64"
printf '%s' "$PROFILE_NAME" > "$TMP_DIR/IOS_PROVISIONING_PROFILE_NAME"
printf '%s' "$KEYCHAIN_PASSWORD" > "$TMP_DIR/IOS_KEYCHAIN_PASSWORD"
printf '%s' "$TEAM_ID" > "$TMP_DIR/APPSTORE_TEAM_ID"
printf '%s' "$API_KEY_ID" > "$TMP_DIR/APPSTORE_API_KEY_ID"
printf '%s' "$API_ISSUER_ID" > "$TMP_DIR/APPSTORE_API_ISSUER_ID"
cp "$ROOT_DIR/$API_KEY_FILE" "$TMP_DIR/APPSTORE_API_PRIVATE_KEY"

# ── 3. Write the GitHub Actions secrets ─────────────────────────────────────
step "Writing iOS GitHub Actions secrets to $GITHUB_REPO"
for name in IOS_DIST_CERTIFICATE_BASE64 IOS_DIST_CERTIFICATE_PASSWORD \
            IOS_PROVISIONING_PROFILE_BASE64 IOS_PROVISIONING_PROFILE_NAME \
            IOS_KEYCHAIN_PASSWORD APPSTORE_TEAM_ID APPSTORE_API_KEY_ID \
            APPSTORE_API_ISSUER_ID APPSTORE_API_PRIVATE_KEY; do
  gh secret set "$name" --repo "$GITHUB_REPO" < "$TMP_DIR/$name"
  echo "  set $name"
done

echo -e "\n${GREEN}Done.${NC} 9 secrets written to $GITHUB_REPO."
