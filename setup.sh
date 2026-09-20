#!/usr/bin/env bash
# One-time Google Cloud setup for AnyBooking.
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
step() { echo -e "\n${GREEN}▶ $*${NC}"; }
warn() { echo -e "${YELLOW}⚠ $*${NC}"; }
die() { echo -e "${RED}✗ $*${NC}" >&2; exit 1; }

usage() {
  cat <<EOF
Usage: $0 --project-id PROJECT --db-password PASSWORD --github-repo OWNER/REPO \
  [options]

Options:
  --region REGION
  --razorpay-key-id KEY_ID
  --razorpay-key-secret SECRET
  --email-user EMAIL
  --email-password APP_PASSWORD
  --from-email ADDRESS
  --admin-email EMAIL
  --site-url URL
EOF
  exit 1
}

REGION="us-central1"; PROJECT_ID=""; DB_PASSWORD=""; GITHUB_REPO=""
RAZORPAY_KEY_ID="PLACEHOLDER"; RAZORPAY_KEY_SECRET="PLACEHOLDER"
EMAIL_USER=""; EMAIL_PASSWORD=""; FROM_EMAIL="AnyBooking <noreply@anybooking.in>"
ADMIN_EMAIL=""; SITE_URL="https://PLACEHOLDER"

[[ $# -eq 0 ]] && usage
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-id) PROJECT_ID="$2"; shift 2 ;;
    --db-password) DB_PASSWORD="$2"; shift 2 ;;
    --github-repo) GITHUB_REPO="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --razorpay-key-id) RAZORPAY_KEY_ID="$2"; shift 2 ;;
    --razorpay-key-secret) RAZORPAY_KEY_SECRET="$2"; shift 2 ;;
    --email-user) EMAIL_USER="$2"; shift 2 ;;
    --email-password) EMAIL_PASSWORD="$2"; shift 2 ;;
    --from-email) FROM_EMAIL="$2"; shift 2 ;;
    --admin-email) ADMIN_EMAIL="$2"; shift 2 ;;
    --site-url) SITE_URL="$2"; shift 2 ;;
    -h|--help) usage ;;
    *) die "Unknown argument: $1" ;;
  esac
done

[[ -n "$PROJECT_ID" ]] || die "--project-id is required"
[[ -n "$DB_PASSWORD" ]] || die "--db-password is required"
[[ -n "$GITHUB_REPO" ]] || die "--github-repo is required"
for command_name in gcloud gh python3 firebase; do
  command -v "$command_name" >/dev/null || die "$command_name is required (firebase: npm install -g firebase-tools)"
done

EMAIL_USER="${EMAIL_USER:-PLACEHOLDER}"
EMAIL_PASSWORD="${EMAIL_PASSWORD:-PLACEHOLDER}"
ADMIN_EMAIL="${ADMIN_EMAIL:-$EMAIL_USER}"
SA_EMAIL="github-deployer@${PROJECT_ID}.iam.gserviceaccount.com"
PROJECT_NUMBER=""

step "Setting active project and enabling APIs"
gcloud config set project "$PROJECT_ID"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com sqladmin.googleapis.com \
  artifactregistry.googleapis.com secretmanager.googleapis.com iam.googleapis.com \
  iamcredentials.googleapis.com storage.googleapis.com playintegrity.googleapis.com \
  firebaseappcheck.googleapis.com firebase.googleapis.com firebasehosting.googleapis.com \
  firebaseappdistribution.googleapis.com

step "Creating Artifact Registry repository"
if gcloud artifacts repositories describe any-booking-repo --location="$REGION" >/dev/null 2>&1; then
  warn "Artifact Registry repository already exists"
else
  gcloud artifacts repositories create any-booking-repo --repository-format=docker --location="$REGION"
fi

step "Creating Cloud SQL PostgreSQL"
if gcloud sql instances describe any-booking-db >/dev/null 2>&1; then
  warn "Cloud SQL instance already exists"
else
  gcloud sql instances create any-booking-db --database-version=POSTGRES_16 --edition=ENTERPRISE \
    --tier=db-f1-micro --region="$REGION" --storage-auto-increase
fi
gcloud sql databases describe anybooking --instance=any-booking-db >/dev/null 2>&1 || \
  gcloud sql databases create anybooking --instance=any-booking-db
gcloud sql users create anybooking_user --instance=any-booking-db --password="$DB_PASSWORD" 2>/dev/null || \
  gcloud sql users set-password anybooking_user --instance=any-booking-db --password="$DB_PASSWORD"

step "Creating deployment service account and permissions"
if gcloud iam service-accounts describe "$SA_EMAIL" >/dev/null 2>&1; then
  warn "GitHub deployment service account already exists"
else
  gcloud iam service-accounts create github-deployer --display-name="GitHub Actions Deployer"
fi
for role in roles/run.admin roles/cloudbuild.builds.editor roles/artifactregistry.writer \
  roles/secretmanager.secretAccessor roles/cloudsql.client roles/iam.serviceAccountUser \
  roles/firebasehosting.admin roles/firebaseappdistro.admin roles/serviceusage.serviceUsageConsumer \
  roles/storage.admin; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$SA_EMAIL" \
    --role="$role" --condition=None >/dev/null
done
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
for role in roles/secretmanager.secretAccessor roles/storage.admin \
  roles/cloudsql.client roles/artifactregistry.writer roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$RUNTIME_SA" \
    --role="$role" --condition=None >/dev/null || true
done

MEDIA_BUCKET="${PROJECT_ID}-media"
if gsutil ls "gs://$MEDIA_BUCKET" >/dev/null 2>&1; then
  warn "Media bucket already exists"
else
  gsutil mb -l "$REGION" "gs://$MEDIA_BUCKET"
fi

step "Creating Cloud Build logs bucket"
BUILD_LOGS_BUCKET="${PROJECT_ID}-build-logs"
if gsutil ls "gs://$BUILD_LOGS_BUCKET" >/dev/null 2>&1; then
  warn "Build logs bucket already exists"
else
  gsutil mb -l "$REGION" "gs://$BUILD_LOGS_BUCKET"
fi

step "Configuring GitHub Workload Identity Federation"
gcloud iam workload-identity-pools describe github-pool --location=global >/dev/null 2>&1 || \
  gcloud iam workload-identity-pools create github-pool --location=global --display-name="GitHub Actions Pool"
if gcloud iam workload-identity-pools providers describe github-provider --location=global \
  --workload-identity-pool=github-pool >/dev/null 2>&1; then
  warn "GitHub OIDC provider already exists"
else
  gcloud iam workload-identity-pools providers create-oidc github-provider --location=global \
    --workload-identity-pool=github-pool --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
    --attribute-condition="assertion.repository=='$GITHUB_REPO'"
fi
POOL_ID="$(gcloud iam workload-identity-pools describe github-pool --location=global --format='value(name)')"
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/$POOL_ID/attribute.repository/$GITHUB_REPO" >/dev/null || true

step "Creating Google Secret Manager secrets"
create_secret() {
  local name="$1" value="$2"
  if gcloud secrets describe "$name" >/dev/null 2>&1; then
    [[ "$value" == PLACEHOLDER ]] && warn "$name already exists; skipping placeholder" || \
      printf '%s' "$value" | gcloud secrets versions add "$name" --data-file=- >/dev/null
  else
    printf '%s' "$value" | gcloud secrets create "$name" --data-file=- >/dev/null
  fi
}
DJANGO_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(50), end="")')"
DB_URL="postgres://anybooking_user:${DB_PASSWORD}@/anybooking?host=/cloudsql/${PROJECT_ID}:${REGION}:any-booking-db"
create_secret DJANGO_SECRET_KEY "$DJANGO_SECRET_KEY"
create_secret DATABASE_URL "$DB_URL"
create_secret RAZORPAY_KEY_ID "$RAZORPAY_KEY_ID"
create_secret RAZORPAY_KEY_SECRET "$RAZORPAY_KEY_SECRET"
create_secret EMAIL_BACKEND "django.core.mail.backends.smtp.EmailBackend"
create_secret EMAIL_HOST smtp.gmail.com
create_secret EMAIL_HOST_USER "$EMAIL_USER"
create_secret EMAIL_HOST_PASSWORD "$EMAIL_PASSWORD"
create_secret DEFAULT_FROM_EMAIL "$FROM_EMAIL"
create_secret ADMIN_NOTIFY_EMAIL "$ADMIN_EMAIL"
create_secret SITE_URL "$SITE_URL"
create_secret GCS_MEDIA_BUCKET "$MEDIA_BUCKET"

step "Linking Firebase to the GCP project"
firebase projects:addfirebase "$PROJECT_ID" --non-interactive >/dev/null 2>&1 || \
  warn "Firebase already linked to this project (or requires manual setup at https://console.firebase.google.com)"

step "Writing GitHub Actions secrets"
WIF_PROVIDER="$(gcloud iam workload-identity-pools providers describe github-provider --location=global \
  --workload-identity-pool=github-pool --format='value(name)')"
gh secret set GCP_PROJECT_ID --body "$PROJECT_ID" --repo "$GITHUB_REPO"
gh secret set GCP_WORKLOAD_IDENTITY_PROVIDER --body "$WIF_PROVIDER" --repo "$GITHUB_REPO"
gh secret set GCP_SERVICE_ACCOUNT --body "$SA_EMAIL" --repo "$GITHUB_REPO"
gh secret set CLOUD_SQL_INSTANCE --body "${PROJECT_ID}:${REGION}:any-booking-db" --repo "$GITHUB_REPO"
gh secret set CLOUD_RUN_HOST --body "*" --repo "$GITHUB_REPO"

echo -e "\n${GREEN}Setup complete. Run ./scripts/deploy.sh or push to main.${NC}"
echo "Frontend will deploy to Firebase Hosting at: https://${PROJECT_ID}.web.app"