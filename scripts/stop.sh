#!/usr/bin/env bash
# Stops the Cloud SQL instance to avoid idle billing.
# Cloud Run already scales to zero automatically and needs no action.
set -euo pipefail

die() { echo "Error: $*" >&2; exit 1; }

usage() {
  cat <<EOF
Usage: $0 --project-id PROJECT [options]

Options:
  --region REGION     Default: us-central1
  --instance NAME     Default: any-booking-db
EOF
  exit 1
}

REGION="us-central1"
PROJECT_ID=""
INSTANCE="any-booking-db"

[[ $# -eq 0 ]] && usage
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-id) PROJECT_ID="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --instance) INSTANCE="$2"; shift 2 ;;
    -h|--help) usage ;;
    *) die "Unknown argument: $1" ;;
  esac
done

[[ -n "$PROJECT_ID" ]] || die "--project-id is required"
command -v gcloud >/dev/null || die "gcloud CLI is required"

gcloud config set project "$PROJECT_ID" >/dev/null

STATE="$(gcloud sql instances describe "$INSTANCE" --format='value(state)')"
if [[ "$STATE" == "STOPPED" ]]; then
  echo "Cloud SQL instance '$INSTANCE' is already stopped."
  exit 0
fi

echo "Stopping Cloud SQL instance '$INSTANCE'..."
gcloud sql instances patch "$INSTANCE" --activation-policy=NEVER --quiet

echo "Stopped. The app will not be able to reach the database until you run scripts/start.sh."
