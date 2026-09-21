#!/usr/bin/env bash
# One-time Android app registration for Firebase App Distribution.
# Generates the android/ platform (if missing), sets the applicationId,
# registers the app with Firebase, creates a tester group, and optionally
# writes the GitHub Actions secrets the `android` job in
# .github/workflows/deploy.yml needs to stop being a no-op.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
step() { echo -e "\n${GREEN}▶ $*${NC}"; }
warn() { echo -e "${YELLOW}⚠ $*${NC}"; }
die()  { echo -e "${RED}✗ $*${NC}" >&2; exit 1; }

usage() {
  cat <<EOF
Usage: $0 --project-id PROJECT --package-name PACKAGE [options]

Required:
  --project-id       GCP/Firebase project ID (e.g. ny-booking-prod)
  --package-name     Android applicationId (reverse-domain, e.g. com.anybooking.app)

Options:
  --tester-group-name    Display name for the App Distribution tester group (default: Testers)
  --tester-group-alias   Alias for the tester group (default: testers)
  --github-repo          OWNER/REPO — also writes FIREBASE_ANDROID_APP_ID and
                          FIREBASE_TESTER_GROUP as GitHub Actions secrets

Example:
  $0 --project-id ny-booking-prod --package-name com.anybooking.app \\
    --github-repo josetonyin/any-booking-flutter
EOF
  exit 1
}

PROJECT_ID=""; PACKAGE_NAME=""; GITHUB_REPO=""
GROUP_NAME="Testers"; GROUP_ALIAS="testers"

[[ $# -eq 0 ]] && usage
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-id) PROJECT_ID="$2"; shift 2 ;;
    --package-name) PACKAGE_NAME="$2"; shift 2 ;;
    --tester-group-name) GROUP_NAME="$2"; shift 2 ;;
    --tester-group-alias) GROUP_ALIAS="$2"; shift 2 ;;
    --github-repo) GITHUB_REPO="$2"; shift 2 ;;
    -h|--help) usage ;;
    *) die "Unknown argument: $1" ;;
  esac
done

[[ -n "$PROJECT_ID" ]] || die "--project-id is required"
[[ -n "$PACKAGE_NAME" ]] || die "--package-name is required"
[[ "$PACKAGE_NAME" =~ ^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$ ]] || \
  die "--package-name must be reverse-domain, lowercase (e.g. com.example.app)"

for command_name in flutter firebase python3; do
  command -v "$command_name" >/dev/null || die "$command_name is required"
done
[[ -n "$GITHUB_REPO" ]] && { command -v gh >/dev/null || die "gh is required with --github-repo"; }

cd "$ROOT_DIR"

# ── 1. Generate the android/ platform if it doesn't exist ──────────────────
if [[ -d android ]]; then
  warn "android/ already exists; skipping flutter create"
else
  step "Generating Android platform files"
  flutter create --platforms=android .
fi

# ── 2. Set the applicationId / namespace ────────────────────────────────────
GRADLE_FILE="android/app/build.gradle.kts"
[[ -f "$GRADLE_FILE" ]] || die "$GRADLE_FILE not found"

step "Setting applicationId to $PACKAGE_NAME"
CURRENT_NAMESPACE="$(sed -n 's/.*namespace = "\(.*\)"/\1/p' "$GRADLE_FILE" | head -1)"
sed -i.bak \
  -e "s/namespace = \".*\"/namespace = \"$PACKAGE_NAME\"/" \
  -e "s/applicationId = \".*\"/applicationId = \"$PACKAGE_NAME\"/" \
  "$GRADLE_FILE"
rm -f "${GRADLE_FILE}.bak"

# ── 3. Move MainActivity.kt to match the new package path ──────────────────
if [[ -n "$CURRENT_NAMESPACE" && "$CURRENT_NAMESPACE" != "$PACKAGE_NAME" ]]; then
  KOTLIN_ROOT="android/app/src/main/kotlin"
  OLD_DIR="$KOTLIN_ROOT/$(echo "$CURRENT_NAMESPACE" | tr '.' '/')"
  NEW_DIR="$KOTLIN_ROOT/$(echo "$PACKAGE_NAME" | tr '.' '/')"
  if [[ -f "$OLD_DIR/MainActivity.kt" ]]; then
    step "Moving MainActivity.kt to new package path"
    mkdir -p "$NEW_DIR"
    mv "$OLD_DIR/MainActivity.kt" "$NEW_DIR/MainActivity.kt"
    sed -i.bak "s/^package .*/package $PACKAGE_NAME/" "$NEW_DIR/MainActivity.kt"
    rm -f "$NEW_DIR/MainActivity.kt.bak"
    # Clean up now-empty old package directories, deepest first.
    old_walk="$OLD_DIR"
    while [[ "$old_walk" != "$KOTLIN_ROOT" && -d "$old_walk" ]]; do
      rmdir "$old_walk" 2>/dev/null || break
      old_walk="$(dirname "$old_walk")"
    done
  fi
fi

# ── 4. Register the app with Firebase (idempotent) ──────────────────────────
step "Checking for an existing Firebase Android app with this package name"
APP_ID="$(firebase apps:list android --project "$PROJECT_ID" --json 2>/dev/null \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)
for app in data.get('result', []):
    if app.get('packageName') == '$PACKAGE_NAME':
        print(app['appId'])
        break
")"

if [[ -n "$APP_ID" ]]; then
  warn "App already registered; reusing App ID $APP_ID"
else
  step "Registering Android app with Firebase"
  CREATE_OUTPUT="$(firebase apps:create android --package-name "$PACKAGE_NAME" --project "$PROJECT_ID")"
  echo "$CREATE_OUTPUT"
  APP_ID="$(echo "$CREATE_OUTPUT" | sed -n 's/.*App ID: \(.*\)/\1/p' | head -1)"
  [[ -n "$APP_ID" ]] || die "Could not parse App ID from firebase apps:create output"
fi

# ── 5. Create the tester group (idempotent) ─────────────────────────────────
step "Checking for tester group '$GROUP_ALIAS'"
GROUP_EXISTS="$(firebase appdistribution:group:list --project "$PROJECT_ID" --json 2>/dev/null \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)
groups = data.get('result', {}).get('groups', [])
print('yes' if any(g['name'].rsplit('/', 1)[-1] == '$GROUP_ALIAS' for g in groups) else 'no')
")"

if [[ "$GROUP_EXISTS" == "yes" ]]; then
  warn "Tester group '$GROUP_ALIAS' already exists; skipping"
else
  step "Creating tester group '$GROUP_NAME' ($GROUP_ALIAS)"
  firebase appdistribution:group:create "$GROUP_NAME" "$GROUP_ALIAS" --project "$PROJECT_ID"
fi

# ── 6. Optionally write GitHub Actions secrets ──────────────────────────────
if [[ -n "$GITHUB_REPO" ]]; then
  step "Writing GitHub Actions secrets to $GITHUB_REPO"
  gh secret set FIREBASE_ANDROID_APP_ID --body "$APP_ID" --repo "$GITHUB_REPO"
  gh secret set FIREBASE_TESTER_GROUP --body "$GROUP_ALIAS" --repo "$GITHUB_REPO"
fi

echo -e "\n${GREEN}Done.${NC}"
echo "  App ID:      $APP_ID"
echo "  Tester group: $GROUP_ALIAS"
if [[ -z "$GITHUB_REPO" ]]; then
  echo -e "\n  Add these as GitHub repository secrets to enable the android job in deploy.yml:"
  echo "    FIREBASE_ANDROID_APP_ID = $APP_ID"
  echo "    FIREBASE_TESTER_GROUP   = $GROUP_ALIAS"
fi
