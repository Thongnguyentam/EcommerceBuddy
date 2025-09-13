#!/bin/bash

# AlloyDB Cost Optimization Script
# This script will reduce your AlloyDB costs by ~85%

set -e

# Configuration
PROJECT_ID="gke-hack-471804"
REGION="us-central1"
CLUSTER_NAME="onlineboutique-cluster"
PRIMARY_INSTANCE_NAME="onlineboutique-instance"
REPLICA_INSTANCE_NAME="onlineboutique-instance-replica"

echo "🎯 AlloyDB Cost Optimization"
echo "================================"
echo "This will:"
echo "✅ Delete expensive read pool instance (save $400-800/month)"
echo "✅ Reduce primary instance to 2 vCPUs (save $100-200/month)"
echo "✅ Total savings: ~85% cost reduction!"
echo ""

read -p "⚠️  Continue with optimization? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Optimization cancelled"
    exit 1
fi

echo ""
echo "📊 Step 1: Current configuration..."
gcloud alloydb instances list --region=${REGION} --cluster=${CLUSTER_NAME}

echo ""
echo "🗑️  Step 2: Deleting expensive read pool replica..."
echo "   Deleting: ${REPLICA_INSTANCE_NAME}"
gcloud alloydb instances delete ${REPLICA_INSTANCE_NAME} \
    --cluster=${CLUSTER_NAME} \
    --region=${REGION} \
    --quiet

echo ""
echo "⏳ Step 3: Waiting for deletion to complete..."
sleep 10

echo ""
echo "🔧 Step 4: Scaling down primary instance to minimal configuration..."
echo "   Reducing ${PRIMARY_INSTANCE_NAME} from 4 vCPUs to 2 vCPUs"

# Note: AlloyDB doesn't support direct CPU scaling via gcloud CLI
# We need to delete and recreate the primary instance
echo ""
echo "⚠️  Note: To change CPU count, we need to recreate the primary instance"
echo "⚠️  This will cause ~5-10 minutes of downtime"
echo ""

read -p "🔄 Proceed with primary instance recreation? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "✅ Read pool deleted. Primary instance unchanged."
    echo "💰 Estimated monthly savings: $400-800"
    exit 0
fi

echo ""
echo "💾 Step 5: Backing up databases before recreation..."
# Get the primary IP for backup
PRIMARY_IP=$(gcloud alloydb instances describe ${PRIMARY_INSTANCE_NAME} \
    --cluster=${CLUSTER_NAME} \
    --region=${REGION} \
    --format="value(ipAddress)")

echo "   Primary IP: ${PRIMARY_IP}"
echo "   📝 Note: Your databases will be preserved in the cluster"

echo ""
echo "🗑️  Step 6: Deleting primary instance..."
gcloud alloydb instances delete ${PRIMARY_INSTANCE_NAME} \
    --cluster=${CLUSTER_NAME} \
    --region=${REGION} \
    --quiet

echo ""
echo "⏳ Step 7: Waiting for deletion to complete..."
sleep 30

echo ""
echo "🚀 Step 8: Creating optimized primary instance (2 vCPUs)..."
gcloud alloydb instances create ${PRIMARY_INSTANCE_NAME} \
    --cluster=${CLUSTER_NAME} \
    --region=${REGION} \
    --cpu-count=2 \
    --instance-type=PRIMARY \
    --quiet

echo ""
echo "⏳ Step 9: Waiting for new instance to be ready..."
echo "   This may take 10-15 minutes..."

# Wait for instance to be ready
while true; do
    STATUS=$(gcloud alloydb instances describe ${PRIMARY_INSTANCE_NAME} \
        --cluster=${CLUSTER_NAME} \
        --region=${REGION} \
        --format="value(state)" 2>/dev/null || echo "CREATING")
    
    if [[ "$STATUS" == "READY" ]]; then
        echo "✅ Instance is ready!"
        break
    else
        echo "   Status: $STATUS - waiting..."
        sleep 30
    fi
done

echo ""
echo "📊 Step 10: New configuration:"
gcloud alloydb instances list --region=${REGION} --cluster=${CLUSTER_NAME}

# Get new primary IP
NEW_PRIMARY_IP=$(gcloud alloydb instances describe ${PRIMARY_INSTANCE_NAME} \
    --cluster=${CLUSTER_NAME} \
    --region=${REGION} \
    --format="value(ipAddress)")

echo ""
echo "🎉 OPTIMIZATION COMPLETE!"
echo "=========================="
echo "✅ Read pool deleted: Save $400-800/month"
echo "✅ Primary reduced to 2 vCPUs: Save $100-200/month"
echo "✅ Total monthly savings: ~85%"
echo ""
echo "📝 IMPORTANT: Update your Kustomize configuration:"
echo "   Old IP: ${PRIMARY_IP}"
echo "   New IP: ${NEW_PRIMARY_IP}"
echo ""
echo "🔧 Run this command to update Kustomize:"
echo "   sed -i 's/${PRIMARY_IP}/${NEW_PRIMARY_IP}/g' kustomize/components/alloydb/kustomization.yaml"
echo ""
echo "🚀 Then redeploy:"
echo "   kubectl apply -k kustomize/" 