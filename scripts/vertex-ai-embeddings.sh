#!/bin/bash

# Vertex AI Embeddings Service Setup Script
# This script sets up all prerequisites for the embedding service

set -e

echo "🚀 Setting up Vertex AI Embeddings Service"
echo "=========================================="

# Configuration
PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project)}
SERVICE_ACCOUNT_NAME="embedding-service"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
KEY_FILE="embedding-service-key.json"

echo "📋 Configuration:"
echo "   Project ID: $PROJECT_ID"
echo "   Service Account: $SERVICE_ACCOUNT_EMAIL"
echo ""

# Step 1: Enable required APIs
echo "🔧 Step 1: Enabling required APIs..."
gcloud services enable aiplatform.googleapis.com --project=$PROJECT_ID
gcloud services enable ml.googleapis.com --project=$PROJECT_ID
echo "✅ APIs enabled"
echo ""

# Step 2: Create service account (if it doesn't exist)
echo "🔧 Step 2: Creating service account..."
if gcloud iam service-accounts describe $SERVICE_ACCOUNT_EMAIL --project=$PROJECT_ID >/dev/null 2>&1; then
    echo "⚠️  Service account already exists: $SERVICE_ACCOUNT_EMAIL"
else
    gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
        --description="Service account for embedding service" \
        --display-name="Embedding Service" \
        --project=$PROJECT_ID
    echo "✅ Service account created: $SERVICE_ACCOUNT_EMAIL"
fi
echo ""

# Step 3: Grant necessary roles
echo "🔧 Step 3: Granting IAM roles..."
ROLES=(
    "roles/aiplatform.user"
    "roles/ml.developer"
    "roles/serviceusage.serviceUsageConsumer"
)

for role in "${ROLES[@]}"; do
    echo "   Granting $role..."
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
        --role="$role" \
        --quiet
done
echo "✅ IAM roles granted"
echo ""

# Step 4: Create service account key
echo "🔧 Step 4: Creating service account key..."
if [ -f "$KEY_FILE" ]; then
    echo "⚠️  Key file already exists: $KEY_FILE"
    read -p "Do you want to create a new key? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -f "$KEY_FILE"
        gcloud iam service-accounts keys create $KEY_FILE \
            --iam-account=$SERVICE_ACCOUNT_EMAIL \
            --project=$PROJECT_ID
        echo "✅ New service account key created: $KEY_FILE"
    else
        echo "⏭️  Using existing key file"
    fi
else
    gcloud iam service-accounts keys create $KEY_FILE \
        --iam-account=$SERVICE_ACCOUNT_EMAIL \
        --project=$PROJECT_ID
    echo "✅ Service account key created: $KEY_FILE"
fi
echo ""

# Step 5: Set up environment file
echo "🔧 Step 5: Creating environment configuration..."
cat > .env << EOF
# Google Cloud Configuration
PROJECT_ID=$PROJECT_ID
REGION=us-central1
EMBEDDING_MODEL=text-embedding-004

# Service Configuration
PORT=8081

# Authentication - Path to service account key
GOOGLE_APPLICATION_CREDENTIALS=./$KEY_FILE

# Development Settings
FLASK_ENV=development
PYTHONUNBUFFERED=1
EOF
echo "✅ Environment file created: .env"
echo ""

# Step 6: Test authentication
echo "🔧 Step 6: Testing authentication..."
export GOOGLE_APPLICATION_CREDENTIALS="./$KEY_FILE"
if gcloud auth application-default print-access-token >/dev/null 2>&1; then
    echo "✅ Authentication test passed"
else
    echo "⚠️  Authentication test failed - you may need to run:"
    echo "   export GOOGLE_APPLICATION_CREDENTIALS='./$KEY_FILE'"
fi
echo ""

# Step 7: Create Kubernetes secret 
echo "🔧 Step 7: Creating Kubernetes secret (optional)..."
read -p "Do you want to create a Kubernetes secret for the service account key? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if kubectl get secret google-cloud-key >/dev/null 2>&1; then
        echo "⚠️  Kubernetes secret already exists"
        read -p "Do you want to update it? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            kubectl delete secret google-cloud-key
            kubectl create secret generic google-cloud-key --from-file=key.json=$KEY_FILE
            echo "✅ Kubernetes secret updated"
        fi
    else
        kubectl create secret generic google-cloud-key --from-file=key.json=$KEY_FILE
        echo "✅ Kubernetes secret created"
    fi
else
    echo "⏭️  Skipping Kubernetes secret creation"
fi
echo ""

# Step 8: Verify setup
echo "🔧 Step 8: Verifying setup..."
echo "   Checking project configuration..."
if [ "$PROJECT_ID" != "$(gcloud config get-value project)" ]; then
    echo "⚠️  Warning: Current gcloud project ($(gcloud config get-value project)) differs from setup project ($PROJECT_ID)"
fi

echo "   Checking service account..."
gcloud iam service-accounts describe $SERVICE_ACCOUNT_EMAIL --project=$PROJECT_ID >/dev/null
echo "✅ Service account verified"

echo "   Checking key file..."
if [ -f "$KEY_FILE" ]; then
    echo "✅ Key file exists: $KEY_FILE"
else
    echo "❌ Key file not found: $KEY_FILE"
    exit 1
fi

echo "   Checking APIs..."
if gcloud services list --enabled --filter="name:aiplatform.googleapis.com" --project=$PROJECT_ID | grep -q "aiplatform"; then
    echo "✅ Vertex AI API enabled"
else
    echo "❌ Vertex AI API not enabled"
    exit 1
fi
echo ""

# Summary
echo "🎉 Setup Complete!"
echo "=================="
echo "✅ Project ID: $PROJECT_ID"
echo "✅ Service Account: $SERVICE_ACCOUNT_EMAIL"
echo "✅ Key File: $KEY_FILE"
echo "✅ Environment File: .env"
echo ""
echo "📋 Next Steps:"
echo "   1. Test the service locally:"
echo "      cd src/embeddingservice"
echo "      source ./env/bin/activate"
echo "      export \$(grep -v '^#' .env | xargs)"
echo "      python tests/test_simple.py"
echo ""
echo "   2. Build and deploy the Docker image:"
echo "      docker build -t embeddingservice:latest ."
echo "      kubectl apply -f ../../kubernetes-manifests/embeddingservice.yaml"
echo ""
echo "   3. Test the deployed service:"
echo "      kubectl port-forward svc/embeddingservice 8081:8081"
echo "      curl http://localhost:8081/health"
echo ""
echo "🔐 Security Note:"
echo "   Keep the key file ($KEY_FILE) secure and do not commit it to version control!"
echo "   Add it to .gitignore if not already present."
