#!/usr/bin/env bash
# Tears down the GCP infrastructure created by setup.sh.
# Destructive. Requires typed confirmation unless --yes is passed.
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
step() { echo -e "\n${GREEN}▶ $*${NC}"; }
warn() { echo -e "${YELLOW}⚠ $*${NC}"; }
die()  { echo -e "${RED}✗ $*${NC}" >&2; exit 1; }

usage() {
  cat <<EOF
Usage: $0 --project-id PROJECT [options]

Removes the Cloud Run service, Artifact Registry repository, Workload
Identity Federation pool, GitHub deployer service account, and Secret
Manager secrets created by setup.sh.

The Cloud SQL instance and media bucket hold real data and are left in
place unless you explicitly opt in to deleting them. Firebase Hosting
(the frontend) costs nothing while idle and is left running unless you
pass --disable-hosting.

Options:
  --region REGION            Default: us-central1
  --disable-hosting          Also disable Firebase Hosting for this project
  --delete-database          Also delete the Cloud SQL instance (irreversible data loss)
  --delete-media-bucket      Also delete PROJECT_ID-media (irreversible data loss)
  --github-repo OWNER/REPO   Also remove the GitHub Actions secrets setup.sh wrote
  --yes                      Skip the confirmation prompt
EOF
  exit 1
}

REGION="us-central1"; PROJECT_ID=""; GITHUB_REPO=""
DELETE_DATABASE=false; DELETE_MEDIA_BUCKET=false; DISABLE_HOSTING=false; ASSUME_YES=false

[[ $# -eq 0 ]] && usage
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-id) PROJECT_ID="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --github-repo) GITHUB_REPO="$2"; shift 2 ;;
    --delete-database) DELETE_DATABASE=true; shift ;;
    --delete-media-bucket) DELETE_MEDIA_BUCKET=true; shift ;;
    --disable-hosting) DISABLE_HOSTING=true; shift ;;
    --yes) ASSUME_YES=true; shift ;;
    -h|--help) usage ;;
    *) die "Unknown argument: $1" ;;
  esac
done

[[ -n "$PROJECT_ID" ]] || die "--project-id is required"
command -v gcloud >/dev/null || die "gcloud CLI is required"

SA_EMAIL="github-deployer@${PROJECT_ID}.iam.gserviceaccount.com"
MEDIA_BUCKET="${PROJECT_ID}-media"

echo -e "${RED}This will permanently delete infrastructure in project '${PROJECT_ID}':${NC}"
echo "  - Cloud Run service: any-booking"
echo "  - Artifact Registry repository: any-booking-repo (and all images)"
echo "  - Workload Identity Federation pool: github-pool"
echo "  - Service account: $SA_EMAIL"
echo "  - Secret Manager secrets (DJANGO_SECRET_KEY, DATABASE_URL, RAZORPAY_*, EMAIL_*, SITE_URL, GCS_MEDIA_BUCKET)"
[[ "$DISABLE_HOSTING" == true ]] && echo "  - Firebase Hosting for this project"
[[ "$DELETE_DATABASE" == true ]] && echo -e "  - ${RED}Cloud SQL instance: any-booking-db (ALL BOOKING DATA)${NC}"
[[ "$DELETE_MEDIA_BUCKET" == true ]] && echo -e "  - ${RED}Media bucket: gs://$MEDIA_BUCKET (ALL UPLOADED IMAGES)${NC}"

if [[ "$ASSUME_YES" != true ]]; then
  read -r -p $'\nType the project ID to confirm: ' CONFIRM
  [[ "$CONFIRM" == "$PROJECT_ID" ]] || die "Confirmation did not match. Aborting."
fi

gcloud config set project "$PROJECT_ID" >/dev/null

step "Deleting Cloud Run service"
gcloud run services delete any-booking --region="$REGION" --quiet 2>/dev/null || warn "Cloud Run service not found"

step "Deleting Artifact Registry repository"
gcloud artifacts repositories delete any-booking-repo --location="$REGION" --quiet 2>/dev/null || warn "Artifact Registry repository not found"

step "Deleting Secret Manager secrets"
for name in DJANGO_SECRET_KEY DATABASE_URL RAZORPAY_KEY_ID RAZORPAY_KEY_SECRET \
  EMAIL_BACKEND EMAIL_HOST EMAIL_HOST_USER EMAIL_HOST_PASSWORD DEFAULT_FROM_EMAIL \
  ADMIN_NOTIFY_EMAIL SITE_URL GCS_MEDIA_BUCKET; do
  gcloud secrets delete "$name" --quiet 2>/dev/null || warn "Secret $name not found"
done

step "Removing Workload Identity Federation"
gcloud iam workload-identity-pools providers delete github-provider --location=global \
  --workload-identity-pool=github-pool --quiet 2>/dev/null || warn "OIDC provider not found"
gcloud iam workload-identity-pools delete github-pool --location=global --quiet 2>/dev/null || warn "WIF pool not found"

step "Deleting GitHub deployer service account"
gcloud iam service-accounts delete "$SA_EMAIL" --quiet 2>/dev/null || warn "Service account not found"

if [[ "$DISABLE_HOSTING" == true ]]; then
  step "Disabling Firebase Hosting"
  command -v firebase >/dev/null || die "Firebase CLI is required (npm install -g firebase-tools)"
  firebase hosting:disable --project "$PROJECT_ID" --non-interactive 2>/dev/null || warn "Firebase Hosting not found or already disabled"
fi

if [[ "$DELETE_MEDIA_BUCKET" == true ]]; then
  step "Deleting media bucket"
  gcloud storage rm --recursive "gs://$MEDIA_BUCKET" --quiet 2>/dev/null || warn "Media bucket not found"
fi

if [[ "$DELETE_DATABASE" == true ]]; then
  step "Deleting Cloud SQL instance"
  gcloud sql instances delete any-booking-db --quiet 2>/dev/null || warn "Cloud SQL instance not found"
fi

if [[ -n "$GITHUB_REPO" ]]; then
  step "Removing GitHub Actions secrets"
  command -v gh >/dev/null || die "gh CLI is required to remove GitHub secrets"
  for name in GCP_PROJECT_ID GCP_WORKLOAD_IDENTITY_PROVIDER GCP_SERVICE_ACCOUNT \
    CLOUD_SQL_INSTANCE CLOUD_RUN_HOST; do
    gh secret delete "$name" --repo "$GITHUB_REPO" 2>/dev/null || warn "GitHub secret $name not found"
  done
fi

echo -e "\n${GREEN}Teardown complete.${NC}"
if [[ "$DELETE_DATABASE" != true ]]; then
  echo "Cloud SQL instance 'any-booking-db' was left in place. Delete it manually or re-run with --delete-database."
fi
if [[ "$DELETE_MEDIA_BUCKET" != true ]]; then
  echo "Media bucket 'gs://$MEDIA_BUCKET' was left in place. Delete it manually or re-run with --delete-media-bucket."
fi
