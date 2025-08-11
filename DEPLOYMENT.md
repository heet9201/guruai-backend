# GuruAI Backend Deployment Guide

## 🚀 Production Deployment Guide

This comprehensive guide will help you deploy the GuruAI Backend to Google Cloud Run with enterprise-grade infrastructure, monitoring, and CI/CD pipeline.

## 📋 Prerequisites

- Google Cloud Project with billing enabled
- Google Cloud CLI (`gcloud`) installed and authenticated
- Docker installed locally
- Terraform installed (optional for infrastructure management)
- GitHub repository with Actions enabled

## 🏗️ Infrastructure Setup

### 1. Initial Google Cloud Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd guruai-backend

# Set your project ID
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"

# Run the infrastructure setup script
./scripts/setup-infrastructure.sh $GCP_PROJECT_ID $GCP_REGION
```

This script will:

- Enable required Google Cloud APIs
- Create VPC network and subnet
- Set up VPC connector for database access
- Create Redis instance for caching
- Create service account with proper IAM roles
- Create secret placeholders in Secret Manager

### 2. Configure Secrets

Update the dummy secrets with your actual values:

```bash
# Database URL (PostgreSQL connection string)
echo "postgresql://user:password@host:port/database" | gcloud secrets versions add database-url --data-file=-

# JWT Secret Key (generate a strong random key)
openssl rand -base64 32 | gcloud secrets versions add jwt-secret-key --data-file=-

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
```

To get the service account key:

```bash
gcloud iam service-accounts keys create key.json \
  --iam-account guruai-cloud-run@$GCP_PROJECT_ID.iam.gserviceaccount.com
```

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
