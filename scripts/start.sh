#!/usr/bin/env bash
# Starts the Cloud SQL instance after it has been stopped with scripts/stop.sh.
# Cloud Run needs no action — it scales up automatically on the next request.
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
if [[ "$STATE" == "RUNNABLE" ]]; then
  echo "Cloud SQL instance '$INSTANCE' is already running."
  exit 0
fi

echo "Starting Cloud SQL instance '$INSTANCE'..."
gcloud sql instances patch "$INSTANCE" --activation-policy=ALWAYS --quiet

echo "Waiting for instance to become RUNNABLE..."
until [[ "$(gcloud sql instances describe "$INSTANCE" --format='value(state)')" == "RUNNABLE" ]]; do
  sleep 5
done

echo "Cloud SQL instance '$INSTANCE' is running."
