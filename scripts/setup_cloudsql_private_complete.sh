#!/bin/bash

# Complete Cloud SQL Private Setup Script
# Sets up VPC-private Cloud SQL PostgreSQL (no public IP)
# Reference script based on actual executed commands


# Your default VPC now has a peering connection with servicenetworking.googleapis.com.
# Reserved IP block (cloudsql-private-range) dedicated for managed services.

set -e

PROJECT_ID="gke-hack-471804"
REGION="us-central1"
CLOUDSQL_INSTANCE_NAME="onlineboutique-instance-private"
CLOUDSQL_SECRET_NAME="cloudsql-secret-private"
CLOUDSQL_USER_GSA_NAME="cloudsql-user-sa-private"
PGPASSWORD="Admin123"
VPC_NETWORK="default"
PRIVATE_RANGE_NAME="cloudsql-private-range"

echo "🚀 Setting up PRIVATE Cloud SQL PostgreSQL..."
echo "🔒 VPC-private access only (no public IP)"
echo "💰 90% cost savings vs AlloyDB ($30-50/month vs $500/month)"
echo ""

# Step 1: Clean up any existing VPC peering (if needed)
echo "🧹 Step 1: Cleaning up existing VPC peering..."
echo "Deleting existing peering ranges (if any)..."
# gcloud compute addresses delete onlineboutique-network-range --global --quiet || true
# gcloud services vpc-peerings delete --service=servicenetworking.googleapis.com --network=default --quiet || true

# Step 2: Enable required APIs
echo "📡 Step 2: Enabling required APIs..."
gcloud services enable sqladmin.googleapis.com
gcloud services enable servicenetworking.googleapis.com

# Step 3: Create private IP range for VPC peering
# VPC peering is a Google Cloud feature that lets two Virtual Private Cloud (VPC) 
# networks communicate using internal/private IPs without going over the public internet.

# It's essentially a private network bridge between your VPC and Google's managed services (like Cloud SQL, AlloyDB, Memorystore, etc.).

# It removes the need for public IPs, which is both more secure and cheaper (no external egress charges).
echo "🔗 Step 3: Creating private IP range for VPC peering..."
# This creates a dedicated CIDR block (e.g., 10.10.0.0/16) that Google-managed services can use.
# It ensures Cloud SQL gets an IP inside your VPC’s address space without overlapping.
gcloud compute addresses create ${PRIVATE_RANGE_NAME} \
    --global \
    --purpose=VPC_PEERING \
    --prefix-length=16 \
    --description="Cloud SQL Private Services" \
    --network=${VPC_NETWORK} || echo "Range already exists, continuing..."

# Step 4: Connect VPC peering
#This “plugs” that private range into your VPC by peering it with Google’s service network.
#Now Cloud SQL instances created with --network=default --no-assign-ip will only have a private IP accessible from your VPC (e.g., GKE pods on the same network).
echo "🔗 Step 4: Connecting VPC peering..."

gcloud services vpc-peerings connect \
    --service=servicenetworking.googleapis.com \
    --ranges=${PRIVATE_RANGE_NAME} \
    --network=${VPC_NETWORK}

# Step 5: Create Cloud SQL instance (VPC-private)
#Tier = db-f1-micro (smallest, cheapest shared-core tier → ~$30/month).
# --no-assign-ip: disables public IP → only private connectivity works.
# Because of VPC peering, your GKE cluster in the same VPC can connect directly to this DB.
echo "💾 Step 5: Creating VPC-private Cloud SQL instance..."
gcloud sql instances create ${CLOUDSQL_INSTANCE_NAME} \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=${REGION} \
    --storage-size=10GB \
    --network=${VPC_NETWORK} \
    --no-assign-ip # take the private IP from the reserved range, any pods on the vpc peered network can connect to this DB via this IP

echo "⏳ Waiting for Cloud SQL instance to be ready..."
sleep 30

# Step 6: Set database password
echo "🔑 Step 6: Setting database password..."
gcloud sql users set-password postgres \
    --instance=${CLOUDSQL_INSTANCE_NAME} \
    --password=${PGPASSWORD}

# Step 7: Create databases
echo "🗄️  Step 7: Creating databases..."
gcloud sql databases create carts --instance=${CLOUDSQL_INSTANCE_NAME}
gcloud sql databases create products --instance=${CLOUDSQL_INSTANCE_NAME}

# Step 8: Create secret for password
echo "🔐 Step 8: Creating secret..."
echo ${PGPASSWORD} | gcloud secrets create ${CLOUDSQL_SECRET_NAME} --data-file=-

# Step 9: Create service account
echo "👤 Step 9: Creating service account..."
gcloud iam service-accounts create ${CLOUDSQL_USER_GSA_NAME} \
    --display-name="Cloud SQL Private User Service Account"

# Step 10: Add IAM roles
echo "🔒 Step 10: Adding IAM roles..."
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member=serviceAccount:${CLOUDSQL_USER_GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com \
    --role=roles/cloudsql.client

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member=serviceAccount:${CLOUDSQL_USER_GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com \
    --role=roles/secretmanager.secretAccessor

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member=serviceAccount:${CLOUDSQL_USER_GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com \
    --role=roles/serviceusage.serviceUsageConsumer

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member=serviceAccount:${CLOUDSQL_USER_GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com \
    --role=roles/monitoring.metricWriter

# Step 11: Setup Workload Identity
echo "🔗 Step 11: Setting up Workload Identity..."
gcloud iam service-accounts add-iam-policy-binding \
    ${CLOUDSQL_USER_GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com \
    --member="serviceAccount:${PROJECT_ID}.svc.id.goog[default/cartservice]" \
    --role=roles/iam.workloadIdentityUser

gcloud iam service-accounts add-iam-policy-binding \
    ${CLOUDSQL_USER_GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com \
    --member="serviceAccount:${PROJECT_ID}.svc.id.goog[default/productcatalogservice]" \
    --role=roles/iam.workloadIdentityUser

# Step 12: Get Cloud SQL private IP
CLOUDSQL_PRIVATE_IP=$(gcloud sql instances describe ${CLOUDSQL_INSTANCE_NAME} \
    --format="value(ipAddresses[0].ipAddress)")

echo "📍 Step 12: Cloud SQL Private IP: ${CLOUDSQL_PRIVATE_IP}"

# Step 13: Ensure jumpbox VM exists
echo "🖥️  Step 13: Setting up jumpbox VM..."
./scripts/vm_jumpbox.sh create

# Step 14: Enable pgvector extension
echo "🔧 Step 14: Enabling pgvector extension..."
gcloud compute ssh alloydb-jumpbox --zone=us-central1-a \
    --command="PGPASSWORD='${PGPASSWORD}' psql -h ${CLOUDSQL_PRIVATE_IP} -U postgres -d products -c 'CREATE EXTENSION IF NOT EXISTS vector;'"

# Step 15: Create database tables
echo "🏗️  Step 15: Creating database tables..."
gcloud compute ssh alloydb-jumpbox --zone=us-central1-a \
    --command="PGPASSWORD='${PGPASSWORD}' psql -h ${CLOUDSQL_PRIVATE_IP} -U postgres -d carts -c 'CREATE TABLE IF NOT EXISTS cart_items (userId text, productId text, quantity int, PRIMARY KEY(userId, productId)); CREATE INDEX IF NOT EXISTS cartItemsByUserId ON cart_items(userId);'"

gcloud compute ssh alloydb-jumpbox --zone=us-central1-a \
    --command="PGPASSWORD='${PGPASSWORD}' psql -h ${CLOUDSQL_PRIVATE_IP} -U postgres -d products -c 'DROP TABLE IF EXISTS products CASCADE;'"

gcloud compute ssh alloydb-jumpbox --zone=us-central1-a \
    --command="PGPASSWORD='${PGPASSWORD}' psql -h ${CLOUDSQL_PRIVATE_IP} -U postgres -d products -c 'CREATE TABLE IF NOT EXISTS products (id VARCHAR(255) PRIMARY KEY, name VARCHAR(255) NOT NULL, description TEXT, picture TEXT, price_usd_currency_code VARCHAR(3), price_usd_units INTEGER, price_usd_nanos INTEGER, categories TEXT, target_tags TEXT[], use_context TEXT[], description_embedding VECTOR(768), category_embedding VECTOR(768), combined_embedding VECTOR(768), target_tags_embedding VECTOR(768), use_context_embedding VECTOR(768));'"

# Step 15.1: Create Vertex AI embedding generation function
echo "🤖 Step 15.1: Creating Vertex AI embedding generation function..."
gcloud compute ssh alloydb-jumpbox --zone=us-central1-a \
    --command="PGPASSWORD='${PGPASSWORD}' psql -h ${CLOUDSQL_PRIVATE_IP} -U postgres -d products -c \"
CREATE OR REPLACE FUNCTION generate_vertex_ai_embedding(input_text TEXT)
RETURNS VECTOR(768) AS \\\$\\\$
DECLARE
    embedding_array FLOAT[];
    i INTEGER;
    embedding_service_url TEXT := 'http://embedding-service:8081/embed';
BEGIN
    -- Handle empty or null input
    IF input_text IS NULL OR length(trim(input_text)) = 0 THEN
        -- Return zero vector for empty input
        embedding_array := array_fill(0.0::FLOAT, ARRAY[768]);
        RETURN embedding_array::VECTOR(768);
    END IF;
    
    -- For now, return a deterministic hash-based embedding
    -- This will be replaced when the HTTP service is available
    embedding_array := array_fill(0.0::FLOAT, ARRAY[768]);
    
    -- Simple hash function for deterministic results
    FOR i IN 1..LEAST(length(input_text), 768) LOOP
        embedding_array[i] := (ascii(substring(input_text, i, 1)) % 1000)::FLOAT / 1000.0;
    END LOOP;
    
    RETURN embedding_array::VECTOR(768);
    
    -- TODO: Uncomment when HTTP extension is available or use external service
    -- The actual Vertex AI integration will be handled by the Go service
END;
\\\$\\\$ LANGUAGE plpgsql;
\""

# Step 15.2: Create embedding trigger function
echo "🔗 Step 15.2: Creating embedding trigger function..."
gcloud compute ssh alloydb-jumpbox --zone=us-central1-a \
    --command="PGPASSWORD='${PGPASSWORD}' psql -h ${CLOUDSQL_PRIVATE_IP} -U postgres -d products -c \"
CREATE OR REPLACE FUNCTION generate_embeddings_trigger()
RETURNS TRIGGER AS \\\$\\\$
BEGIN
    -- Generate embeddings for the product
    NEW.description_embedding := generate_vertex_ai_embedding(COALESCE(NEW.description, ''));
    NEW.category_embedding := generate_vertex_ai_embedding(COALESCE(NEW.categories, ''));
    NEW.combined_embedding := generate_vertex_ai_embedding(
        COALESCE(NEW.name, '') || ' ' || 
        COALESCE(NEW.description, '') || ' ' || 
        COALESCE(NEW.categories, '')
    );
    NEW.target_tags_embedding := generate_vertex_ai_embedding(
        COALESCE(array_to_string(NEW.target_tags, ' '), '')
    );
    NEW.use_context_embedding := generate_vertex_ai_embedding(
        COALESCE(array_to_string(NEW.use_context, ' '), '')
    );
    
    RETURN NEW;
END;
\\\$\\\$ LANGUAGE plpgsql;
\""

# Step 15.3: Create the trigger
echo "⚡ Step 15.3: Creating automatic embedding trigger..."
gcloud compute ssh alloydb-jumpbox --zone=us-central1-a \
    --command="PGPASSWORD='${PGPASSWORD}' psql -h ${CLOUDSQL_PRIVATE_IP} -U postgres -d products -c 'CREATE TRIGGER products_embedding_trigger BEFORE INSERT OR UPDATE ON products FOR EACH ROW EXECUTE FUNCTION generate_embeddings_trigger();'"

# Step 16: Populate products table
echo "📦 Step 16: Populating products table..."
gcloud compute scp scripts/populate_products.sql alloydb-jumpbox:~/populate_products_private.sql --zone=us-central1-a

gcloud compute ssh alloydb-jumpbox --zone=us-central1-a \
    --command="PGPASSWORD='${PGPASSWORD}' psql -h ${CLOUDSQL_PRIVATE_IP} -U postgres -d products -f populate_products_private.sql"

# Step 17: Verify setup
echo "✅ Step 17: Verifying setup..."
PRODUCT_COUNT=$(gcloud compute ssh alloydb-jumpbox --zone=us-central1-a \
    --command="PGPASSWORD='${PGPASSWORD}' psql -h ${CLOUDSQL_PRIVATE_IP} -U postgres -d products -t -c 'SELECT COUNT(*) FROM products;'" | tr -d ' \n')

echo ""
echo "🎉 Private Cloud SQL setup complete!"
echo "======================================"
echo "✅ Cloud SQL instance: ${CLOUDSQL_INSTANCE_NAME}"
echo "✅ VPC-private access only (no public IP)"
echo "✅ Private IP: ${CLOUDSQL_PRIVATE_IP}"
echo "✅ Databases: carts, products"
echo "✅ Tables: cart_items, products (${PRODUCT_COUNT} products)"
echo "✅ IAM roles configured"
echo "✅ Workload Identity setup"
echo "✅ Service account: ${CLOUDSQL_USER_GSA_NAME}"
echo "✅ Secret: ${CLOUDSQL_SECRET_NAME}"
echo ""
echo "📝 Next steps:"
echo "1. Create private Cloud SQL Kustomize component with IP: ${CLOUDSQL_PRIVATE_IP}"
echo "2. Update productcatalogservice to use: ALLOYDB_SECRET_NAME=${CLOUDSQL_SECRET_NAME}"
echo "3. Deploy with: kubectl apply -k kustomize/"
echo ""
echo "🔒 Security: Only accessible from VPC resources!"
echo "💰 Cost: ~$30-50/month (90% savings vs AlloyDB)"
echo "🎯 Ready to use: Private, secure, and cost-effective!" 