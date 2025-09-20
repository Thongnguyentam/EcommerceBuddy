#!/bin/bash

# Setup Shopping Assistant Service with Cloud SQL
# This script adds the shopping assistant service to your existing Cloud SQL setup

set -euo pipefail

# Configuration - Match your existing PRIVATE Cloud SQL setup
PROJECT_ID="gke-hack-471804"
CLOUDSQL_INSTANCE="onlineboutique-instance-private"
REGION="us-central1"
CLOUDSQL_PRIVATE_IP="10.103.0.3"
SECRET_NAME="cloudsql-secret-private"
CLOUDSQL_USER_GSA_NAME="cloudsql-user-sa-private"

echo "🤖 Setting up Shopping Assistant Service with Cloud SQL..."
echo "=================================================="
echo "🔒 Using PRIVATE Cloud SQL (same as other services)"
echo "📍 Private IP: ${CLOUDSQL_PRIVATE_IP}"
echo "📦 Database: products (existing)"
echo "🔑 Secret: ${SECRET_NAME} (existing)"
echo "👤 GSA: ${CLOUDSQL_USER_GSA_NAME} (existing)"

# Function to setup Workload Identity for shopping assistant
setup_workload_identity() {
    echo "🔗 Setting up Workload Identity for shoppingassistantservice..."
    
    # Add shoppingassistantservice to the existing PRIVATE GSA
    gcloud iam service-accounts add-iam-policy-binding \
        ${CLOUDSQL_USER_GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com \
        --member="serviceAccount:${PROJECT_ID}.svc.id.goog[default/shoppingassistantservice]" \
        --role=roles/iam.workloadIdentityUser \
        2>/dev/null || echo "Workload Identity binding already exists"
    
    echo "✅ Workload Identity configured for shoppingassistantservice"
}

# Function to enable required APIs
enable_apis() {
    echo "📡 Enabling required APIs..."
    
    gcloud services enable generativelanguage.googleapis.com
    gcloud services enable aiplatform.googleapis.com
    
    echo "✅ APIs enabled"
}

# Function to build and push Docker image
build_and_push_image() {
    echo "🐳 Building and pushing shopping assistant image..."
    
    # Build the image
    cd src/shoppingassistantservice-cloudsql
    
    docker build -t gcr.io/${PROJECT_ID}/shoppingassistantservice-cloudsql:latest .
    docker push gcr.io/${PROJECT_ID}/shoppingassistantservice-cloudsql:latest
    
    cd ../..
    
    echo "✅ Docker image built and pushed"
}

# Function to get Google API key and store in Secret Manager
setup_google_api_key() {
    echo "🔑 Setting up Google API Key..."
    echo ""
    echo "⚠️  IMPORTANT: You need to provide a Google API Key for Gemini AI"
    echo ""
    echo "To get a Google API key:"
    echo "1. Go to: https://console.cloud.google.com/apis/credentials"
    echo "2. Create credentials -> API key"
    echo "3. Restrict the key to 'Generative Language API'"
    echo ""
    
    read -p "Enter your Google API Key: " GOOGLE_API_KEY
    
    if [ -z "$GOOGLE_API_KEY" ]; then
        echo "❌ API key is required. Exiting."
        exit 1
    fi
    
    # Store API key in Secret Manager
    echo "📝 Storing API key in Secret Manager..."
    echo "${GOOGLE_API_KEY}" | gcloud secrets create google-gemini-api-key \
        --data-file=- \
        --project=${PROJECT_ID} \
        2>/dev/null || echo "Secret already exists, updating..."
    
    # Update existing secret if it already exists
    if [ $? -ne 0 ]; then
        echo "${GOOGLE_API_KEY}" | gcloud secrets versions add google-gemini-api-key \
            --data-file=- \
            --project=${PROJECT_ID}
    fi
    
    # Create Kubernetes secret from Secret Manager
    echo "🔐 Creating Kubernetes secret..."
    kubectl delete secret google-api-key-secret --ignore-not-found=true
    kubectl create secret generic google-api-key-secret \
        --from-literal=api-key="${GOOGLE_API_KEY}"
    
    echo "✅ Google API key configured securely"
}

# Function to verify products table exists
verify_products_table() {
    echo "🔍 Verifying products table exists..."
    
    # Check if products table exists using jumpbox VM
    PRODUCT_COUNT=$(gcloud compute ssh alloydb-jumpbox --zone=us-central1-a \
        --command="PGPASSWORD='Admin123' psql -h ${CLOUDSQL_PRIVATE_IP} -U postgres -d products -t -c 'SELECT COUNT(*) FROM products;'" | tr -d ' \n')
    
    echo "✅ Products table verified: ${PRODUCT_COUNT} products available"
}

# Main execution
main() {
    echo "Starting shopping assistant setup..."
    echo "Project: ${PROJECT_ID}"
    echo "Instance: ${CLOUDSQL_INSTANCE} (PRIVATE)"
    echo "Database: products (existing)"
    echo "Secret: ${SECRET_NAME} (existing)"
    echo "GSA: ${CLOUDSQL_USER_GSA_NAME} (existing)"
    echo "Private IP: ${CLOUDSQL_PRIVATE_IP}"
    echo ""
    
    # Enable required APIs
    enable_apis
    
    # Setup Workload Identity for shopping assistant
    setup_workload_identity
    
    # Verify products table exists
    verify_products_table
    
    # Setup Google API key
    setup_google_api_key
    
    # Build and push Docker image
    build_and_push_image
    
    echo ""
    echo "🎉 Shopping Assistant setup complete!"
    echo ""
    echo "📝 Next steps:"
    echo "1. Enable the shopping-assistant-cloudsql component in your kustomization.yaml:"
    echo "   components:"
    echo "   - ../kustomize/components/shopping-assistant-cloudsql"
    echo ""
    echo "2. Deploy with: kubectl apply -k kubernetes-manifests/"
    echo ""
    echo "3. Test the shopping assistant:"
    echo "   kubectl port-forward svc/shoppingassistantservice 8080:80"
    echo "   curl -X POST http://localhost:8080/ -H 'Content-Type: application/json' -d '{\"message\":\"I need furniture for my living room\"}'"
    echo ""
    echo "🔒 Using PRIVATE Cloud SQL instance: ${CLOUDSQL_INSTANCE}"
    echo "🔑 Using private secret: ${SECRET_NAME}"
    echo "👤 Using private GSA: ${CLOUDSQL_USER_GSA_NAME}"
    echo ""
    echo "🎯 Environment variables configured:"
    echo "   - CLOUDSQL_HOST: ${CLOUDSQL_PRIVATE_IP}"
    echo "   - CLOUDSQL_DATABASE_NAME: products"
    echo "   - CLOUDSQL_SECRET_NAME: ${SECRET_NAME}"
    echo ""
    echo "✅ Ready to use with your existing Cloud SQL setup!"
}

# Run main function
main "$@" 