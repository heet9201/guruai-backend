# GuruAI Backend Deployment Guide

## 🚀 Production Deployment Guide

This comprehensive guide will help you deploy the GuruAI Backend to Google Cloud Run with enterprise-grade infrastructure, Redis caching, and automated CI/CD pipeline.

## 📋 Prerequisites

- Google Cloud Project with billing enabled
- Google Cloud CLI (`gcloud`) installed and authenticated
- Docker installed locally
- GitHub repository with Actions enabled
- Basic understanding of Google Cloud services

## 🏗️ Infrastructure Overview

### Production Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   GitHub Repo   │───▶│   Cloud Build    │───▶│  Artifact Reg.  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Monitoring    │◀───│   Cloud Run      │◀───│   Load Balancer │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   VPC Connector  │
                       └──────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  Redis Instance  │
                       └──────────────────┘
```

### Core Components

1. **Google Cloud Run**: Auto-scaling containerized application hosting
2. **Google Cloud Memorystore (Redis)**: High-performance caching and session storage
3. **VPC Connector**: Secure private network connectivity to Redis
4. **Artifact Registry**: Container image storage and management
5. **Cloud Build**: Automated CI/CD pipeline with GitHub integration

## 🛠️ Initial Setup

### 1. Google Cloud Project Setup

```bash
# Set up your project
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"
export SERVICE_NAME="guruai-backend"

# Authenticate with Google Cloud
gcloud auth login
gcloud config set project $GCP_PROJECT_ID

# Enable required APIs
gcloud services enable \
  artifactregistry.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  redis.googleapis.com \
  vpcaccess.googleapis.com \
  compute.googleapis.com
```

### 2. Create Redis Infrastructure

```bash
# Create Redis instance (1GB, Redis 7.0)
gcloud redis instances create guruai-redis \
  --size=1 \
  --region=$GCP_REGION \
  --redis-version=redis_7_0 \
  --network=default

# Get Redis host IP (save this for later)
REDIS_HOST=$(gcloud redis instances describe guruai-redis \
  --region=$GCP_REGION \
  --format='value(host)')
echo "Redis Host: $REDIS_HOST"
```

### 3. Create VPC Connector

```bash
# Create subnet for VPC connector
gcloud compute networks subnets create guruai-connector-subnet \
  --range=10.8.0.0/28 \
  --network=default \
  --region=$GCP_REGION

# Create VPC connector
gcloud compute networks vpc-access connectors create guruai-connector \
  --region=$GCP_REGION \
  --subnet=guruai-connector-subnet
```

### 4. Create Deployment Service Account

**Important**: Use a dedicated service account for deployments (not Firebase admin):

```bash
# Create dedicated deployment service account
gcloud iam service-accounts create guruai-deployment \
  --display-name="GuruAI Deployment Service Account" \
  --description="Service account for CI/CD deployment"

# Set service account email
DEPLOY_SA="guruai-deployment@$GCP_PROJECT_ID.iam.gserviceaccount.com"

# Add required roles
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$DEPLOY_SA" \
  --role="roles/serviceusage.serviceUsageAdmin"

gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$DEPLOY_SA" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$DEPLOY_SA" \
  --role="roles/cloudbuild.builds.editor"

gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$DEPLOY_SA" \
  --role="roles/artifactregistry.admin"

gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$DEPLOY_SA" \
  --role="roles/redis.admin"

gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$DEPLOY_SA" \
  --role="roles/vpcaccess.admin"

gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$DEPLOY_SA" \
  --role="roles/compute.networkAdmin"

gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$DEPLOY_SA" \
  --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:$DEPLOY_SA" \
  --role="roles/iam.serviceAccountTokenCreator"

# Create service account key
gcloud iam service-accounts keys create deployment-key.json \
  --iam-account=$DEPLOY_SA

# Convert to base64 for GitHub Secrets
cat deployment-key.json | base64

# Clean up the key file (IMPORTANT for security)
rm deployment-key.json
```

## 🔐 GitHub Secrets Configuration

Go to your GitHub repository → Settings → Secrets and variables → Actions

### Required Secrets

1. **`GCP_SA_KEY`**: Base64 encoded service account key (from step 4 above)
2. **`GCP_PROJECT_ID`**: Your Google Cloud project ID

### Example:

```
GCP_SA_KEY=ewogICJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIsCiAgInByb2plY3RfaWQiOi...
GCP_PROJECT_ID=your-project-id
```

## 🚀 CI/CD Pipeline

### Automated Deployment Flow

The GitHub Actions workflow (`.github/workflows/ci-cd.yml`) provides:

#### 1. **Testing Stage**

- Unit tests with Redis mock
- Integration tests
- Security scanning (Bandit, Safety, Semgrep)
- Code coverage reporting

#### 2. **Build Stage**

- Multi-stage Docker build
- Image optimization
- Push to Artifact Registry

#### 3. **Staging Deployment**

- Deploy to staging environment
- Smoke tests on staging
- Health check validation

#### 4. **Production Deployment**

- Blue-green deployment strategy
- Gradual traffic shifting: 10% → 50% → 100%
- Automatic rollback on failures

### Deployment Strategies

#### Standard Deployment (Gradual)

```bash
git add .
git commit -m "feat: Add new feature"
git push origin main
```

**Result**: 10% → 50% → 100% traffic shift over 10 minutes

#### Fast Deployment (Skip Gradual)

```bash
git add .
git commit -m "hotfix: Critical fix [skip-gradual]"
git push origin main
```

**Result**: Immediate 100% traffic shift

### Manual Deployment (Emergency)

If GitHub Actions fails, deploy manually:

```bash
# Build and push image
docker build -t $GCP_REGION-docker.pkg.dev/$GCP_PROJECT_ID/guruai-backend/app:manual .
docker push $GCP_REGION-docker.pkg.dev/$GCP_PROJECT_ID/guruai-backend/app:manual

# Get Redis host
REDIS_HOST=$(gcloud redis instances describe guruai-redis \
  --region=$GCP_REGION \
  --format='value(host)')

# Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \
  --image $GCP_REGION-docker.pkg.dev/$GCP_PROJECT_ID/guruai-backend/app:manual \
  --platform managed \
  --region $GCP_REGION \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 1 \
  --timeout 300 \
  --concurrency 80 \
  --set-env-vars="ENVIRONMENT=production,REDIS_HOST=$REDIS_HOST,REDIS_PORT=6379" \
  --vpc-connector guruai-connector
```

# Encryption Key (32-byte key for data encryption)

openssl rand -base64 32 | gcloud secrets versions add encryption-key --data-file=-

# PII Encryption Key (separate key for PII data)

openssl rand -base64 32 | gcloud secrets versions add pii-encryption-key --data-file=-

# OpenAI API Key

echo "your-openai-api-key" | gcloud secrets versions add openai-api-key --data-file=-

```

### 3. GitHub Repository Secrets

Configure the following secrets in your GitHub repository (Settings → Secrets and variables → Actions):

```

GCP_PROJECT_ID=your-project-id
GCP_SA_KEY=<service-account-json-key>
SLACK_WEBHOOK_URL=<optional-slack-webhook-for-notifications>

````

To get the service account key:

```bash
gcloud iam service-accounts keys create key.json \
  --iam-account guruai-cloud-run@$GCP_PROJECT_ID.iam.gserviceaccount.com
````

## 🚀 Deployment Options

### Option A: Automated Deployment via GitHub Actions

1. **Push to staging branch** for staging deployment:

   ```bash
   git checkout -b staging
   git push origin staging
   ```

2. **Push to main branch** for production deployment:
   ```bash
   git checkout main
   git push origin main
   ```

The CI/CD pipeline will automatically:

- Run comprehensive tests (unit, integration, API)
- Perform security scanning
- Build and push Docker image
- Deploy to Google Cloud Run
- Run health checks
- Send notifications

### Option B: Manual Deployment

```bash
# Build and deploy manually
./scripts/deploy.sh
```

## 📊 Monitoring and Observability

### Grafana Dashboard

Access your Grafana dashboard at: `https://monitoring-<hash>-uc.a.run.app`

Default credentials:

- Username: `admin`
- Password: Check Cloud Run logs for generated password

### Key Metrics Monitored

- **Request Rate**: Requests per second
- **Response Time**: Average and P95 latency
- **Error Rate**: HTTP 4xx/5xx responses
- **Memory Usage**: Container memory consumption
- **Active Users**: Current active user sessions
- **AI Service Performance**: Content generation metrics
- **Storage Usage**: File upload and storage metrics

### Alert Policies

Alerts are configured for:

- High error rate (>1%)
- Slow response times (>2s for chat, >30s for content generation)
- High memory usage (>80%)
- Service downtime
- AI service failures
- Cost threshold breaches

## 🔍 Health Checks

The application provides multiple health check endpoints:

- `GET /health` - Overall application health
- `GET /health/ready` - Kubernetes readiness probe
- `GET /health/live` - Kubernetes liveness probe

Health checks verify:

- Database connectivity
- Redis connectivity
- AI service availability
- Storage service status
- Memory and disk usage

## 📈 Scalability Configuration

### Auto-scaling Settings

- **Minimum instances**: 0 (scales to zero when no traffic)
- **Maximum instances**: 1000
- **Target CPU utilization**: 70%
- **Target memory utilization**: 80%
- **Cold start optimization**: Multi-stage Docker build

### Performance Targets

- **Concurrent users**: 10,000+
- **API requests**: 100,000+ per hour
- **Content generations**: 1,000+ per hour
- **Uptime target**: 99.9%
- **Response time targets**:
  - Chat API: <2 seconds
  - Content generation: <30 seconds
  - File operations: <5 seconds

## 🔒 Security Features

- **JWT Authentication** with refresh token rotation
- **Multi-Factor Authentication** support
- **End-to-end encryption** for sensitive data
- **Content moderation** and AI safety filters
- **Rate limiting** and DDoS protection
- **PII detection** and GDPR compliance
- **Comprehensive audit logging**

## 🐛 Troubleshooting

### Common Issues

1. **Deployment fails with authentication error**:

   ```bash
   gcloud auth application-default login
   gcloud config set project $GCP_PROJECT_ID
   ```

2. **Health check fails**:

   - Check Cloud Run logs: `gcloud logs read --service=guruai-backend`
   - Verify database and Redis connectivity
   - Check secret values in Secret Manager

3. **High memory usage**:

   - Monitor Grafana dashboard
   - Check for memory leaks in application logs
   - Consider increasing memory allocation

4. **Slow response times**:
   - Check AI service performance metrics
   - Monitor database query performance
   - Verify Redis caching effectiveness

### Log Analysis

```bash
# View application logs
gcloud logs read --service=guruai-backend --limit=100

# View specific error logs
gcloud logs read --service=guruai-backend --filter="severity>=ERROR"

# Follow logs in real-time
gcloud logs tail --service=guruai-backend
```

## 🔄 Rollback Procedures

### Automatic Rollback

The CI/CD pipeline includes automatic rollback on:

- Health check failures
- High error rates
- Deployment timeouts

### Manual Rollback

```bash
# List recent revisions
gcloud run revisions list --service=guruai-backend

# Rollback to previous revision
gcloud run services update-traffic guruai-backend \
  --to-revisions=REVISION_NAME=100
```

## 💰 Cost Optimization

### Monitoring Costs

- Cost alerts configured for monthly thresholds
- Grafana dashboard includes cost tracking
- Regular cost analysis recommendations

### Optimization Tips

1. **Right-size resources**: Monitor actual usage vs. allocated resources
2. **Use preemptible instances**: For batch processing workloads
3. **Optimize cold starts**: Multi-stage Docker builds reduce image size
4. **Scale to zero**: Automatic scaling when no traffic
5. **Cache effectively**: Redis caching reduces database queries

## 📞 Support and Maintenance

### Regular Maintenance Tasks

- **Weekly**: Review security scan results
- **Monthly**: Update dependencies and base images
- **Quarterly**: Review and optimize resource allocation
- **Annually**: Security audit and compliance review

### Monitoring Checklist

- [ ] All health checks passing
- [ ] Error rate below 1%
- [ ] Response times within targets
- [ ] Memory usage below 80%
- [ ] No critical security vulnerabilities
- [ ] Cost within budget
- [ ] All alerts properly configured

## 🎯 Next Steps

1. **Set up custom domain**: Configure your domain with Cloud Load Balancer
2. **Configure CDN**: Enable Cloud CDN for static assets
3. **Set up backup strategy**: Configure automated database backups
4. **Implement disaster recovery**: Multi-region deployment for HA
5. **Security hardening**: Enable additional security features
6. **Performance optimization**: Fine-tune based on production metrics

---

For additional support or questions, refer to the monitoring dashboards, application logs, or create an issue in the repository.

## 📊 Monitoring and Health Checks

### Application Health Endpoints

The application provides comprehensive health monitoring:

```bash
# Basic health check
curl https://your-service-url/api/v1/health

# Sample response
{
  "status": "healthy",
  "checks": {
    "redis": {
      "status": "healthy",
      "details": {
        "connected_clients": 6,
        "redis_version": "7.0.15",
        "used_memory_human": "3.88M"
      },
      "response_time_ms": 17.58
    },
    "memory": {
      "status": "healthy",
      "details": {
        "available_gb": 1.48,
        "memory_percent": 26.0,
        "total_gb": 2.0
      }
    },
    "disk": {
      "status": "healthy",
      "details": {
        "free_gb": 8589934592.0,
        "used_percent": 0.0
      }
    }
  },
  "environment": "production",
  "uptime_seconds": 3600,
  "total_check_time_ms": 19.74
}
```

### Monitoring Infrastructure Components

```bash
# Check Redis instance status
gcloud redis instances describe guruai-redis --region=$GCP_REGION

# Check VPC connector status
gcloud compute networks vpc-access connectors describe guruai-connector \
  --region=$GCP_REGION

# Check Cloud Run service status
gcloud run services describe guruai-backend --region=$GCP_REGION

# View service logs
gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"guruai-backend\"" \
  --limit=50 \
  --format="table(timestamp,textPayload)"
```

## 🔧 Troubleshooting Guide

### Common Issues and Solutions

#### 1. Redis Connection Issues

**Problem**: Application can't connect to Redis
**Symptoms**: Health check shows Redis as "degraded" or "unhealthy"

```bash
# Check Redis instance status
gcloud redis instances describe guruai-redis --region=$GCP_REGION

# Check VPC connector
gcloud compute networks vpc-access connectors describe guruai-connector \
  --region=$GCP_REGION

# Verify Cloud Run has VPC connector attached
gcloud run services describe guruai-backend --region=$GCP_REGION \
  --format="value(spec.template.metadata.annotations.'run.googleapis.com/vpc-access-connector')"
```

**Solution**:

```bash
# If VPC connector is missing, update the service
gcloud run services update guruai-backend \
  --vpc-connector guruai-connector \
  --region=$GCP_REGION
```

#### 2. Deployment Permission Errors

**Problem**: GitHub Actions fails with permission denied errors
**Symptoms**: "Permission 'iam.serviceaccounts.actAs' denied"

**Solution**: Verify service account has required roles:

```bash
# Check current permissions
gcloud projects get-iam-policy $GCP_PROJECT_ID \
  --flatten="bindings[].members" \
  --format='table(bindings.role)' \
  --filter="bindings.members:guruai-deployment@$GCP_PROJECT_ID.iam.gserviceaccount.com"

# Should show these roles:
# roles/artifactregistry.admin
# roles/cloudbuild.builds.editor
# roles/compute.networkAdmin
# roles/iam.serviceAccountTokenCreator
# roles/iam.serviceAccountUser
# roles/redis.admin
# roles/run.admin
# roles/serviceusage.serviceUsageAdmin
# roles/vpcaccess.admin
```

#### 3. Traffic Allocation Failures

**Problem**: Blue-green deployment fails with revision errors
**Symptoms**: "Revision target 'abc123' invalid. Expected a revision prefixed with 'guruai-backend-'"

**Solution**: The workflow automatically handles this by getting proper revision names:

```bash
# Check current revisions
gcloud run revisions list --service=guruai-backend --region=$GCP_REGION

# Manual traffic allocation if needed
LATEST_REVISION=$(gcloud run services describe guruai-backend \
  --region=$GCP_REGION \
  --format='value(status.latestCreatedRevisionName)')

gcloud run services update-traffic guruai-backend \
  --to-revisions=$LATEST_REVISION=100 \
  --region=$GCP_REGION
```

### Emergency Procedures

#### Immediate Rollback

```bash
# Get previous revision
PREVIOUS_REVISION=$(gcloud run revisions list \
  --service=guruai-backend \
  --region=$GCP_REGION \
  --format='value(metadata.name)' \
  --limit=2 | tail -n 1)

# Immediate rollback
gcloud run services update-traffic guruai-backend \
  --to-revisions=$PREVIOUS_REVISION=100 \
  --region=$GCP_REGION
```

#### Service Recovery

```bash
# Restart all instances
gcloud run services update guruai-backend \
  --region=$GCP_REGION \
  --update-env-vars="RESTART_TIMESTAMP=$(date +%s)"

# Scale up minimum instances for faster response
gcloud run services update guruai-backend \
  --min-instances=3 \
  --region=$GCP_REGION
```

## 🔄 Maintenance Tasks

### Weekly Tasks

```bash
# Check Redis memory usage
gcloud redis instances describe guruai-redis \
  --region=$GCP_REGION \
  --format="value(memorySizeGb,currentLocationId)"

# Review application logs for errors
gcloud logging read "resource.type=\"cloud_run_revision\" AND severity>=ERROR" \
  --since="7d" \
  --limit=100
```

### Monthly Tasks

```bash
# Review and rotate service account keys (if any external keys exist)
gcloud iam service-accounts keys list \
  --iam-account=guruai-deployment@$GCP_PROJECT_ID.iam.gserviceaccount.com

# Review IAM permissions
gcloud projects get-iam-policy $GCP_PROJECT_ID \
  --format="table(bindings.role,bindings.members)"
```

## 🔐 Security Best Practices

### Network Security

- Redis instances are private (VPC-only access)
- Cloud Run uses HTTPS-only traffic
- VPC connector provides secure Redis connectivity

### Application Security

- JWT tokens with short expiration
- Redis session storage for scalability
- Rate limiting enabled

---

## 📝 Final Deployment Checklist

Before going to production, ensure:

- [ ] Redis instance is created and accessible
- [ ] VPC connector is configured and in READY state
- [ ] Service account has all required permissions
- [ ] GitHub secrets are configured correctly
- [ ] Health checks pass in staging environment
- [ ] Security scan passes
- [ ] Documentation is up to date

**🎉 Your GuruAI Backend is now production-ready with enterprise-grade infrastructure!**
