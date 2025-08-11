#!/bin/bash

# Infrastructure Setup Script
set -e

PROJECT_ID=${1:-$GCP_PROJECT_ID}
REGION=${2:-"us-central1"}

if [ -z "$PROJECT_ID" ]; then
  echo "❌ Error: PROJECT_ID is required"
  echo "Usage: ./setup-infrastructure.sh PROJECT_ID [REGION]"
  exit 1
fi

echo "🏗️ Setting up infrastructure for GuruAI Backend..."
echo "📍 Project: $PROJECT_ID"
echo "🌍 Region: $REGION"

# Set project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔌 Enabling required APIs..."
gcloud services enable \
  run.googleapis.com \
  vpcaccess.googleapis.com \
  redis.googleapis.com \
  secretmanager.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com \
  cloudtrace.googleapis.com \
  compute.googleapis.com \
  servicenetworking.googleapis.com \
  cloudbuild.googleapis.com

# Create VPC network
echo "🌐 Creating VPC network..."
gcloud compute networks create guruai-vpc \
  --subnet-mode regional \
  --bgp-routing-mode regional || echo "VPC already exists"

# Create subnet
echo "🔗 Creating subnet..."
gcloud compute networks subnets create guruai-subnet \
  --network guruai-vpc \
  --range 10.0.0.0/24 \
  --region $REGION || echo "Subnet already exists"

# Create VPC connector
echo "🔌 Creating VPC connector..."
gcloud compute networks vpc-access connectors create guruai-connector \
  --region $REGION \
  --subnet guruai-subnet \
  --subnet-project $PROJECT_ID \
  --min-instances 2 \
  --max-instances 10 || echo "VPC connector already exists"

# Create Redis instance
echo "🗄️ Creating Redis instance..."
gcloud redis instances create guruai-cache \
  --size 5 \
  --region $REGION \
  --network projects/$PROJECT_ID/global/networks/guruai-vpc \
  --redis-version redis_7_0 \
  --tier standard \
  --auth-enabled || echo "Redis instance already exists"

# Create service account
echo "👤 Creating service account..."
gcloud iam service-accounts create guruai-cloud-run \
  --display-name "GuruAI Cloud Run Service Account" || echo "Service account already exists"

# Grant IAM roles
echo "🔐 Granting IAM roles..."
for role in \
  "roles/cloudsql.client" \
  "roles/secretmanager.secretAccessor" \
  "roles/storage.objectViewer" \
  "roles/storage.objectCreator" \
  "roles/monitoring.metricWriter" \
  "roles/logging.logWriter" \
  "roles/cloudtrace.agent"
do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member "serviceAccount:guruai-cloud-run@$PROJECT_ID.iam.gserviceaccount.com" \
    --role $role
done

# Create secrets (you'll need to set these values)
echo "🔒 Creating secret placeholders..."
echo "dummy-database-url" | gcloud secrets create database-url --data-file=- || echo "Secret already exists"
echo "dummy-jwt-key" | gcloud secrets create jwt-secret-key --data-file=- || echo "Secret already exists"
echo "dummy-encryption-key" | gcloud secrets create encryption-key --data-file=- || echo "Secret already exists"
echo "dummy-pii-key" | gcloud secrets create pii-encryption-key --data-file=- || echo "Secret already exists"
echo "dummy-openai-key" | gcloud secrets create openai-api-key --data-file=- || echo "Secret already exists"

# Grant secret access
echo "🔑 Granting secret access..."
for secret in database-url jwt-secret-key encryption-key pii-encryption-key openai-api-key; do
  gcloud secrets add-iam-policy-binding $secret \
    --member "serviceAccount:guruai-cloud-run@$PROJECT_ID.iam.gserviceaccount.com" \
    --role "roles/secretmanager.secretAccessor"
done

echo "✅ Infrastructure setup completed!"
echo ""
echo "📝 Next steps:"
echo "1. Update the secret values with actual credentials:"
echo "   gcloud secrets versions add database-url --data-file=<your-db-url-file>"
echo "   gcloud secrets versions add jwt-secret-key --data-file=<your-jwt-key-file>"
echo "   gcloud secrets versions add encryption-key --data-file=<your-encryption-key-file>"
echo "   gcloud secrets versions add pii-encryption-key --data-file=<your-pii-key-file>"
echo "   gcloud secrets versions add openai-api-key --data-file=<your-openai-key-file>"
echo ""
echo "2. Run Terraform to deploy the full infrastructure:"
echo "   cd deployment && terraform init && terraform apply"
echo ""
echo "3. Deploy the application:"
echo "   ./scripts/deploy.sh"
