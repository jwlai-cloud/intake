#!/usr/bin/env bash
# Deploy the agent service to Cloud Run. Run from the repo root.
set -euo pipefail

PROJECT="${GOOGLE_CLOUD_PROJECT:?set GOOGLE_CLOUD_PROJECT}"
REGION="${CLOUD_RUN_REGION:-us-central1}"
SERVICE="${CLOUD_RUN_SERVICE:-intake-agent}"

# The build context needs both the package and the templates directory, so it is
# staged rather than built straight from backend/.
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp -r backend/intake_agent backend/Dockerfile backend/requirements.txt backend/.dockerignore "$STAGE/"
cp -r templates "$STAGE/templates"

gcloud run deploy "$SERVICE" \
  --source "$STAGE" \
  --project "$PROJECT" \
  --region "$REGION" \
  --set-env-vars "^@^GOOGLE_GENAI_USE_VERTEXAI=TRUE@GOOGLE_CLOUD_PROJECT=$PROJECT@GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION:-global}@GEMINI_MODEL=${GEMINI_MODEL:-gemini-3.6-flash}@FIRESTORE_DATABASE=${FIRESTORE_DATABASE:-(default)}@INTAKE_ALLOWED_ORIGINS=${INTAKE_ALLOWED_ORIGINS:-http://localhost:5173}" \
  --set-secrets "INTAKE_API_KEY=intake-api-key:latest" \
  --allow-unauthenticated

# --allow-unauthenticated, gated at the application layer by X-Intake-Key.
# Cloud Run IAM would be stronger, but the client is a browser: it cannot mint a
# Google identity token without a signed-in Google user, and this product
# deliberately has no user accounts.
#
# Be clear-eyed about what that buys. The key ships inside the built JS bundle,
# so it stops drive-by traffic and nothing more. Two things carry the real
# weight: a hard spend cap on the project, and taking the service down when it
# is not being demonstrated.
#
#   gcloud run services delete "$SERVICE" --region "$REGION" --project "$PROJECT"
