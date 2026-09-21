#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REGION="us-central1"
PROJECT_ID=""
CLOUD_RUN_HOST="*"
SERVICE_NAME="any-booking"
REPOSITORY="any-booking-repo"
IMAGE="any-booking"
FIREBASE_PROJECT_NUMBER=""
APP_CHECK_RECAPTCHA_SITE_KEY=""

usage() {
  cat <<EOF
Usage: $0 --project-id PROJECT [options]

Options:
  --region REGION                    Default: us-central1
  --cloud-run-host HOST              Set ALLOWED_HOSTS; default: *
  --service-name NAME                Default: any-booking
  --firebase-project-number NUMBER   Enables App Check enforcement on the backend
  --app-check-recaptcha-site-key KEY reCAPTCHA v3 site key for App Check on the web build
EOF
  exit 1
}

die() { echo "Error: $*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-id) PROJECT_ID="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --cloud-run-host) CLOUD_RUN_HOST="$2"; shift 2 ;;
    --service-name) SERVICE_NAME="$2"; shift 2 ;;
    --firebase-project-number) FIREBASE_PROJECT_NUMBER="$2"; shift 2 ;;
    --app-check-recaptcha-site-key) APP_CHECK_RECAPTCHA_SITE_KEY="$2"; shift 2 ;;
    -h|--help) usage ;;
    *) die "Unknown argument: $1" ;;
  esac
done

[[ -n "$PROJECT_ID" ]] || die "--project-id is required"
command -v gcloud >/dev/null || die "gcloud CLI is required"
command -v flutter >/dev/null || die "Flutter is required"
command -v firebase >/dev/null || die "Firebase CLI is required (npm install -g firebase-tools)"

gcloud config set project "$PROJECT_ID" >/dev/null
BUILD_NUMBER="$(date -u +%Y%m%d%H%M%S)"
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE}:${BUILD_NUMBER}"
CLOUD_SQL_INSTANCE="${PROJECT_ID}:${REGION}:any-booking-db"

CORS_ALLOWED_ORIGINS="https://${PROJECT_ID}.web.app,https://${PROJECT_ID}.firebaseapp.com"
ENV_VARS="^|^ALLOWED_HOSTS=$CLOUD_RUN_HOST|CORS_ALLOWED_ORIGINS=$CORS_ALLOWED_ORIGINS"
if [[ -n "$FIREBASE_PROJECT_NUMBER" ]]; then
  ENV_VARS="${ENV_VARS}|FIREBASE_APP_CHECK_PROJECT_NUMBER=${FIREBASE_PROJECT_NUMBER}"
fi

printf '\nBuilding backend image...\n'
gcloud builds submit "$ROOT_DIR/backend" --tag "$IMAGE_URI" \
  --gcs-log-dir="gs://${PROJECT_ID}-build-logs/logs"

printf '\nDeploying backend to Cloud Run...\n'
gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE_URI" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --add-cloudsql-instances "$CLOUD_SQL_INSTANCE" \
  --set-env-vars "$ENV_VARS" \
  --set-secrets "SECRET_KEY=DJANGO_SECRET_KEY:latest,DATABASE_URL=DATABASE_URL:latest,RAZORPAY_KEY_ID=RAZORPAY_KEY_ID:latest,RAZORPAY_KEY_SECRET=RAZORPAY_KEY_SECRET:latest,EMAIL_BACKEND=EMAIL_BACKEND:latest,EMAIL_HOST=EMAIL_HOST:latest,EMAIL_HOST_USER=EMAIL_HOST_USER:latest,EMAIL_HOST_PASSWORD=EMAIL_HOST_PASSWORD:latest,DEFAULT_FROM_EMAIL=DEFAULT_FROM_EMAIL:latest,ADMIN_NOTIFY_EMAIL=ADMIN_NOTIFY_EMAIL:latest,SITE_URL=SITE_URL:latest,GCS_MEDIA_BUCKET=GCS_MEDIA_BUCKET:latest" \
  --memory 512Mi \
  --cpu 1 \
  --concurrency 80 \
  --timeout 120

API_URL="$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format='value(status.url)')"
printf '%s' "$API_URL" | gcloud secrets versions add SITE_URL --data-file=-

printf '\nBuilding Flutter web app...\n'
cd "$ROOT_DIR"
if [[ ! -d web ]]; then
  flutter create --platforms=web .
fi
flutter pub get
flutter build web --release --build-number="$BUILD_NUMBER" \
  --dart-define=API_BASE_URL="${API_URL}/api" \
  --dart-define=APP_CHECK_WEB_RECAPTCHA_SITE_KEY="${APP_CHECK_RECAPTCHA_SITE_KEY}"

printf '\nDeploying Flutter web app to Firebase Hosting...\n'
firebase deploy --only hosting --project "$PROJECT_ID" --non-interactive

printf '\nDeployment complete:\n  API: %s\n  Frontend: https://%s.web.app\n' "$API_URL" "$PROJECT_ID"
