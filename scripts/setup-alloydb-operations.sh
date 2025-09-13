#!/bin/bash

# ==============================================================================
# Online Boutique - AlloyDB + Google Cloud Operations Setup Script
# ==============================================================================

set -e  # Exit on any error

echo "🚀 Setting up Online Boutique with AlloyDB and Google Cloud Operations"

# Get current authenticated account
CURRENT_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1)
echo "   ✅ Authenticated as: $CURRENT_ACCOUNT"

# ==============================================================================
# CONFIGURATION - EDIT THESE VALUES
# ==============================================================================

export PROJECT_ID="gke-hack-471804"

export REGION="us-central1"
export ALLOYDB_NETWORK="default"
export ALLOYDB_SERVICE_NAME="onlineboutique-network-range"
export ALLOYDB_CLUSTER_NAME="onlineboutique-cluster"
export ALLOYDB_INSTANCE_NAME="onlineboutique-instance"

# **Note:** Primary and Read IP will need to be set after you create the instance. 
# The command to set this in the shell is included below, but it would also be a good idea to run the command, and manually set the IP address in the .bashrc
export ALLOYDB_DATABASE_NAME="carts"
export ALLOYDB_TABLE_NAME="cart_items"
export ALLOYDB_USER_GSA_NAME="alloydb-user-sa"
export CARTSERVICE_KSA_NAME="cartservice"
export ALLOYDB_SECRET_NAME="alloydb-secret"

# PGPASSWORD needs to be set in order to run the psql from the CLI easily. The value for this
# needs to be set behind the Secret mentioned above
export PGPASSWORD="Admin123"

# Derived variables
export USE_GKE_GCLOUD_AUTH_PLUGIN=True
export ALLOYDB_USER_GSA_ID="${ALLOYDB_USER_GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# ==============================================================================
# VALIDATION
# ==============================================================================

# Check if user has access to the project
echo "   Checking project access..."
if ! gcloud projects describe ${PROJECT_ID} &> /dev/null; then
    echo "❌ ERROR: Cannot access project '${PROJECT_ID}'"
    echo "   Possible issues:"
    echo "   1. Project ID is incorrect"
    echo "   2. You don't have access to this project"
    echo "   3. Project doesn't exist"
    echo ""
    echo "   Please check:"
    echo "   - Your project ID in this script"
    echo "   - Your permissions in Google Cloud Console"
    exit 1
fi

echo "   ✅ Project access confirmed"

echo ""
echo "📋 Configuration:"
echo "   Project ID: $PROJECT_ID"
echo "   Region: $REGION"
echo "   AlloyDB Cluster: $ALLOYDB_CLUSTER_NAME"
echo "   Authenticated as: $CURRENT_ACCOUNT"

# ==============================================================================
# STEP 1: SETUP GOOGLE CLOUD PROJECT
# ==============================================================================

echo ""
echo "🔧 Step 1: Setting up Google Cloud project..."

gcloud config set project ${PROJECT_ID}

echo "   Enabling required APIs (this may take a few minutes)..."
gcloud services enable \
    container.googleapis.com \
    alloydb.googleapis.com \
    servicenetworking.googleapis.com \
    secretmanager.googleapis.com \
    monitoring.googleapis.com \
    cloudtrace.googleapis.com \
    cloudprofiler.googleapis.com

# ==============================================================================
# STEP 2: CREATE GKE CLUSTER
# ==============================================================================

echo ""
echo "🏗️  Step 2: Creating GKE cluster with Workload Identity..."

# Creates a GKE Autopilot cluster named online-boutique
# Autopilot clusters have Workload Identity enabled by default
echo "   Note: Autopilot clusters have Workload Identity enabled by default"

gcloud container clusters create-auto online-boutique \
    --project=${PROJECT_ID} \
    --region=${REGION}


# Downloads and configures kubectl credentials for the newly created cluster.
# Updates your local ~/.kube/config so that when you run kubectl, it connects to the online-boutique cluster in the specified project and region.
# After this, you can deploy workloads with kubectl apply, check pods, etc.

echo "   Getting cluster credentials..."
gcloud container clusters get-credentials online-boutique \
    --region=${REGION} \
    --project=${PROJECT_ID}

# ==============================================================================
# STEP 3: SETUP ALLOYDB INFRASTRUCTURE
# ==============================================================================

echo ""
echo "🗄️  Step 3: Setting up AlloyDB infrastructure..."

echo "   Creating secret for database password..."
echo ${PGPASSWORD} | gcloud secrets create ${ALLOYDB_SECRET_NAME} --data-file=-

echo "   Setting up VPC peering for AlloyDB..."
gcloud compute addresses create ${ALLOYDB_SERVICE_NAME} \
    --global \
    --purpose=VPC_PEERING \
    --prefix-length=16 \
    --description="Online Boutique Private Services" \
    --network=${ALLOYDB_NETWORK}

gcloud services vpc-peerings connect \
    --service=servicenetworking.googleapis.com \
    --ranges=${ALLOYDB_SERVICE_NAME} \
    --network=${ALLOYDB_NETWORK}

echo "   Creating AlloyDB cluster (this takes ~20 minutes)..."
gcloud alloydb clusters create ${ALLOYDB_CLUSTER_NAME} \
    --region=${REGION} \
    --password=${PGPASSWORD} \
    --disable-automated-backup \
    --network=${ALLOYDB_NETWORK}

echo "   Creating primary instance..."
gcloud alloydb instances create ${ALLOYDB_INSTANCE_NAME} \
    --cluster=${ALLOYDB_CLUSTER_NAME} \
    --region=${REGION} \
    --cpu-count=4 \
    --instance-type=PRIMARY
    
echo "   Creating read replica..."
gcloud alloydb instances create ${ALLOYDB_INSTANCE_NAME}-replica \
    --cluster=${ALLOYDB_CLUSTER_NAME} \
    --region=${REGION} \
    --cpu-count=4 \
    --instance-type=READ_POOL \
    --read-pool-node-count=2

# ==============================================================================
# STEP 4: GET ALLOYDB IPS AND CREATE DATABASE
# ==============================================================================

echo ""
echo "🔍 Step 4: Getting AlloyDB IPs and creating database..."

export ALLOYDB_PRIMARY_IP=$(gcloud alloydb instances list --region=${REGION} --cluster=${ALLOYDB_CLUSTER_NAME} --filter="INSTANCE_TYPE:PRIMARY" --format="value(ipAddress)")
export ALLOYDB_READ_IP=$(gcloud alloydb instances list --region=${REGION} --cluster=${ALLOYDB_CLUSTER_NAME} --filter="INSTANCE_TYPE:READ_POOL" --format="value(ipAddress)")

echo "   AlloyDB Primary IP: ${ALLOYDB_PRIMARY_IP}"
echo "   AlloyDB Read IP: ${ALLOYDB_READ_IP}"

echo "   Creating database and table..."
psql -h ${ALLOYDB_PRIMARY_IP} -U postgres -c "CREATE DATABASE ${ALLOYDB_DATABASE_NAME}"
psql -h ${ALLOYDB_PRIMARY_IP} -U postgres -d ${ALLOYDB_DATABASE_NAME} -c "CREATE TABLE ${ALLOYDB_TABLE_NAME} (userId text, productId text, quantity int, PRIMARY KEY(userId, productId))"
psql -h ${ALLOYDB_PRIMARY_IP} -U postgres -d ${ALLOYDB_DATABASE_NAME} -c "CREATE INDEX cartItemsByUserId ON ${ALLOYDB_TABLE_NAME}(userId)"

# ==============================================================================
# STEP 5: SETUP SERVICE ACCOUNTS AND IAM
# As a good practice, let's create a dedicated least privilege Google Service Account 
# to allow the cartservice to communicate with the AlloyDB database 
#and grab the database password from the Secret manager.

# ==============================================================================

echo ""
echo "🔐 Step 5: Setting up service accounts and IAM..."

echo "   Creating Google Service Account for AlloyDB access..."
gcloud iam service-accounts create ${ALLOYDB_USER_GSA_NAME} \
    --display-name=${ALLOYDB_USER_GSA_NAME}

echo "   Granting AlloyDB permissions..."
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member=serviceAccount:${ALLOYDB_USER_GSA_ID} \
    --role=roles/alloydb.client

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member=serviceAccount:${ALLOYDB_USER_GSA_ID} \
    --role=roles/secretmanager.secretAccessor

echo "   Setting up Workload Identity binding..."
gcloud iam service-accounts add-iam-policy-binding ${ALLOYDB_USER_GSA_ID} \
    --member "serviceAccount:${PROJECT_ID}.svc.id.goog[default/${CARTSERVICE_KSA_NAME}]" \
    --role roles/iam.workloadIdentityUser

echo "   Granting permissions for Google Cloud Operations..."
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member "serviceAccount:${PROJECT_ID}.svc.id.goog[default/default]" \
    --role roles/cloudtrace.agent

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member "serviceAccount:${PROJECT_ID}.svc.id.goog[default/default]" \
    --role roles/monitoring.metricWriter
  
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member "serviceAccount:${PROJECT_ID}.svc.id.goog[default/default]" \
    --role roles/cloudprofiler.agent

# ==============================================================================
# STEP 6: CONFIGURE KUSTOMIZE
# ==============================================================================

echo ""
echo "⚙️  Step 6: Configuring Kustomize for AlloyDB and Google Cloud Operations..."

cd kustomize

echo "   Components already added to kustomization.yaml"

echo "   Updating AlloyDB configuration with actual values..."
sed -i "s/PROJECT_ID_VAL/${PROJECT_ID}/g" components/alloydb/kustomization.yaml
sed -i "s/ALLOYDB_PRIMARY_IP_VAL/${ALLOYDB_PRIMARY_IP}/g" components/alloydb/kustomization.yaml
sed -i "s/ALLOYDB_USER_GSA_ID/${ALLOYDB_USER_GSA_ID}/g" components/alloydb/kustomization.yaml
sed -i "s/ALLOYDB_CARTS_DATABASE_NAME_VAL/${ALLOYDB_DATABASE_NAME}/g" components/alloydb/kustomization.yaml
sed -i "s/ALLOYDB_CARTS_TABLE_NAME_VAL/${ALLOYDB_TABLE_NAME}/g" components/alloydb/kustomization.yaml
sed -i "s/ALLOYDB_SECRET_NAME_VAL/${ALLOYDB_SECRET_NAME}/g" components/alloydb/kustomization.yaml

# ==============================================================================
# STEP 7: DEPLOY TO GKE
# ==============================================================================

echo ""
echo "🚀 Step 7: Deploying Online Boutique to GKE..."

echo "   Previewing configuration..."
kubectl kustomize .

echo ""
echo "   Applying configuration to GKE cluster..."
kubectl apply -k .

# ==============================================================================
# COMPLETION
# ==============================================================================

echo ""
echo "✅ Setup complete!"
echo ""
echo "📊 Monitoring & Observability:"
echo "   • Google Cloud Console: https://console.cloud.google.com/operations/tracing/overview?project=${PROJECT_ID}"
echo "   • Monitoring: https://console.cloud.google.com/monitoring?project=${PROJECT_ID}"
echo ""
echo "🗄️  AlloyDB:"
echo "   • Console: https://console.cloud.google.com/alloydb/clusters?project=${PROJECT_ID}"
echo "   • Primary IP: ${ALLOYDB_PRIMARY_IP}"
echo ""
echo "🔍 Check deployment status:"
echo "   kubectl get pods"
echo "   kubectl get service frontend-external"
echo ""
echo "🌐 Access the application:"
echo "   kubectl get service frontend-external | awk '{print \$4}'"
echo ""
echo "🧹 To clean up later, run:"
echo "   ./cleanup-alloydb-operations.sh" 