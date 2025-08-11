#!/bin/bash

# Terraform deployment script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TERRAFORM_DIR="deployment"
PROJECT_ID=${1:-$GCP_PROJECT_ID}
ENVIRONMENT=${2:-"production"}

function print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

function print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

function print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

function print_error() {
    echo -e "${RED}❌ $1${NC}"
}

function check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check if terraform is installed
    if ! command -v terraform &> /dev/null; then
        print_error "Terraform is not installed. Please install Terraform first."
        exit 1
    fi
    print_success "Terraform is installed"
    
    # Check if gcloud is installed and authenticated
    if ! command -v gcloud &> /dev/null; then
        print_error "Google Cloud CLI is not installed. Please install gcloud first."
        exit 1
    fi
    print_success "Google Cloud CLI is installed"
    
    # Check if authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        print_error "Not authenticated with Google Cloud. Please run: gcloud auth login"
        exit 1
    fi
    print_success "Authenticated with Google Cloud"
    
    # Check project ID
    if [ -z "$PROJECT_ID" ]; then
        print_error "PROJECT_ID is required. Set GCP_PROJECT_ID environment variable or pass as first argument."
        exit 1
    fi
    print_success "Project ID: $PROJECT_ID"
    
    # Check if terraform.tfvars exists
    if [ ! -f "$TERRAFORM_DIR/terraform.tfvars" ]; then
        print_warning "terraform.tfvars not found. Creating from example..."
        cp "$TERRAFORM_DIR/terraform.tfvars.example" "$TERRAFORM_DIR/terraform.tfvars"
        print_warning "Please edit $TERRAFORM_DIR/terraform.tfvars with your configuration"
        exit 1
    fi
    print_success "terraform.tfvars found"
}

function setup_terraform_backend() {
    print_header "Setting up Terraform Backend"
    
    BUCKET_NAME="${PROJECT_ID}-terraform-state"
    
    # Check if bucket exists, create if not
    if ! gsutil ls -b gs://$BUCKET_NAME &> /dev/null; then
        print_warning "Creating Terraform state bucket: $BUCKET_NAME"
        gsutil mb gs://$BUCKET_NAME
        gsutil versioning set on gs://$BUCKET_NAME
        print_success "Terraform state bucket created"
    else
        print_success "Terraform state bucket already exists"
    fi
    
    # Update backend configuration
    cat > "$TERRAFORM_DIR/backend.tf" << EOF
terraform {
  backend "gcs" {
    bucket = "$BUCKET_NAME"
    prefix = "terraform/state/$ENVIRONMENT"
  }
}
EOF
    print_success "Backend configuration updated"
}

function terraform_init() {
    print_header "Initializing Terraform"
    
    cd $TERRAFORM_DIR
    terraform init -upgrade
    print_success "Terraform initialized"
}

function terraform_plan() {
    print_header "Planning Terraform Deployment"
    
    terraform plan \
        -var="project_id=$PROJECT_ID" \
        -var="environment=$ENVIRONMENT" \
        -out=tfplan
    
    print_success "Terraform plan completed"
    
    echo -e "${YELLOW}Review the plan above. Do you want to continue? (y/N)${NC}"
    read -r response
    if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        print_warning "Deployment cancelled"
        exit 0
    fi
}

function terraform_apply() {
    print_header "Applying Terraform Configuration"
    
    terraform apply tfplan
    print_success "Terraform deployment completed"
}

function display_outputs() {
    print_header "Deployment Outputs"
    
    echo -e "${BLUE}Cloud Run URL:${NC} $(terraform output -raw cloud_run_url)"
    echo -e "${BLUE}Load Balancer IP:${NC} $(terraform output -raw load_balancer_ip)"
    echo -e "${BLUE}Redis Host:${NC} $(terraform output -raw redis_host)"
    echo -e "${BLUE}Database Connection:${NC} $(terraform output -raw database_connection_name)"
    echo -e "${BLUE}Monitoring Dashboard:${NC} $(terraform output -raw monitoring_dashboard_url)"
}

function post_deployment_tasks() {
    print_header "Post-Deployment Tasks"
    
    print_warning "Don't forget to:"
    echo "1. Update DNS records to point to the load balancer IP"
    echo "2. Configure SSL certificate for your domain"
    echo "3. Update environment variables in Secret Manager"
    echo "4. Test the deployment with health checks"
    echo "5. Set up monitoring alerts"
    echo "6. Configure backup schedules"
}

function cleanup() {
    print_header "Cleaning up"
    
    if [ -f "$TERRAFORM_DIR/tfplan" ]; then
        rm "$TERRAFORM_DIR/tfplan"
        print_success "Terraform plan file removed"
    fi
}

# Main execution
main() {
    trap cleanup EXIT
    
    print_header "GuruAI Backend Terraform Deployment"
    echo "Environment: $ENVIRONMENT"
    echo "Project ID: $PROJECT_ID"
    echo ""
    
    check_prerequisites
    setup_terraform_backend
    terraform_init
    terraform_plan
    terraform_apply
    display_outputs
    post_deployment_tasks
    
    print_success "Deployment completed successfully!"
}

# Help function
show_help() {
    echo "Usage: $0 [PROJECT_ID] [ENVIRONMENT]"
    echo ""
    echo "Arguments:"
    echo "  PROJECT_ID   Google Cloud Project ID (or set GCP_PROJECT_ID env var)"
    echo "  ENVIRONMENT  Deployment environment (default: production)"
    echo ""
    echo "Examples:"
    echo "  $0 my-project-id production"
    echo "  $0 my-project-id staging"
    echo ""
    echo "Environment variables:"
    echo "  GCP_PROJECT_ID  Google Cloud Project ID"
    echo ""
}

# Check for help flag
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    show_help
    exit 0
fi

# Run main function
main
