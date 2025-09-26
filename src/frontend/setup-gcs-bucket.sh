#!/bin/bash

# Setup GCS Bucket for User Image Uploads
# This script creates the necessary GCS bucket for the direct upload feature

PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"gke-hack-471804"}
BUCKET_NAME="${PROJECT_ID}-user-uploads"

echo "🚀 Setting up GCS bucket for image uploads..."
echo "Project ID: $PROJECT_ID"
echo "Bucket Name: $BUCKET_NAME"

# Create bucket if it doesn't exist
if ! gsutil ls -b gs://$BUCKET_NAME >/dev/null 2>&1; then
    echo "📦 Creating GCS bucket: $BUCKET_NAME"
    gsutil mb -p $PROJECT_ID gs://$BUCKET_NAME
    
    # Set bucket lifecycle (delete objects after 7 days)
    echo "⏰ Setting lifecycle policy (delete after 7 days)"
    cat > lifecycle.json << EOF
{
  "rule": [
    {
      "action": {"type": "Delete"},
      "condition": {"age": 7}
    }
  ]
}
EOF
    
    gsutil lifecycle set lifecycle.json gs://$BUCKET_NAME
    rm lifecycle.json
    
    # Set CORS policy for browser uploads
    echo "🌐 Setting CORS policy for browser uploads"
    cat > cors.json << EOF
[
  {
    "origin": ["*"],
    "method": ["GET", "POST", "PUT"],
    "responseHeader": ["Content-Type"],
    "maxAgeSeconds": 3600
  }
]
EOF
    
    gsutil cors set cors.json gs://$BUCKET_NAME
    rm cors.json
    
    echo "✅ GCS bucket created and configured successfully!"
else
    echo "✅ GCS bucket already exists: $BUCKET_NAME"
fi

# Set environment variables
echo ""
echo "🔧 Environment Variables to set:"
echo "export GOOGLE_CLOUD_PROJECT=$PROJECT_ID"
echo "export GCS_UPLOADS_BUCKET=$BUCKET_NAME"

echo ""
echo "🎉 GCS setup complete! You can now upload images directly from the frontend." 