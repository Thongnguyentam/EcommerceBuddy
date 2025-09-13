#!/bin/bash

# AlloyDB + Workload Identity IAM Setup Script
# This script sets up all Google Cloud IAM resources needed for AlloyDB integration
# Run this script after `kubectl delete -k .` to restore IAM configurations

set -e

# Configuration
PROJECT_ID="gke-hack-471804"
REGION="us-central1"
CLUSTER_NAME="autopilot-cluster-1"
ALLOYDB_USER_GSA_NAME="alloydb-user-sa"
ALLOYDB_USER_GSA_EMAIL="${ALLOYDB_USER_GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
ALLOYDB_SECRET_NAME="alloydb-secret"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[SETUP]${NC} $1"
}

# Function to check if resource exists
gsa_exists() {
    gcloud iam service-accounts describe ${ALLOYDB_USER_GSA_EMAIL} \
        --project=${PROJECT_ID} \
        --quiet > /dev/null 2>&1
}

secret_exists() {
    gcloud secrets describe ${ALLOYDB_SECRET_NAME} \
        --project=${PROJECT_ID} \
        --quiet > /dev/null 2>&1
}

# Function to create Google Service Account
create_google_service_account() {
    print_header "Creating Google Service Account for AlloyDB..."
    
    if gsa_exists; then
        print_warning "Google Service Account ${ALLOYDB_USER_GSA_EMAIL} already exists"
    else
        print_status "Creating Google Service Account: ${ALLOYDB_USER_GSA_NAME}"
        gcloud iam service-accounts create ${ALLOYDB_USER_GSA_NAME} \
            --display-name="AlloyDB User Service Account" \
            --description="Service account for AlloyDB access from GKE workloads" \
            --project=${PROJECT_ID}
        
        print_status "✅ Google Service Account created: ${ALLOYDB_USER_GSA_EMAIL}"
    fi
}

# Function to grant IAM roles to the Google Service Account
grant_iam_roles() {
    print_header "Granting IAM roles to Google Service Account..."
    
    local roles=(
        "roles/alloydb.client"
        "roles/alloydb.admin" 
        "roles/alloydb.viewer"
        "roles/secretmanager.secretAccessor"
        "roles/monitoring.metricWriter"
        "roles/serviceusage.serviceUsageConsumer"
    )
    
    for role in "${roles[@]}"; do
        print_status "Granting role: ${role}"
        gcloud projects add-iam-policy-binding ${PROJECT_ID} \
            --member="serviceAccount:${ALLOYDB_USER_GSA_EMAIL}" \
            --role="${role}" \
            --quiet
    done
    
    print_status "✅ All IAM roles granted to ${ALLOYDB_USER_GSA_EMAIL}"
}

# Function to create Workload Identity bindings
create_workload_identity_bindings() {
    print_header "Setting up Workload Identity bindings..."
    
    local k8s_service_accounts=(
        "cartservice"
        "productcatalogservice"
    )
    
    for ksa in "${k8s_service_accounts[@]}"; do
        print_status "Creating Workload Identity binding for KSA: ${ksa}"
        
        # Grant workloadIdentityUser role to allow KSA to impersonate GSA
        gcloud iam service-accounts add-iam-policy-binding ${ALLOYDB_USER_GSA_EMAIL} \
            --role="roles/iam.workloadIdentityUser" \
            --member="serviceAccount:${PROJECT_ID}.svc.id.goog[default/${ksa}]" \
            --project=${PROJECT_ID} \
            --quiet
        
        print_status "✅ Workload Identity binding created: default/${ksa} -> ${ALLOYDB_USER_GSA_EMAIL}"
    done
}

# Function to create Secret Manager secret if it doesn't exist
create_secret_if_needed() {
    print_header "Checking Secret Manager secret..."
    
    if secret_exists; then
        print_warning "Secret ${ALLOYDB_SECRET_NAME} already exists"
        local current_password=$(gcloud secrets versions access latest --secret=${ALLOYDB_SECRET_NAME} --project=${PROJECT_ID})
        print_status "Current password: ${current_password}"
    else
        print_status "Creating Secret Manager secret: ${ALLOYDB_SECRET_NAME}"
        print_warning "Using default password: Admin123"
        echo "Admin123" | gcloud secrets create ${ALLOYDB_SECRET_NAME} \
            --data-file=- \
            --project=${PROJECT_ID}
        
        print_status "✅ Secret created: ${ALLOYDB_SECRET_NAME}"
    fi
}

# Function to annotate Kubernetes Service Accounts (after deployment)
annotate_kubernetes_service_accounts() {
    print_header "Annotating Kubernetes Service Accounts..."
    
    local k8s_service_accounts=(
        "cartservice"
        "productcatalogservice"
    )
    
    print_warning "This step requires the Kubernetes Service Accounts to exist first!"
    print_warning "Run this after: kubectl apply -k ."
    echo ""
    
    for ksa in "${k8s_service_accounts[@]}"; do
        echo "# Annotate ${ksa} KSA to use GSA:"
        echo "kubectl annotate serviceaccount ${ksa} \\"
        echo "  iam.gke.io/gcp-service-account=${ALLOYDB_USER_GSA_EMAIL} \\"
        echo "  --overwrite"
        echo ""
    done
    
    echo "# Restart deployments to pick up new annotations:"
    echo "kubectl rollout restart deploy/cartservice"
    echo "kubectl rollout restart deploy/productcatalogservice"
}

# Function to verify current setup
verify_setup() {
    print_header "Verifying current setup..."
    
    echo ""
    echo "=== Google Service Account ==="
    if gsa_exists; then
        print_status "✅ GSA exists: ${ALLOYDB_USER_GSA_EMAIL}"
    else
        print_error "❌ GSA missing: ${ALLOYDB_USER_GSA_EMAIL}"
    fi
    
    echo ""
    echo "=== IAM Roles ==="
    gcloud projects get-iam-policy ${PROJECT_ID} \
        --flatten="bindings[].members" \
        --format="table(bindings.role)" \
        --filter="bindings.members:${ALLOYDB_USER_GSA_EMAIL}" | \
        sed 's/^/  /'
    
    echo ""
    echo "=== Workload Identity Bindings ==="
    gcloud iam service-accounts get-iam-policy ${ALLOYDB_USER_GSA_EMAIL} \
        --project=${PROJECT_ID} \
        --flatten="bindings[].members" \
        --format="table(bindings.role,bindings.members)" \
        --filter="bindings.role:roles/iam.workloadIdentityUser" | \
        sed 's/^/  /'
    
    echo ""
    echo "=== Secret Manager ==="
    if secret_exists; then
        print_status "✅ Secret exists: ${ALLOYDB_SECRET_NAME}"
        local password=$(gcloud secrets versions access latest --secret=${ALLOYDB_SECRET_NAME} --project=${PROJECT_ID})
        echo "  Password: ${password}"
    else
        print_error "❌ Secret missing: ${ALLOYDB_SECRET_NAME}"
    fi
    
    echo ""
    echo "=== Kubernetes Service Accounts (if deployed) ==="
    local ksa_exists=false
    for ksa in cartservice productcatalogservice; do
        if kubectl get serviceaccount ${ksa} &>/dev/null; then
            ksa_exists=true
            local annotation=$(kubectl get serviceaccount ${ksa} -o jsonpath='{.metadata.annotations.iam\.gke\.io/gcp-service-account}')
            if [[ "${annotation}" == "${ALLOYDB_USER_GSA_EMAIL}" ]]; then
                print_status "  ✅ ${ksa}: ${annotation}"
            else
                print_warning "  ⚠️  ${ksa}: ${annotation:-'<not annotated>'}"
            fi
        fi
    done
    
    if [[ "${ksa_exists}" == "false" ]]; then
        print_warning "  No Kubernetes Service Accounts found (need to deploy first)"
    fi
}

# Function to clean up all IAM resources
cleanup_iam() {
    print_header "Cleaning up IAM resources..."
    print_warning "This will remove all AlloyDB-related IAM configurations!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if gsa_exists; then
            print_status "Deleting Google Service Account: ${ALLOYDB_USER_GSA_EMAIL}"
            gcloud iam service-accounts delete ${ALLOYDB_USER_GSA_EMAIL} \
                --project=${PROJECT_ID} \
                --quiet
        fi
        
        if secret_exists; then
            print_status "Deleting Secret Manager secret: ${ALLOYDB_SECRET_NAME}"
            gcloud secrets delete ${ALLOYDB_SECRET_NAME} \
                --project=${PROJECT_ID} \
                --quiet
        fi
        
        print_status "✅ IAM cleanup complete"
    else
        print_status "Cleanup cancelled"
    fi
}

# Function to show help
show_help() {
    echo "AlloyDB + Workload Identity IAM Setup Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  setup       Complete IAM setup (GSA + roles + WI bindings + secret)"
    echo "  gsa         Create Google Service Account only"
    echo "  roles       Grant IAM roles to GSA only"
    echo "  workload    Create Workload Identity bindings only"
    echo "  secret      Create Secret Manager secret only"
    echo "  annotate    Show commands to annotate Kubernetes Service Accounts"
    echo "  verify      Verify current setup"
    echo "  cleanup     Remove all IAM resources"
    echo "  help        Show this help message"
    echo ""
    echo "Configuration:"
    echo "  Project ID: ${PROJECT_ID}"
    echo "  Region: ${REGION}"
    echo "  GSA Name: ${ALLOYDB_USER_GSA_NAME}"
    echo "  GSA Email: ${ALLOYDB_USER_GSA_EMAIL}"
    echo "  Secret Name: ${ALLOYDB_SECRET_NAME}"
    echo ""
    echo "Typical workflow after 'kubectl delete -k .':"
    echo "  1. $0 setup              # Set up all IAM resources"
    echo "  2. kubectl apply -k .    # Deploy application"
    echo "  3. $0 annotate          # Get commands to annotate KSAs"
    echo "  4. $0 verify            # Verify everything is working"
}

# Main script logic
case "$1" in
    "setup")
        print_header "🚀 Starting complete AlloyDB IAM setup..."
        create_google_service_account
        grant_iam_roles
        create_workload_identity_bindings
        create_secret_if_needed
        echo ""
        print_status "✅ AlloyDB IAM setup complete!"
        echo ""
        print_warning "Next steps:"
        echo "1. Deploy application: kubectl apply -k ."
        echo "2. Annotate KSAs: $0 annotate"
        echo "3. Verify setup: $0 verify"
        ;;
    "gsa")
        create_google_service_account
        ;;
    "roles")
        grant_iam_roles
        ;;
    "workload")
        create_workload_identity_bindings
        ;;
    "secret")
        create_secret_if_needed
        ;;
    "annotate")
        annotate_kubernetes_service_accounts
        ;;
    "verify")
        verify_setup
        ;;
    "cleanup")
        cleanup_iam
        ;;
    "help"|"--help"|"-h"|"")
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac 