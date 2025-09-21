#!/bin/bash

# Copyright 2024 Google LLC
# Setup script for Image Assistant Service local development

set -e

echo "🚀 Setting up Image Assistant Service for local development..."

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install it first:"
    echo "   https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get current project
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo "❌ No default project set. Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "📋 Using project: $PROJECT_ID"

# Set variables
BUCKET_NAME="${PROJECT_ID}-image-analysis"
RENDERS_BUCKET_NAME="${PROJECT_ID}-image-renders"
REGION="us-central1"
SERVICE_ACCOUNT_NAME="imageassistant-sa"
KEY_FILE="./service-account-key.json"

echo "🔧 Setting up Google Cloud resources..."

# Enable required APIs
echo "📡 Enabling required APIs..."
gcloud services enable vision.googleapis.com
gcloud services enable aiplatform.googleapis.com
gcloud services enable storage.googleapis.com

# Create GCS buckets
echo "🪣 Creating GCS buckets..."

# Create main analysis bucket
echo "   Creating analysis bucket: $BUCKET_NAME"
if gsutil ls gs://$BUCKET_NAME &>/dev/null; then
    echo "   ✅ Analysis bucket already exists"
else
    gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$BUCKET_NAME
    echo "   ✅ Created analysis bucket: gs://$BUCKET_NAME"
fi

# Create renders bucket for Imagen outputs
echo "   Creating renders bucket: $RENDERS_BUCKET_NAME"
if gsutil ls gs://$RENDERS_BUCKET_NAME &>/dev/null; then
    echo "   ✅ Renders bucket already exists"
else
    gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$RENDERS_BUCKET_NAME
    echo "   ✅ Created renders bucket: gs://$RENDERS_BUCKET_NAME"
fi

# Set bucket permissions for public read (optional, for testing)
echo "🔐 Setting bucket permissions..."
gsutil iam ch allUsers:objectViewer gs://$BUCKET_NAME 2>/dev/null || echo "   ⚠️  Could not set public read on analysis bucket (this is optional)"
gsutil iam ch allUsers:objectViewer gs://$RENDERS_BUCKET_NAME 2>/dev/null || echo "   ⚠️  Could not set public read on renders bucket (this is optional)"

# Create service account if it doesn't exist
echo "👤 Setting up service account..."
if gcloud iam service-accounts describe $SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com &>/dev/null; then
    echo "   ✅ Service account already exists"
else
    gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
        --description="Service account for Image Assistant Service" \
        --display-name="Image Assistant Service Account"
    echo "   ✅ Created service account: $SERVICE_ACCOUNT_NAME"
    
    # Wait a few seconds for service account to propagate
    echo "   ⏳ Waiting for service account to propagate..."
    sleep 5
fi

# Grant necessary permissions
echo "🔑 Granting permissions to service account..."

# AI Platform User role for Vertex AI/Gemini access
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user" || echo "   ⚠️  AI Platform role already assigned or failed"

# Storage Admin role for GCS access
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.admin" || echo "   ⚠️  Storage role already assigned or failed"

# ML Developer role for Vision API access (includes Vision API permissions)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/ml.developer" || echo "   ⚠️  ML Developer role already assigned or failed"

echo "   ✅ Permissions granted successfully"

# Create and download service account key
echo "🔐 Creating service account key..."
if [ -f "$KEY_FILE" ]; then
    echo "   ⚠️  Key file already exists, skipping..."
else
    gcloud iam service-accounts keys create $KEY_FILE \
        --iam-account=$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com
    echo "   ✅ Downloaded key to: $KEY_FILE"
fi

# Create Python virtual environment if it doesn't exist
echo "🐍 Setting up Python environment..."
if [ ! -d "env" ]; then
    python3 -m venv env
    echo "   ✅ Created virtual environment"
else
    echo "   ✅ Virtual environment already exists"
fi

# Activate virtual environment and install dependencies
echo "📦 Installing dependencies..."
source env/bin/activate

# Upgrade pip first
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
echo "   ✅ Dependencies installed"

# Generate gRPC code
echo "🔧 Generating gRPC code..."
./genproto.sh

# Create .env file
echo "📝 Creating .env file..."
cat > .env << EOF
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=$PROJECT_ID
GOOGLE_CLOUD_REGION=$REGION
GOOGLE_APPLICATION_CREDENTIALS=$(pwd)/$KEY_FILE

# GCS Configuration
GCS_BUCKET=$BUCKET_NAME
GCS_RENDERS_BUCKET=$RENDERS_BUCKET_NAME

# Server Configuration
PORT=8080
HTTP_PORT=8000
ENABLE_HTTP=true

# Logging
LOG_LEVEL=INFO

# Development flags
DEBUG=false

# Gemini API Key (required for StyleAnalyzer)
GEMINI_API_KEY=your-gemini-api-key-here
EOF

echo "   ✅ Created .env file with:"
echo "      - Project: $PROJECT_ID"
echo "      - Analysis Bucket: $BUCKET_NAME"
echo "      - Renders Bucket: $RENDERS_BUCKET_NAME"
echo "      - Key file: $KEY_FILE"

# Test bucket access
echo "🧪 Testing bucket access..."
echo "test" | gsutil cp - gs://$BUCKET_NAME/test.txt
gsutil rm gs://$BUCKET_NAME/test.txt
echo "   ✅ Analysis bucket access confirmed"

echo "test-render" | gsutil cp - gs://$RENDERS_BUCKET_NAME/test-render.txt
gsutil rm gs://$RENDERS_BUCKET_NAME/test-render.txt
echo "   ✅ Renders bucket access confirmed"

# Tests are available but not run during setup
echo "🔍 Service tests are available:"
echo "   - Image analysis test: python test_image_analyzer_local.py"
echo "   - Product visualization test: python test_product_visualizer_local.py"
echo "   Run these after starting the server to verify functionality."

echo ""
echo "🎉 Setup complete! Summary:"
echo ""
echo "✅ Google Cloud APIs enabled:"
echo "   - Vision API"
echo "   - AI Platform (Vertex AI)"
echo "   - Cloud Storage"
echo ""
echo "✅ Resources created:"
echo "   - Analysis GCS Bucket: gs://$BUCKET_NAME"
echo "   - Renders GCS Bucket: gs://$RENDERS_BUCKET_NAME"
echo "   - Service Account: $SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com"
echo "   - Service Account Key: $KEY_FILE"
echo ""
echo "✅ Environment configured:"
echo "   - Python virtual environment: ./env"
echo "   - Dependencies installed"
echo "   - gRPC code generated"
echo "   - Environment file: .env"
echo ""
echo "🚀 Ready to run! Next steps:"
echo ""
echo "1. Activate environment: source env/bin/activate"
echo "2. Run the service: python server.py"
echo "3. Test image analysis: python test_image_analyzer_local.py"
echo "4. Test product visualization: python test_product_visualizer_local.py"
echo ""
echo "⚠️  Security notes:"
echo "   - Keep service-account-key.json secure"
echo "   - Never commit the key file to version control"
echo "   - Add service-account-key.json to .gitignore"
echo ""
echo "🔑 Additional setup required:"
echo "   - Get a Gemini API key from Google AI Studio:"
echo "     https://aistudio.google.com/app/apikey"
echo "   - Update GEMINI_API_KEY in .env file"
echo "   - The StyleAnalyzer needs this for intelligent style detection" 