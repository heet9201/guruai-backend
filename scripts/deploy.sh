# Deployment Scripts
#!/bin/bash

# Google Cloud Run Deployment Script
set -e

# Configuration
PROJECT_ID=${GCP_PROJECT_ID}
SERVICE_NAME="guruai-backend"
REGION="us-central1"
IMAGE_TAG=${GITHUB_SHA:-latest}

echo "🚀 Starting deployment to Google Cloud Run..."

# Authenticate with Google Cloud
echo "🔐 Authenticating with Google Cloud..."
gcloud auth activate-service-account --key-file=${GOOGLE_APPLICATION_CREDENTIALS}
gcloud config set project ${PROJECT_ID}

# Build and push Docker image
echo "🐳 Building and pushing Docker image..."
docker build -t gcr.io/${PROJECT_ID}/${SERVICE_NAME}:${IMAGE_TAG} .
docker push gcr.io/${PROJECT_ID}/${SERVICE_NAME}:${IMAGE_TAG}

# Deploy to Cloud Run
echo "☁️ Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image gcr.io/${PROJECT_ID}/${SERVICE_NAME}:${IMAGE_TAG} \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 1000 \
  --timeout 300 \
  --concurrency 1000 \
  --vpc-connector projects/${PROJECT_ID}/locations/${REGION}/connectors/guruai-connector \
  --set-env-vars "FLASK_ENV=production,GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
  --service-account guruai-cloud-run@${PROJECT_ID}.iam.gserviceaccount.com

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format='value(status.url)')

echo "✅ Deployment successful!"
echo "🌐 Service URL: ${SERVICE_URL}"

# Run health check
echo "🏥 Running health check..."
curl -f ${SERVICE_URL}/health || {
  echo "❌ Health check failed!"
  exit 1
}

echo "✅ Health check passed!"
echo "🎉 Deployment completed successfully!"
