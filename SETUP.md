# AnyBooking — Setup & Deployment Guide

This is the single setup, deployment and operations guide for the repository. It covers:

- **Django API** — Cloud Run, backed by Cloud SQL for PostgreSQL, images in Artifact Registry
- **Flutter web app** — Firebase Hosting
- **Android app** — Firebase App Distribution (optional)
- **iOS app** — TestFlight (optional)
- **CI/CD** — GitHub Actions with Workload Identity Federation (no JSON keys in GitHub)
- **Backend administration** — admin dashboard, vendors, payments, email, terms, and so on

The active Flutter project is the repository root. The `anybookingflutter/` directory is a separate Flutter project and is not used by deployment — do not run deployment commands from it.

## Contents

1. [Architecture](#architecture)
2. [Scripts](#scripts)
3. [Prerequisites](#prerequisites)
4. [One-time GCP setup](#one-time-gcp-setup)
5. [Infrastructure reference](#infrastructure-reference)
6. [Deploying](#deploying)
7. [Post-deploy steps](#post-deploy-steps)
8. [Firebase Hosting and custom domains](#firebase-hosting-and-custom-domains)
9. [Android app (Firebase App Distribution)](#android-app-firebase-app-distribution)
10. [iOS app (TestFlight)](#ios-app-testflight)
11. [Infrastructure lifecycle](#infrastructure-lifecycle)
12. [Local development](#local-development)
13. [Backend administration guide](#admin-dashboard)

## Architecture

```
GitHub (push to main)
  └── GitHub Actions
        ├── 1. Django checks + tests (against ephemeral Postgres)
        ├── 2. Build Docker image → push to Artifact Registry
        ├── 3. Deploy to Cloud Run
        │       └── Cloud SQL Auth Proxy (socket) → Cloud SQL PostgreSQL
        ├── 4. Build Flutter web → Firebase Hosting
        ├── 5. (optional) Build release APK → Firebase App Distribution
        └── 6. (optional, manual) Build iOS → TestFlight
```

Cloud Run is configured with 0–10 instances (scales to zero when idle), 512 Mi RAM, 1 vCPU, 80 concurrent requests per instance and a 120 s request timeout.

## Scripts

| Script | Purpose |
|---|---|
| [`setup.sh`](setup.sh) | One-time full GCP setup (infrastructure, secrets, GitHub Actions config) |
| [`scripts/deploy.sh`](scripts/deploy.sh) | Repeat deployments of the backend and Flutter web app |
| [`scripts/register_android.sh`](scripts/register_android.sh) | One-time Android app registration with Firebase App Distribution |
| [`scripts/set_ios_secrets.sh`](scripts/set_ios_secrets.sh) | One-time write of the iOS/TestFlight GitHub Actions secrets from a local credentials file |
| [`scripts/stop.sh`](scripts/stop.sh) / [`scripts/start.sh`](scripts/start.sh) | Stop/start the Cloud SQL instance to control idle billing |
| [`scripts/teardown.sh`](scripts/teardown.sh) | Remove the GCP infrastructure created by `setup.sh` |
| [`backend/create_admin.sh`](backend/create_admin.sh) | Create or reset a Django admin user in production |

## Prerequisites

Install the CLIs:

| Tool | Install | Verify |
|---|---|---|
| Google Cloud CLI | [cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install) | `gcloud --version` |
| GitHub CLI | `brew install gh` (macOS) or [cli.github.com](https://cli.github.com) | `gh --version` |
| Firebase CLI | `npm install -g firebase-tools` | `firebase --version` |
| Python 3.11+ | `brew install python@3.11` (macOS) | `python3 --version` |

Authenticate:

```bash
gcloud auth login
gcloud auth application-default login
gh auth login
```

You need a GCP project with billing enabled.

**Use an existing project:**

```bash
gcloud projects list          # find your project ID
gcloud config set project YOUR_PROJECT_ID
```

**Or create a new one** (the ID must be globally unique: lowercase letters, numbers, hyphens):

```bash
gcloud projects create any-booking-prod --name="AnyBooking"
gcloud config set project any-booking-prod

# Link a billing account (required for Cloud Run, Cloud SQL, Artifact Registry, Cloud Build)
gcloud billing accounts list
gcloud billing projects link any-booking-prod \
  --billing-account=XXXXXX-XXXXXX-XXXXXX
```

The project ID is used with `--project-id` and the GitHub secret `GCP_PROJECT_ID`; it is different from the display name and project number.

Optionally set a shell variable so you don't have to substitute it in every command:

```bash
export PROJECT_ID=$(gcloud config get-value project)
```

> Always use curly braces (`${PROJECT_ID}`, not `$PROJECT_ID`) — in zsh, `$PROJECT_ID:us-central1` is misread as an uppercase modifier, silently corrupting the value.

## One-time GCP setup

From the repository root, run the setup script. It is safe to re-run:

```bash
./setup.sh \
  --project-id YOUR_GCP_PROJECT_ID \
  --db-password 'CHOOSE_A_STRONG_DATABASE_PASSWORD' \
  --github-repo YOUR_GITHUB_OWNER/YOUR_REPOSITORY \
  --email-user you@example.com \
  --email-password YOUR_SMTP_APP_PASSWORD \
  --admin-email you@example.com
```

Optional payment credentials can be supplied with `--razorpay-key-id` and `--razorpay-key-secret`, or added later:

```bash
echo -n "rzp_live_XXXX" | gcloud secrets versions add RAZORPAY_KEY_ID --data-file=-
echo -n "your_secret"   | gcloud secrets versions add RAZORPAY_KEY_SECRET --data-file=-
```

The script performs these steps in order, skipping any that already exist:

1. Enable required GCP APIs
2. Create the Artifact Registry repository
3. Create the Cloud SQL instance, database and user
4. Create the `github-deployer` service account and grant all required roles
5. Grant the Cloud Run runtime service account its roles
6. Set up Workload Identity Federation (keyless GitHub Actions auth)
7. Store all secrets in Google Secret Manager
8. Link Firebase to the project for Hosting
9. Set all GitHub Actions secrets via `gh`

> Cloud SQL creation takes ~5 minutes. The script waits automatically.

## Infrastructure reference

What `setup.sh` does, for when you need to do it by hand or debug it.

### Enable services

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  storage.googleapis.com \
  playintegrity.googleapis.com \
  firebaseappcheck.googleapis.com \
  firebase.googleapis.com \
  firebasehosting.googleapis.com \
  firebaseappdistribution.googleapis.com
```

### Artifact Registry

```bash
gcloud artifacts repositories create any-booking-repo \
  --repository-format=docker \
  --location=us-central1
```

### Cloud SQL

```bash
gcloud sql instances create any-booking-db \
  --database-version=POSTGRES_16 \
  --edition=ENTERPRISE \
  --tier=db-f1-micro \
  --region=us-central1 \
  --storage-auto-increase

gcloud sql databases create anybooking --instance=any-booking-db
gcloud sql users create anybooking_user \
  --instance=any-booking-db \
  --password='CHOOSE_A_STRONG_PASSWORD'
```

The production `DATABASE_URL` must use the Cloud SQL Unix socket:

```text
postgres://anybooking_user:PASSWORD@/anybooking?host=/cloudsql/PROJECT_ID:us-central1:any-booking-db
```

### Secrets (Google Secret Manager)

Runtime application secrets live in Secret Manager, not GitHub. The pipeline mounts them on every deploy, so no GitHub secret is needed for these:

```text
DJANGO_SECRET_KEY        DATABASE_URL
RAZORPAY_KEY_ID          RAZORPAY_KEY_SECRET
EMAIL_BACKEND            EMAIL_HOST
EMAIL_HOST_USER          EMAIL_HOST_PASSWORD
DEFAULT_FROM_EMAIL       ADMIN_NOTIFY_EMAIL
SITE_URL                 GCS_MEDIA_BUCKET
```

Create the two required ones:

```bash
printf '%s' 'DJANGO_SECRET_KEY_VALUE' | gcloud secrets create DJANGO_SECRET_KEY --data-file=-
printf '%s' 'DATABASE_URL_VALUE'      | gcloud secrets create DATABASE_URL --data-file=-
```

Create the rest when needed:

```bash
for name in RAZORPAY_KEY_ID RAZORPAY_KEY_SECRET EMAIL_BACKEND \
  EMAIL_HOST EMAIL_HOST_USER EMAIL_HOST_PASSWORD DEFAULT_FROM_EMAIL \
  ADMIN_NOTIFY_EMAIL SITE_URL GCS_MEDIA_BUCKET; do
  printf '%s' 'SET_VALUE' | gcloud secrets create "$name" --data-file=-
done
```

Replace a secret value later with:

```bash
printf '%s' 'NEW_VALUE' | gcloud secrets versions add SECRET_NAME --data-file=-
```

Typical values: `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST=smtp.gmail.com`, `DEFAULT_FROM_EMAIL="AnyBooking <noreply@anybooking.in>"`.

### IAM roles

Two separate identities need IAM roles, and their needs differ — `setup.sh` grants both automatically.

**Runtime service account** (`PROJECT_NUMBER-compute@developer.gserviceaccount.com`, the default Compute Engine service account — Cloud Run runs as this identity, and so does `gcloud builds submit`/`gcloud run deploy` when run manually via `scripts/deploy.sh`, since no `--service-account` override is set):

- `roles/secretmanager.secretAccessor` — read runtime app secrets
- `roles/storage.admin` — read/write the media bucket, and bucket-level access (`storage.buckets.get`) to the custom Cloud Build logs bucket (see below) — this is the Cloud Build *worker* identity, not just the submitter, and it independently needs access to whatever bucket `--gcs-log-dir` points at. `storage.objectAdmin` alone is not enough; missing this fails `gcloud builds submit` with `invalid bucket "..."; service account ...-compute@developer.gserviceaccount.com does not have access to the bucket`
- `roles/cloudsql.client` — connect to Cloud SQL over the Unix socket (missing this causes `gcloud run deploy` to fail its startup health check with a Cloud SQL `403 NOT_AUTHORIZED` in the logs)
- `roles/artifactregistry.writer` — push the built image (missing this causes `gcloud builds submit` to fail with a retry-budget-exhausted push error)
- `roles/logging.logWriter` — write build logs

**GitHub deployment service account** (`github-deployer@PROJECT_ID.iam.gserviceaccount.com`, used via Workload Identity Federation in CI):

- `roles/run.admin`
- `roles/cloudbuild.builds.editor`
- `roles/artifactregistry.writer`
- `roles/secretmanager.secretAccessor`
- `roles/cloudsql.client`
- `roles/iam.serviceAccountUser`
- `roles/firebasehosting.admin`
- `roles/firebaseappdistro.admin`
- `roles/serviceusage.serviceUsageConsumer` and `roles/storage.admin` — both required for `gcloud builds submit` to access the auto-created `PROJECT_ID_cloudbuild` staging bucket; missing either fails with `The user is forbidden from accessing the bucket [..._cloudbuild]`. That bucket uses legacy ACLs scoped to the primitive `projectEditor`/`projectOwner`/`projectViewer` roles rather than plain IAM, so project-level custom roles alone don't grant access to it. `roles/storage.admin` (not just `storage.objectAdmin` — the build also needs bucket-level `storage.buckets.get`, not just object access) at the project level does, additively, regardless of when the bucket gets created.

`gcloud builds submit` also polls Cloud Build for completion by tailing logs from Google's default logs bucket, which requires being a project Viewer/Owner — and this held true even after granting `roles/viewer` directly, so treat it as unreliable/not worth chasing further. `roles/logging.viewer` and `--suppress-logs` don't help either (confirmed by direct reproduction) — `--suppress-logs` only skips printing logs, the polling still runs. The actual fix both `scripts/deploy.sh` and `.github/workflows/deploy.yml` use: pass `--gcs-log-dir="gs://PROJECT_ID-build-logs/logs"`, a bucket `setup.sh` creates. This routes logs to a bucket under normal project IAM instead of Google's externally-managed default bucket, sidestepping the primitive-role check entirely — but note both the submitting identity (`github-deployer`) *and* the Cloud Build worker identity (the runtime service account, see above) need `storage.admin` on it. Worth knowing either way: a failed `gcloud builds submit` doesn't always mean the build failed — check `gcloud builds describe BUILD_ID` before assuming the image wasn't pushed; several of the failures during this troubleshooting were successful builds with only a CLI-side polling or access-check error.

### Workload Identity Federation and GitHub secrets (manual)

```bash
gcloud iam service-accounts create github-deployer --display-name="GitHub Actions Deployer"
SA_EMAIL="github-deployer@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud iam workload-identity-pools create github-pool \
  --location=global --display-name="GitHub Actions Pool"

gcloud iam workload-identity-pools providers create-oidc github-provider \
  --location=global \
  --workload-identity-pool=github-pool \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='YOUR_GITHUB_OWNER/YOUR_REPOSITORY'"

POOL_ID=$(gcloud iam workload-identity-pools describe github-pool \
  --location=global --format='value(name)')

gcloud iam service-accounts add-iam-policy-binding ${SA_EMAIL} \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${POOL_ID}/attribute.repository/YOUR_GITHUB_OWNER/YOUR_REPOSITORY"

WIF_PROVIDER=$(gcloud iam workload-identity-pools providers describe github-provider \
  --location=global --workload-identity-pool=github-pool --format='value(name)')

gh secret set GCP_PROJECT_ID                 --body "${PROJECT_ID}"
gh secret set GCP_WORKLOAD_IDENTITY_PROVIDER --body "${WIF_PROVIDER}"
gh secret set GCP_SERVICE_ACCOUNT            --body "${SA_EMAIL}"
gh secret set CLOUD_SQL_INSTANCE             --body "${PROJECT_ID}:us-central1:any-booking-db"
```

> Secret names must be all caps with underscores only — no spaces, no hyphens.

### GitHub Actions secrets

Written by `setup.sh`, in **GitHub → Settings → Secrets and variables → Actions**:

| Secret | Value |
|---|---|
| `GCP_PROJECT_ID` | Google Cloud project ID |
| `GCP_SERVICE_ACCOUNT` | GitHub deployment service account email |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Full Workload Identity Provider resource name |
| `CLOUD_SQL_INSTANCE` | `PROJECT_ID:us-central1:any-booking-db` |
| `CLOUD_RUN_HOST` | Cloud Run hostname, without `https://` |
| `FIREBASE_ANDROID_APP_ID` | Optional — enables the Android build/distribute job |
| `FIREBASE_TESTER_GROUP` | Optional — defaults to `testers` |
| iOS secrets | Optional — see [iOS app (TestFlight)](#ios-app-testflight) |

Workload Identity Federation is preferred over storing a Google service-account key in GitHub.

## Deploying

### Manually

```bash
./scripts/deploy.sh --project-id YOUR_GCP_PROJECT_ID
```

For a custom Cloud Run hostname, add `--cloud-run-host api.example.com`. To turn on [App Check enforcement](README.md#app-check-api-client-attestation), add `--firebase-project-number` and `--app-check-recaptcha-site-key` — omit both to leave the API open to any client.

The script builds the backend image, deploys it to Cloud Run, runs migrations on container startup, updates the `SITE_URL` secret, builds the root Flutter app against the new API URL, and deploys `build/web` to Firebase Hosting (config in [`firebase.json`](firebase.json)).

### Automatically, via GitHub Actions

The workflow is [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml). Once `setup.sh` has completed and the repository is pushed to GitHub, every push to `main`:

1. Runs Django checks and tests against a fresh Postgres container.
2. Builds the backend image and pushes it to Artifact Registry.
3. Deploys it to Cloud Run (zero-downtime rolling update); migrations run on container startup.
4. Generates Flutter web support, builds the root Flutter app with the deployed API URL, and deploys `build/web` to Firebase Hosting.
5. If `FIREBASE_ANDROID_APP_ID` is set, builds a release APK and distributes it to testers.

```bash
git add .
git commit -m "Configure Google Cloud deployment"
git push origin main
```

### Deploying individual parts

The workflow also runs on `workflow_dispatch` with a `deploy_target` choice — `all`, `api`, `web`, `android`, or `ios` — for deploying just one piece without waiting on (or paying for) the others:

```bash
gh workflow run deploy.yml --repo YOUR_GITHUB_OWNER/YOUR_REPOSITORY -f deploy_target=web
```

(or the **Actions** tab → *Deploy AnyBooking to Google Cloud* → **Run workflow** → pick a target). `api` rebuilds and redeploys the Django backend; `web`/`android`/`ios` each build and ship just that client against the **currently deployed** API URL (fetched read-only via `gcloud run services describe`, without redeploying the backend); `all` does everything, including `ios`. A plain push to `main` always deploys `api` + `web` + `android` and never `ios`.

## Post-deploy steps

After the first successful deploy.

**1. Get the deployed URL:**

```bash
FULL_URL=$(gcloud run services describe any-booking \
  --region=us-central1 \
  --format='value(status.url)')
echo "$FULL_URL"
```

**2. Allow public access** (Cloud Run blocks unauthenticated requests by default):

```bash
gcloud run services add-iam-policy-binding any-booking \
  --region=us-central1 \
  --member="allUsers" \
  --role="roles/run.invoker"
```

**3. Update the `CLOUD_RUN_HOST` GitHub secret** so `ALLOWED_HOSTS` is set to the real hostname (not `*`), then push a commit or re-run the workflow:

```bash
gh secret set CLOUD_RUN_HOST --body "${FULL_URL#https://}"
```

**4. Update `SITE_URL`** (used to build links in outgoing emails; `scripts/deploy.sh` does this for you):

```bash
printf '%s' "$FULL_URL" | gcloud secrets versions add SITE_URL --data-file=-
```

**5. Create the admin superuser** with [`backend/create_admin.sh`](backend/create_admin.sh):

```bash
./backend/create_admin.sh \
  --project-id YOUR_GCP_PROJECT_ID \
  --username admin \
  --email admin@example.com \
  --password 'CHOOSE_A_STRONG_PASSWORD'
```

It runs a one-off Cloud Run job against the latest deployed image, then deletes the job. Safe to re-run — pass `--reset` to change the password of an existing user:

```bash
./backend/create_admin.sh \
  --project-id YOUR_GCP_PROJECT_ID \
  --username admin \
  --password 'NEW_PASSWORD' \
  --reset
```

**6. Seed data** — one-off commands run as Cloud Run Jobs. First get the latest image (set once per session):

```bash
IMAGE=$(gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/${PROJECT_ID}/any-booking-repo/any-booking \
  --sort-by="~CREATE_TIME" --limit=1 \
  --format="value(IMAGE,DIGEST)" | awk '{print $1"@"$2}')
```

*Import banquet hall data from Excel.* The file must be reachable from the container, so upload it to Cloud Storage first:

```bash
# Create the bucket (once)
gsutil mb -l us-central1 gs://${PROJECT_ID}-uploads

# Grant the Cloud Run runtime service account read access
PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format='value(projectNumber)')
gsutil iam ch \
  serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com:objectViewer \
  gs://${PROJECT_ID}-uploads

# Upload the file
gsutil cp halls.xlsx gs://${PROJECT_ID}-uploads/halls.xlsx

gcloud run jobs create import-halls \
  --image="$IMAGE" \
  --region=us-central1 \
  --set-cloudsql-instances="${PROJECT_ID}:us-central1:any-booking-db" \
  --set-secrets="DATABASE_URL=DATABASE_URL:latest,SECRET_KEY=DJANGO_SECRET_KEY:latest" \
  --command="bash" \
  --args="-c,python -c \"from google.cloud import storage; storage.Client().bucket('${PROJECT_ID}-uploads').blob('halls.xlsx').download_to_filename('/tmp/halls.xlsx')\" && python manage.py import_halls /tmp/halls.xlsx" \
  --execute-now
```

*Seed sample data for all categories and international locations (optional):*

```bash
gcloud run jobs create seed-sample-data \
  --image="$IMAGE" \
  --region=us-central1 \
  --set-cloudsql-instances="${PROJECT_ID}:us-central1:any-booking-db" \
  --set-secrets="DATABASE_URL=DATABASE_URL:latest,SECRET_KEY=DJANGO_SECRET_KEY:latest" \
  --command="python" \
  --args="manage.py,seed_sample_data" \
  --execute-now
```

> If a job already exists, delete it first with `gcloud run jobs delete JOB_NAME --region=us-central1 --quiet` and recreate it, or re-execute it unchanged with `gcloud run jobs execute JOB_NAME --region=us-central1`.

### Connecting to the production database locally

```bash
brew install libpq
echo 'export PATH="/opt/homebrew/opt/libpq/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc
gcloud auth application-default login

gcloud sql connect any-booking-db --user=anybooking_user --database=anybooking
```

Type `\q` to exit the psql prompt.

## Firebase Hosting and custom domains

`setup.sh` links Firebase to the existing GCP project — this does not create a separate project. To do it by hand:

```bash
firebase projects:addfirebase YOUR_PROJECT_ID
```

That provisions a default Hosting site at `https://YOUR_PROJECT_ID.web.app` and `https://YOUR_PROJECT_ID.firebaseapp.com`, both on HTTPS with a Google-managed certificate — no bucket, load balancer or certificate provisioning needed.

`firebase.json` at the repository root configures the deploy (`"public": "build/web"`, with a catch-all rewrite to `index.html` for client-side routing):

```bash
flutter build web --release --dart-define=API_BASE_URL=https://YOUR_CLOUD_RUN_URL/api
firebase deploy --only hosting --project YOUR_PROJECT_ID
```

### Adding a custom domain

1. [Firebase console](https://console.firebase.google.com) → your project → **Build → Hosting → Add custom domain**
2. Enter the domain and add the **TXT** record it gives you at your DNS registrar to verify ownership
3. Once verified, add the **A** records (or **CNAME** for a subdomain) Firebase provides
4. Firebase provisions and auto-renews a managed SSL certificate — this can take a few minutes up to 24 hours after DNS propagates

Domain verification is console-only (it requires proving DNS ownership interactively), so it can't be scripted into `setup.sh` or `deploy.sh`.

## Android app (Firebase App Distribution)

Off by default — the `android` job in [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) builds a release APK on every push to `main` and distributes it to testers, but is a no-op until `FIREBASE_ANDROID_APP_ID` is set. One-time registration with [`scripts/register_android.sh`](scripts/register_android.sh):

```bash
./scripts/register_android.sh \
  --project-id YOUR_GCP_PROJECT_ID \
  --package-name com.yourcompany.app \
  --github-repo YOUR_GITHUB_OWNER/YOUR_REPOSITORY
```

It generates the `android/` platform if missing, sets the `applicationId`, registers the app with Firebase, creates a `testers` group, and (with `--github-repo`) writes the `FIREBASE_ANDROID_APP_ID` and `FIREBASE_TESTER_GROUP` GitHub secrets. Safe to re-run. Add testers afterward with:

```bash
firebase appdistribution:testers:add someone@example.com --group-alias testers --project YOUR_GCP_PROJECT_ID
```

To register by hand instead:

```bash
firebase apps:create android --package-name com.yourcompany.any_booking --project YOUR_PROJECT_ID
firebase appdistribution:group:create "Testers" testers --project YOUR_PROJECT_ID
```

`apps:create` prints the app's **App ID** (format `1:PROJECT_NUMBER:android:HEX`), also visible at **Firebase console → Project settings → Your apps**. It is the same Android app registration [App Check](README.md#app-check-api-client-attestation) needs for the Play Integrity provider, so register once and reuse the App ID for both.

The release APK is signed with Flutter's default debug keystore — fine for internal tester distribution, but **not suitable for the Play Store**, which needs a real upload keystore. See [Android app (Firebase App Distribution)](README.md#android-app-firebase-app-distribution) in the README for what the CI job builds.

## iOS app (TestFlight)

Optional. Enabled by these GitHub secrets:

```text
IOS_DIST_CERTIFICATE_BASE64        IOS_DIST_CERTIFICATE_PASSWORD
IOS_PROVISIONING_PROFILE_BASE64    IOS_PROVISIONING_PROFILE_NAME
IOS_KEYCHAIN_PASSWORD              APPSTORE_TEAM_ID
APPSTORE_API_KEY_ID                APPSTORE_API_ISSUER_ID
APPSTORE_API_PRIVATE_KEY
```

Unlike Android, creating the certificate, profile and API key is manual in Apple's portals — follow the [One-time setup](README.md#one-time-setup-1) steps under iOS app (TestFlight) in the README first. Once you have the `.p8` API key, the `.p12` distribution certificate and the `.mobileprovision` profile downloaded, [`scripts/set_ios_secrets.sh`](scripts/set_ios_secrets.sh) reads them plus your Team ID / Key ID / Issuer ID from a local JSON file and writes all nine secrets with `gh secret set`. It never prints secret values.

**Prerequisites:**

- `gh` authenticated (`gh auth login`) with write access to the repo
- `python3` on `PATH`
- The three downloaded files saved locally — this repo's `.gitignore` excludes `.private/`, so that's a safe place to keep them
- A JSON credentials file — copy [`.private/credentials.example.json`](.private/credentials.example.json) to `.private/credentials` and fill it in:

  ```json
  {
    "teamId": "YOUR_APPLE_TEAM_ID",
    "appstoreApiKeyId": "YOUR_API_KEY_ID",
    "appstoreApiIssuerId": "YOUR_API_ISSUER_ID",
    "appstoreApiPrivateKeyFile": ".private/AuthKey_YOUR_KEY_ID.p8",
    "distributionCertificateFile": ".private/dist_cert.p12",
    "distributionCertificatePassword": "PASSWORD_YOU_SET_WHEN_EXPORTING_THE_P12",
    "provisioningProfileFile": ".private/your_profile.mobileprovision",
    "provisioningProfileName": "EXACT_PROFILE_NAME_FROM_APPLE_DEVELOPER_PORTAL",
    "keychainPassword": ""
  }
  ```

  Leave `keychainPassword` empty to have the script generate a throwaway one — it only protects the temporary keychain created inside a single CI run and is never reused.

Then run:

```bash
./scripts/set_ios_secrets.sh --github-repo YOUR_GITHUB_OWNER/YOUR_REPOSITORY
```

The `ios` job runs on `macos-latest`, which GitHub bills at 10x the Linux per-minute rate on private repos, so it is opt-in on every run. It is skipped on ordinary pushes to `main`, and on a manual `workflow_dispatch` it only runs if `deploy_target` is `all` or `ios`:

```bash
gh workflow run deploy.yml --repo YOUR_GITHUB_OWNER/YOUR_REPOSITORY -f deploy_target=ios
```

See [iOS app (TestFlight)](README.md#ios-app-testflight) in the README for details.

## Infrastructure lifecycle

### Pause / resume the database

Cloud Run scales to zero when idle, but Cloud SQL bills continuously while running. Stop it during periods of no traffic, and start it before the next deploy or when traffic resumes:

```bash
./scripts/stop.sh --project-id YOUR_GCP_PROJECT_ID
./scripts/start.sh --project-id YOUR_GCP_PROJECT_ID   # waits until RUNNABLE
```

### Tear down

[`scripts/teardown.sh`](scripts/teardown.sh) removes the Cloud Run service, Artifact Registry repository, Workload Identity Federation pool, GitHub deployer service account, and Secret Manager secrets created by `setup.sh`:

```bash
./scripts/teardown.sh --project-id YOUR_GCP_PROJECT_ID
```

It prompts for the project ID as confirmation before deleting anything (skip with `--yes`). The Cloud SQL instance and media bucket hold real data and are **left in place** unless you pass `--delete-database` and/or `--delete-media-bucket`. Firebase Hosting costs nothing while idle and is left running unless you pass `--disable-hosting`. Pass `--github-repo OWNER/REPO` to also remove the GitHub Actions secrets `setup.sh` wrote.

<details>
<summary>Manual teardown (irreversible — all Cloud SQL data is lost)</summary>

```bash
# 1. Cloud Run service and jobs
gcloud run services delete any-booking --region=us-central1 --quiet
gcloud run jobs delete import-halls     --region=us-central1 --quiet 2>/dev/null || true
gcloud run jobs delete seed-sample-data --region=us-central1 --quiet 2>/dev/null || true

# 2. Cloud SQL instance (drops all databases and users inside it)
gcloud sql instances delete any-booking-db --quiet

# 3. Secret Manager secrets
for secret in \
  DJANGO_SECRET_KEY DATABASE_URL \
  RAZORPAY_KEY_ID RAZORPAY_KEY_SECRET \
  EMAIL_HOST EMAIL_HOST_USER EMAIL_HOST_PASSWORD \
  DEFAULT_FROM_EMAIL ADMIN_NOTIFY_EMAIL SITE_URL EMAIL_BACKEND GCS_MEDIA_BUCKET; do
  gcloud secrets delete "$secret" --quiet 2>/dev/null || true
done

# 4. Artifact Registry images, then the repository
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/YOUR_PROJECT_ID/any-booking-repo \
  --format="value(IMAGE)" \
  | xargs -I{} gcloud artifacts docker images delete {} --quiet 2>/dev/null || true
gcloud artifacts repositories delete any-booking-repo --location=us-central1 --quiet

# 5. Workload Identity provider and pool, then the service account
gcloud iam workload-identity-pools providers delete github-provider \
  --location=global --workload-identity-pool=github-pool --quiet
gcloud iam workload-identity-pools delete github-pool --location=global --quiet
gcloud iam service-accounts delete "github-deployer@YOUR_PROJECT_ID.iam.gserviceaccount.com" --quiet
```

To tear down only the app while keeping infrastructure for a redeploy, run step 1 only.

</details>

## Local development

### Backend (Django)

Requires Python 3.11+ and PostgreSQL 14+ (tests should always run against real PostgreSQL). Run from `backend/`.

```bash
cd backend
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your values:

```
DEBUG=True
SECRET_KEY=<generate a strong key>
DATABASE_URL=postgres://<user>:<password>@localhost:5432/anybooking
ALLOWED_HOSTS=localhost,127.0.0.1

# Razorpay — only required if India payments are enabled in Admin → Payment Gateway Configs
RAZORPAY_KEY_ID=<your Razorpay key>
RAZORPAY_KEY_SECRET=<your Razorpay secret>
```

Then:

```bash
createdb anybooking
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

Optional data loading:

```bash
# Import banquet hall data from Excel
python manage.py import_halls "/path/to/Banquet Halls.xlsx"
python manage.py import_halls "path/to/file.xlsx" --clear    # re-import cleanly

# Seed USA/Canada/UAE locations and ~37 sample services (+ 16 admin log entries)
python manage.py seed_sample_data

# Production static files
python manage.py collectstatic
```

`import_halls` creates the India → Telangana → Districts → Cities hierarchy, all 7 service categories (if not yet added), attribute definitions (AC Hall, Non-AC, Capacity, Rooms), a country-level RegionalCategoryConfig for India/Banquet Hall, and imports every hall as a Service with attribute values.

| URL | Description |
|---|---|
| http://127.0.0.1:8000/ | Public site |
| http://127.0.0.1:8000/admin/ | Admin portal |
| http://127.0.0.1:8000/admin/dashboard/ | Admin dashboard |
| http://127.0.0.1:8000/vendor/login/ | Vendor portal login |

### Flutter web app

From the repository root, against the local backend:

```bash
flutter run -d web-server \
  --web-hostname 127.0.0.1 \
  --web-port 8080 \
  --dart-define=API_BASE_URL=http://127.0.0.1:8000/api
```

---

## Admin Dashboard

The dashboard is accessible at `/admin/dashboard/` and is also linked from the **📊 Dashboard** button in the top-right corner of every admin page.

### What it shows

| Section | Details |
|---|---|
| **Stat cards** | Total / Confirmed / Completed / Cancelled bookings; Total order value; Advance collected; Balance outstanding; Payments captured (Razorpay); Refunded amount; Active services |
| **Bookings trend** | Line chart — daily count for the last 30 days |
| **Revenue trend** | Bar chart — total value vs advance collected per month (last 6 months) |
| **Status doughnut** | Pending / Confirmed / Completed / Cancelled breakdown |
| **Top services** | Ranked by booking count with confirmed count |
| **Upcoming events** | Next 10 confirmed bookings sorted by event date |
| **Recent bookings** | Last 15 bookings with status badges and amounts |
| **Audit log** | Last 20 admin actions (Added / Changed / Deleted) with user, object, and timestamp |

### Location scoping
Superusers see all data across all regions. Staff users with a **StaffProfile** see only data for their assigned country, state, or city. The active scope is shown as a badge ("📍 Telangana, India") in the dashboard header.

---

## Location-Scoped Staff

Admin users can be restricted to a specific country, state, or city. Scoping is enforced across Services, Vendors, Bookings, Blocked Dates, Payments, and the Dashboard.

### Access levels

| User type | Access |
|---|---|
| **Superuser** | All data, all admin sections (Users, Groups, Staff Profiles) |
| **Staff — City scope** | Only records for that city |
| **Staff — State scope** | Only records for any city in that state |
| **Staff — Country scope** | Only records for any city in that country |
| **Staff — no profile** | Nothing (fail-safe: empty querysets) |

Non-superuser staff cannot see the Users or Groups sections of the admin.

### Creating a location-scoped staff user

1. Go to **Admin → Users → Add User**, set `is_staff = True`
2. Go to **Admin → Staff Profiles → Add**
3. Select the User and set `Country`, `State`, or `City` — most specific wins
4. Save — the user can now log in and will see only their region's data

### Creating a test staff user (local dev)
```python
python manage.py shell -c "
from django.contrib.auth.models import User
from services.models import StaffProfile, Country, State

u = User.objects.create_user('staff_tg', password='testpass123', is_staff=True)
state = State.objects.get(name='Telangana')
country = Country.objects.get(name='India')
StaffProfile.objects.create(user=u, country=country, state=state)
print('Created:', u.username)
"
```

---

## Vendor Portal

Vendors log in at `/vendor/login/` and see only their own listings and bookings — no admin access required.

### Access levels

| User type | Access |
|---|---|
| **Superuser / Staff** | Full Django admin (`/admin/`) |
| **Vendor user** | Vendor portal only (`/vendor/`) — own listings and bookings |

### Creating a vendor login account

**From the admin (recommended):**

1. Go to **Admin → Vendors → [vendor name]**
2. Scroll to the **Portal Access** fieldset — click **Create login account for this vendor**
3. Enter a username and password, click **Create account**
4. The new user is automatically linked to the vendor and added to the **Vendor** Django group

**Manually:**

1. Go to **Admin → Users → Add User**, set a username and password
2. Under **Groups**, add the user to the **Vendor** group (`is_staff` and `is_superuser` must remain unticked)
3. Go to **Admin → Vendors → [vendor name]**, set the **User** field to the new user, save

### What vendor users can see

| Page | URL | Contents |
|---|---|---|
| Dashboard | `/vendor/dashboard/` | Stat cards (total/pending/confirmed/completed bookings), active listings, recent bookings |
| Bookings | `/vendor/bookings/` | All bookings for their services; filterable by service and status |

Vendors cannot see other vendors' data, access the Django admin, or modify any records — the portal is read-only.

### No extra environment variables

The vendor portal requires no additional secrets or environment variables. It uses the same Django session auth as the admin.

---

## Category Management

All 7 service categories are pre-defined. Each can be enabled or disabled independently from **Admin → Categories**.

### Enabling / disabling a category

1. Go to **Admin → Categories**
2. Tick or untick the **Is Active** checkbox in the list (inline-editable)
3. Click **Save** — the change takes effect immediately on the public site

Disabled categories are hidden from:
- The navbar
- The Browse by Category section on the home page
- The category sidebar on the service list page
- Category detail URLs (returns 404)

By default, only **Banquet Hall** is active. Enable additional categories as the business expands to them.

### Adding attributes for a category

Go to **Admin → Attribute Definitions → Add**:

| Category | Example attributes |
|---|---|
| Banquet Hall | AC Hall, Non-AC Hall, Venue Capacity, Lunch Capacity, AC Rooms, Non-AC Rooms |
| Hotels | AC Rooms, Non-AC Rooms, Swimming Pool, Gym, Restaurant |
| Catering | Veg, Non-Veg, Jain Food, Min Guests, Price Per Plate |
| Music Band | Genre, No. of Artists, Sound Equipment |
| Dancing | Style, Group/Solo, Duration |
| Priests | Religion, Ceremony Type, Language |
| Event Management | Wedding, Corporate, Birthday, Decoration, Photography |

---

## Adding a New Country/Region

1. Go to **Admin → Countries → Add Country** (set name, ISO code, currency symbol, phone code)
2. Add **States** under that country
3. Add **Districts** and **Cities** under each state
4. Go to **Admin → Regional Category Configs → Add**
   - Pick the Category (e.g. Banquet Hall) and Country (and optionally a State for a state-level override)
   - Tick the **Enabled Attributes** that apply in that region
   - Set a local **Price Unit Label** (e.g. "per night", "per plate")
   - Optionally set a **Local Display Name** if the category is known by a different name in that region

State-level configs override country-level configs automatically.

---

## How Regional Label Overrides Work

Category names and attribute labels can be customised per country or state so users always see terminology natural to their region — for example **"Priests"** becomes **"Purohit"** in Telangana or **"Archakar"** in Tamil Nadu.

### Priority order
```
State-level label  →  Country-level label  →  Default English name
```
The most specific match always wins.

### What can be overridden

| What | Model | Scope |
|---|---|---|
| Category display name | `RegionalCategoryConfig.local_display_name` | Country or State |
| Category description | `RegionalCategoryConfig.local_description` | Country or State |
| Attribute label | `AttributeLocalName.local_name` | Country or State |
| Price unit label | `RegionalCategoryConfig.price_unit_label` | Country or State |
| Which attributes are shown | `RegionalCategoryConfig.enabled_attributes` | Country or State |

### Where the label appears automatically
Once configured, the local name shows throughout the UI whenever the user has that region selected:
- Navbar category links
- Home page category cards
- List page heading, breadcrumb, and sidebar category links
- Service card category badge
- Service detail page breadcrumb and category badge
- Feature/attribute labels inside service cards and detail pages

### Setting a category label override

1. Go to **Admin → Regional Category Configs → Add**
2. Set **Category**, **Country**, and optionally **State**
3. Fill in **Local Display Name** and optionally **Local Description**
4. Save — takes effect immediately

| Region | Category | Local Name |
|---|---|---|
| India (default) | Priests | Pandit / Priest |
| Telangana | Priests | Purohit |
| Tamil Nadu | Priests | Archakar |
| Punjab | Priests | Granthi |

### Setting an attribute label override

1. Go to **Admin → Attribute Definitions → select the attribute**
2. Scroll to the **Attribute Local Names** inline section
3. Add a row: Country + optional State + Local Name
4. Save

---

## Location Preference (Public Site)

On first visit, users see a modal to set their preferred country and state. The preference is saved in cookies (`ab_country`, `ab_state`) for one year and is used to:
- Pre-filter the service list
- Pre-populate location dropdowns
- Show location-filtered counts on category cards
- Display the current location in the navbar ("📍 Telangana, India")

Users can change their location at any time via the **Change** link in the navbar. The modal also offers **Auto-detect** which uses the IP geolocation API (`ipapi.co`) to suggest a matching country and state from the database.

---

## Service Ratings & Review Moderation

All customer reviews are held in a **pending** state until an admin approves or rejects them. No review is visible on the public site until explicitly approved.

### Moderation workflow

1. Go to **Admin → Reviews → Reviews**
2. Use the **Status** filter in the right sidebar to show `Pending` reviews
3. Select one or more reviews
4. Choose an action from the dropdown:
   - **Approve selected reviews** — makes them visible immediately on the service detail page and updates the average star rating on listing cards
   - **Reject selected reviews** — hides them permanently; the record is kept for audit purposes
5. Click **Go**

Review content (reviewer name, rating, body, submission date) is read-only — it cannot be edited from the admin. Only the status can be changed.

### No environment variables required

Review moderation is fully configuration-driven. No `.env` changes needed.

---

## Photo / Image Management

### Service listing photos

Each service can have multiple photos. The first one marked **Primary** is used as the card thumbnail on the listing page.

1. Go to **Admin → Services → [service name]**
2. Scroll to the **Images** inline section at the bottom
3. Click **Add another Image**, upload a file, and tick **Is Primary** for the main photo
4. Add more rows for additional photos — drag to reorder by **Order** field
5. Save

Images appear in the photo gallery on the service detail page. The primary image is also shown on listing cards.

### Category tiles (home page)

1. Go to **Admin → Categories → [category name]**
2. Upload an image to the **Image** field
3. Save — the image appears in the "Browse by Category" grid on the home page

If no image is set, the tile falls back to the category's Bootstrap icon on a coloured background.

### Featured city cards (home page)

1. Go to **Admin → Cities → [city name]**
2. Upload an image to the **Image** field
3. Tick **Is Featured** so the city appears in the "Explore Cities" row on the home page
4. Save

Up to 6 featured cities are shown.

### Production note — images on Cloud Run

Cloud Run containers have no persistent disk. Media files are automatically stored in Google Cloud Storage (`gs://${PROJECT_ID}-media`) via `django-storages`. The `GCS_MEDIA_BUCKET` secret is mounted on every deploy — no extra setup needed.

If setting up a new environment, create the bucket and grant access once:

```bash
gsutil mb -l us-central1 gs://${PROJECT_ID}-media

PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format='value(projectNumber)')
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

printf '%s' "${PROJECT_ID}-media" | gcloud secrets create GCS_MEDIA_BUCKET --data-file=-
```

---

## Admin Bulk Actions

### Services (Admin → Services)
| Action | Effect |
|---|---|
| ⭐ Mark selected as Featured | Sets `is_featured = True` |
| Remove Featured | Sets `is_featured = False` |
| ✅ Activate | Sets `is_active = True` |
| 🚫 Deactivate | Sets `is_active = False` |

### Reviews (Admin → Reviews)
| Action | Effect |
|---|---|
| ✅ Approve selected reviews | Sets status → Approved; review appears publicly |
| ❌ Reject selected reviews | Sets status → Rejected; review hidden permanently |

### Bookings (Admin → Bookings)
| Action | Effect |
|---|---|
| ✅ Approve & notify customer | Status → Confirmed; sends approval email to customer |
| ❌ Cancel with refund & notify customer | Opens refund form; status → Cancelled; sends cancellation email |
| 🏁 Mark as Completed | Status → Completed (Confirmed only) |

### Blocked Dates (Admin → Blocked Dates)
| Action | Effect |
|---|---|
| 🗑 Remove selected blocked dates | Deletes the selected blocked date records |

---

## Email Workflow

### How it works

All transactional emails are sent via Django's email backend. In development they print to the console; in production configure SMTP via environment variables.

Every email sent (or failed) is recorded in the **EmailLog** table and viewable at **Admin → Bookings → Email Logs**.

### Email triggers

| Event | Recipient(s) | Template |
|---|---|---|
| Customer submits booking | Customer | `booking_received.html` |
| Customer submits booking | Super-admin + area admins | `admin_notify.html` |
| Admin approves booking | Customer | `booking_approved.html` |
| Admin cancels booking | Customer | `booking_cancelled.html` |

**Area admin resolution:** when a booking arrives, the system queries `StaffProfile` records whose city, state, or country scope covers the booking's location and emails every matching staff user.

### Cancel with Refund workflow

1. In **Admin → Bookings**, select one or more bookings
2. Choose **❌ Cancel with refund & notify customer** from the Actions dropdown
3. An intermediate form appears — fill in:
   - **Refund Type**: Full Refund / Partial Refund / No Refund
   - **Refund Amount** (if Partial): the exact amount to be returned
   - **Cancellation Reason**: shown verbatim to the customer in the email
   - **Internal Notes**: optional, admin-only, not sent to the customer
4. Click **Cancel Bookings & Send Emails** — bookings are cancelled and emails fire immediately

### Email Logs

Go to **Admin → Bookings → Email Logs** to see every email sent, with:
- Type badge (colour-coded: blue = received, amber = admin notify, green = approved, red = cancelled)
- Recipient address and linked booking
- Subject line and full HTML body preview
- Sent / Failed status
- Timestamp and which admin triggered it (system = auto-sent on booking creation)

The **Booking change view** also shows a compact email history table under the collapsible *Email Communications* section.

### Local development

In development (`EMAIL_BACKEND=console`) emails are printed to the terminal — no SMTP setup needed. To test real delivery locally, use [Mailpit](https://mailpit.axllent.org/) or a Gmail App Password:

```bash
# .env additions for local SMTP testing
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your@gmail.com
EMAIL_HOST_PASSWORD=xxxx-xxxx-xxxx-xxxx   # Gmail App Password
DEFAULT_FROM_EMAIL=AnyBooking <noreply@anybooking.in>
ADMIN_NOTIFY_EMAIL=your@gmail.com
SITE_URL=http://127.0.0.1:8000
```

### Production (Google Secret Manager)

Store each email setting as a separate secret (see [Secrets](#secrets-google-secret-manager)) and mount them as environment variables in your Cloud Run service. The `EMAIL_BACKEND` secret should be set to:
```
django.core.mail.backends.smtp.EmailBackend
```

All email secrets are auto-mounted on every deploy via the CI/CD pipeline — no manual `gcloud run services update` step needed.

---

## Payment Gateway

Online payments are **feature-flagged per country** via `PaymentGatewayConfig`. When a country has `is_enabled=False` (the default), bookings skip payment entirely. When enabled, customers are redirected to the configured gateway immediately after booking submission.

### Enabling payments for India (Razorpay)

#### 1. Add API credentials to `.env` (local) or Secret Manager (production)

**Local `.env`:**
```
RAZORPAY_KEY_ID=rzp_test_XXXXXXXXXXXX
RAZORPAY_KEY_SECRET=your_razorpay_secret
```

**Production — store in Secret Manager and mount on Cloud Run:**
```bash
echo -n "rzp_live_XXXXXXXXXXXX" | gcloud secrets create RAZORPAY_KEY_ID --data-file=-
echo -n "your_live_secret"      | gcloud secrets create RAZORPAY_KEY_SECRET --data-file=-

gcloud run services update any-booking \
  --region=us-central1 \
  --update-secrets=\
RAZORPAY_KEY_ID=RAZORPAY_KEY_ID:latest,\
RAZORPAY_KEY_SECRET=RAZORPAY_KEY_SECRET:latest
```

Get your keys from the [Razorpay Dashboard → Settings → API Keys](https://dashboard.razorpay.com/app/website-app-settings/api-keys). Use **Test** keys for dev, **Live** keys for production.

#### 2. Enable the gateway in Admin

1. Go to **Admin → Payment Gateway Configs → Add**
2. Select **Country: India**, **Gateway: Razorpay**, tick **Is Enabled**
3. Optionally set a **Display Name** (e.g. "Pay Online")
4. Save — bookings for services in Indian cities now redirect to Razorpay checkout

#### 3. Configure the Razorpay webhook (production)

In your Razorpay Dashboard → Webhooks, add:
```
https://your-domain.com/payments/callback/
```
Events: `payment.captured`, `payment.failed`. The callback endpoint uses HMAC-SHA256 to verify every payload.

### How the gateway selection works

```
booking_create  →  get_gateway_for_country(country)
                        ├── No PaymentGatewayConfig? → skip payment
                        ├── is_enabled=False?        → skip payment
                        └── is_enabled=True          → redirect to initiate_payment
                                                          └── gateway.create_order()
                                                          └── render checkout_<slug>.html
payment_callback  →  match gateway from POST data → gateway.verify_callback()
                        ├── valid   → Payment.status = captured → Booking.status = confirmed
                        └── invalid → Payment.status = failed → show failed.html
```

### Adding a new gateway (e.g. Stripe for UK)

1. Create `payments/gateways/stripe_gateway.py` implementing `BasePaymentGateway`:
   - `create_order(booking)` → create a Stripe PaymentIntent, return `{order_id, amount, currency}`
   - `verify_callback(post_data)` → verify Stripe webhook signature
   - `get_checkout_context(booking, payment)` → return vars needed by the template
   - `extract_order_id(post_data)` → pull the intent ID from POST data
2. Register it in `payments/gateways/registry.py`:
   ```python
   from .stripe_gateway import StripeGateway
   GATEWAY_REGISTRY['stripe'] = StripeGateway
   ```
3. Create `templates/payments/checkout_stripe.html`
4. Store `STRIPE_PUBLISHABLE_KEY` / `STRIPE_SECRET_KEY` in `.env` / Secret Manager
5. In Admin → Payment Gateway Configs, add a row for UK with gateway=Stripe, `is_enabled=True`

No changes to `bookings/views.py` or `payments/views.py` are needed.

---

## Terms of Use

Terms of Use are **feature-flagged per document** via the `is_active` field. When no active terms apply to a service, the booking form shows no acceptance step and nothing changes for the customer.

### Creating terms

1. Go to **Admin → Terms of Use → Add**
2. Fill in **Title**, **Version** (e.g. `v1.0` or `2024-01`), and **Content** (HTML supported)
3. Set **Scope**:
   - **Site-wide** — shown on every booking regardless of service
   - **Service-specific** — select a specific service; shown only for bookings of that service
4. Tick **Is Active**
5. Save — the terms box appears on the booking form immediately

Multiple active terms (site-wide + service-specific) stack: all are shown together, with one combined checkbox.

### Updating terms

Create a **new** `TermsOfUse` record with a new version string rather than editing the existing one. Deactivate the old record by unticking `Is Active`. This preserves the original text for all historical acceptances.

### Viewing acceptance records

| Location | What you see |
|---|---|
| **Admin → Terms → Terms Acceptances** | All acceptances across all bookings; searchable by customer name, email, IP address; filterable by terms document and date |
| **Admin → Bookings → [booking detail]** | Terms Acceptances inline — shows which documents were accepted for that booking, the version, IP, and timestamp |
| **Admin → Terms of Use → [terms detail]** | Acceptances inline — shows every booking that accepted this specific document |

Each acceptance record captures:
- The exact version string at the moment of signing (snapshot)
- Customer IP address (handles `X-Forwarded-For` proxy headers)
- User agent string
- Timestamp (UTC)

Acceptance records are **immutable** — they cannot be edited or deleted via the admin. Terms documents that have existing acceptances are also protected from deletion.

### Disabling terms

Untick **Is Active** on the terms document. Existing acceptance records are preserved. The booking form immediately stops showing that document.

### No environment variables required

Terms of Use is fully configuration-driven via the admin. No `.env` changes, no secrets, no deploy needed.

---

## Booking Lookup & Confirmation Numbers

### How confirmation numbers work

Every booking gets a unique `AB-XXXXXXXX` code on creation (8 random unambiguous characters). It is:
- Shown prominently on the post-booking confirmation page
- Included in the subject line and body of all transactional emails
- Searchable in the admin (Admin → Bookings search box)

No setup is required — confirmation numbers are generated automatically.

### Find My Booking page (`/bookings/find/`)

Accessible from the navbar. Customers can search by:
- **Confirmation number** — the `AB-XXXXXXXX` code from their email
- **Last name + phone number** — both fields required; partial match on each

Only **pending** and **confirmed** bookings are returned. Cancelled and completed bookings are intentionally excluded.

No configuration needed. The page is always live.

---

## Customer Cancellation Requests

### Workflow overview

```
Customer finds booking (/bookings/find/)
  └── Clicks "Request Cancellation"
        └── Submits reason (/bookings/cancel-request/<conf_num>/)
              ├── Customer receives acknowledgement email
              ├── Admin(s) receive alert email with "Review in Admin" button
              └── Booking flagged: cancellation_requested = True

Admin reviews:
  └── Admin → Bookings → filter "Cancellation Requested = Yes"
        └── Selects booking → "❌ Cancel with refund & notify customer" action
              └── Fills refund form → booking cancelled → customer notified
```

### Admin actions

| Location | What to do |
|---|---|
| **Admin → Bookings list** | Filter by **Cancellation Requested = Yes** to see all pending requests; look for the **⚠ Requested** amber badge |
| **Booking detail** | Expand **Customer Cancellation Request** fieldset to read the reason and timestamp |
| **Booking list** | Select the booking → **❌ Cancel with refund & notify customer** → fill in refund details and confirm |

### Notes

- Customers can only submit one request per booking — the form blocks duplicates
- The cancellation request does **not** automatically cancel the booking; admin controls the refund decision
- All emails (customer acknowledgement + admin alert) are recorded in Email Logs
- No environment variables or configuration required beyond the SMTP settings already in place

---

## Vendor Booking Notifications

Vendor email notifications are **off by default** and require no code changes or environment variables to enable. They are controlled entirely from the admin.

### Enabling for a vendor

1. Go to **Admin → Vendors → [vendor name]**
2. Set the **Email** field to the vendor's email address (if not already set)
3. Tick **Notify on Booking** under the *Booking Notifications* fieldset
4. Save

You can also bulk-toggle the flag from the **Admin → Vendors list** — `Notify on Booking` is an inline-editable column.

### What triggers a vendor email

| Trigger | Email sent |
|---|---|
| Admin runs **✅ Approve & notify customer** | Vendor receives booking confirmation with full customer details |
| Admin runs **❌ Cancel with refund & notify customer** | Vendor receives cancellation notice with the reason and freed date |

The vendor email fires **in addition to** the customer email — both are sent in the same admin action. No extra steps required.

### Guard conditions

A vendor email is only sent when **both** conditions are true:
- `Vendor.notify_on_booking = True`
- `Vendor.email` is a non-empty valid address

If either is missing the send is silently skipped and no EmailLog entry is created for the vendor.

### Viewing vendor emails in the audit log

Go to **Admin → Bookings → Email Logs** and filter by type:
- **Booking Confirmed (vendor)** — green badge
- **Booking Cancelled (vendor)** — rose badge

Both are linked to the relevant booking and show the full rendered email body.
