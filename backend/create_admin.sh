#!/usr/bin/env bash
# Create or reset a Django superuser on the production Cloud Run / Cloud SQL stack.
# Safe to re-run — uses createsuperuser for new users, changepassword to reset existing ones.
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
step() { echo -e "\n${GREEN}▶ $*${NC}"; }
warn() { echo -e "${YELLOW}⚠ $*${NC}"; }
die()  { echo -e "${RED}✗ $*${NC}" >&2; exit 1; }

usage() {
  cat <<EOF
Usage: $0 [options]

Required:
  --project-id   GCP project ID (e.g. my-any-booking)
  --username     Admin username
  --email        Admin email address
  --password     Admin password

Optional:
  --region       GCP region (default: us-central1)
  --reset        Reset password for an existing user instead of creating a new one

Examples:
  # Create a new superuser
  ./create_admin.sh \\
    --project-id my-any-booking \\
    --username admin \\
    --email admin@example.com \\
    --password "ChangeMe123!"

  # Reset password for an existing superuser
  ./create_admin.sh \\
    --project-id my-any-booking \\
    --username admin \\
    --password "NewPassword123!" \\
    --reset
EOF
  exit 1
}

# ── Defaults ───────────────────────────────────────────────────────────────────
REGION="us-central1"
PROJECT_ID=""
USERNAME=""
EMAIL=""
PASSWORD=""
RESET=false

[[ $# -eq 0 ]] && usage

while [[ $# -gt 0 ]]; do
  case $1 in
    --project-id) PROJECT_ID="$2"; shift 2 ;;
    --username)   USERNAME="$2";   shift 2 ;;
    --email)      EMAIL="$2";      shift 2 ;;
    --password)   PASSWORD="$2";   shift 2 ;;
    --region)     REGION="$2";     shift 2 ;;
    --reset)      RESET=true;      shift ;;
    -h|--help)    usage ;;
    *) die "Unknown argument: $1. Run $0 --help for usage." ;;
  esac
done

[[ -z "$PROJECT_ID" ]] && die "--project-id is required"
[[ -z "$USERNAME"   ]] && die "--username is required"
[[ -z "$PASSWORD"   ]] && die "--password is required"
[[ "$RESET" == false && -z "$EMAIL" ]] && die "--email is required when creating a new user"

# ── Get latest image ───────────────────────────────────────────────────────────
step "Fetching latest image from Artifact Registry"
IMAGE=$(gcloud artifacts docker images list \
  "us-central1-docker.pkg.dev/${PROJECT_ID}/any-booking-repo/any-booking" \
  --sort-by="~CREATE_TIME" --limit=1 \
  --format="value(IMAGE,DIGEST)" | awk '{print $1"@"$2}')

[[ -z "$IMAGE" ]] && die "No image found in Artifact Registry for project ${PROJECT_ID}"
echo "  Image: ${IMAGE}"

# ── Run the job ────────────────────────────────────────────────────────────────
JOB_NAME="admin-$(date +%s)"
CLOUDSQL_INSTANCE="${PROJECT_ID}:${REGION}:any-booking-db"

if [[ "$RESET" == true ]]; then
  step "Resetting password for user '${USERNAME}'"
  # changepassword reads from stdin; pass via a shell heredoc through --args
  gcloud run jobs create "${JOB_NAME}" \
    --image="$IMAGE" \
    --region="${REGION}" \
    --set-cloudsql-instances="${CLOUDSQL_INSTANCE}" \
    --set-secrets="DATABASE_URL=DATABASE_URL:latest,SECRET_KEY=DJANGO_SECRET_KEY:latest" \
    --set-env-vars="DJANGO_NEW_PASSWORD=${PASSWORD}" \
    --command="python" \
    --args="manage.py,shell,-c,from django.contrib.auth.models import User; u=User.objects.get(username='${USERNAME}'); u.set_password('${PASSWORD}'); u.save(); print('Password updated for ${USERNAME}')" \
    --execute-now
else
  step "Creating superuser '${USERNAME}' (${EMAIL})"
  gcloud run jobs create "${JOB_NAME}" \
    --image="$IMAGE" \
    --region="${REGION}" \
    --set-cloudsql-instances="${CLOUDSQL_INSTANCE}" \
    --set-secrets="DATABASE_URL=DATABASE_URL:latest,SECRET_KEY=DJANGO_SECRET_KEY:latest" \
    --set-env-vars="DJANGO_SUPERUSER_PASSWORD=${PASSWORD}" \
    --command="python" \
    --args="manage.py,createsuperuser,--noinput,--username,${USERNAME},--email,${EMAIL}" \
    --execute-now
fi

# ── Cleanup ────────────────────────────────────────────────────────────────────
step "Cleaning up one-off job"
gcloud run jobs delete "${JOB_NAME}" --region="${REGION}" --quiet

echo -e "\n${GREEN}✓ Done!${NC}"
if [[ "$RESET" == true ]]; then
  echo "  Password for '${USERNAME}' has been reset."
else
  echo "  Superuser '${USERNAME}' created."
  echo "  Login at: https://$(gcloud run services describe any-booking \
    --region="${REGION}" --format='value(status.url)' \
    2>/dev/null | sed 's|https://||')/admin/"
fi
