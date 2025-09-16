#!/bin/bash

# Setup Orders Database for Checkout Service
# This script creates the orders database and tables in the existing PRIVATE Cloud SQL instance

set -euo pipefail

# Configuration - Match the PRIVATE Cloud SQL setup (same as cart/product services)
PROJECT_ID="gke-hack-471804"
CLOUDSQL_INSTANCE="onlineboutique-instance-private"  # Private instance
REGION="us-central1"
CLOUDSQL_PRIVATE_IP="10.103.0.3"  # Private IP (same as cart/product)
DATABASE_NAME="orders"
SECRET_NAME="cloudsql-secret-private"  
CLOUDSQL_USER_GSA_NAME="cloudsql-user-sa-private"  
PGPASSWORD="Admin123"  

echo "🗃️ Setting up Orders Database for Checkout Service..."
echo "=================================================="
echo "🔒 Using PRIVATE Cloud SQL (same as cart/product services)"
echo "📍 Private IP: ${CLOUDSQL_PRIVATE_IP}"

# Function to create database
create_database() {
    echo "📦 Creating orders database..."
    
    # Create the database
    gcloud sql databases create ${DATABASE_NAME} \
        --instance=${CLOUDSQL_INSTANCE} \
        --project=${PROJECT_ID} \
        2>/dev/null || echo "Database ${DATABASE_NAME} already exists"
    
    echo "✅ Database '${DATABASE_NAME}' is ready"
}

# Function to create tables using VM jumpbox (matching private setup pattern)
create_tables_via_jumpbox() {
    echo "🛠️ Creating tables via jumpbox VM..."
    echo "Using private IP: ${CLOUDSQL_PRIVATE_IP}"
    
    # Create the tables SQL directly via gcloud compute ssh (matching private setup)
    echo "Creating order_history table..."
    gcloud compute ssh alloydb-jumpbox --zone=us-central1-a \
        --command="PGPASSWORD='${PGPASSWORD}' psql -h ${CLOUDSQL_PRIVATE_IP} -U postgres -d ${DATABASE_NAME} -c 'CREATE TABLE IF NOT EXISTS order_history (order_id VARCHAR(255) PRIMARY KEY, user_id VARCHAR(255) NOT NULL, email VARCHAR(255), total_amount_currency VARCHAR(10), total_amount_units BIGINT, total_amount_nanos INTEGER, shipping_tracking_id VARCHAR(255), shipping_address TEXT, order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, status VARCHAR(50) DEFAULT '\''completed'\'');'"
    
    echo "Creating order_items table..."
    gcloud compute ssh alloydb-jumpbox --zone=us-central1-a \
        --command="PGPASSWORD='${PGPASSWORD}' psql -h ${CLOUDSQL_PRIVATE_IP} -U postgres -d ${DATABASE_NAME} -c 'CREATE TABLE IF NOT EXISTS order_items (id SERIAL PRIMARY KEY, order_id VARCHAR(255) REFERENCES order_history(order_id) ON DELETE CASCADE, product_id VARCHAR(255) NOT NULL, quantity INTEGER NOT NULL, unit_price_currency VARCHAR(10), unit_price_units BIGINT, unit_price_nanos INTEGER, total_price_currency VARCHAR(10), total_price_units BIGINT, total_price_nanos INTEGER);'"
    
    echo "Creating indexes for performance..."
    gcloud compute ssh alloydb-jumpbox --zone=us-central1-a \
        --command="PGPASSWORD='${PGPASSWORD}' psql -h ${CLOUDSQL_PRIVATE_IP} -U postgres -d ${DATABASE_NAME} -c 'CREATE INDEX IF NOT EXISTS idx_order_history_user_id ON order_history(user_id); CREATE INDEX IF NOT EXISTS idx_order_history_date ON order_history(order_date); CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id); CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);'"
    
    echo "✅ Orders tables created successfully"
}

# Function to setup Workload Identity for checkoutservice
setup_workload_identity() {
    echo "🔗 Setting up Workload Identity for checkoutservice..."
    
    # Add checkoutservice to the existing PRIVATE GSA
    gcloud iam service-accounts add-iam-policy-binding \
        ${CLOUDSQL_USER_GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com \
        --member="serviceAccount:${PROJECT_ID}.svc.id.goog[default/checkoutservice]" \
        --role=roles/iam.workloadIdentityUser \
        2>/dev/null || echo "Workload Identity binding already exists"
    
    echo "✅ Workload Identity configured for checkoutservice"
}

# Function to verify setup
verify_setup() {
    echo "🔍 Verifying orders database setup..."
    
    # Check if tables exist using jumpbox VM
    echo "Checking tables in orders database:"
    gcloud compute ssh alloydb-jumpbox --zone=us-central1-a \
        --command="PGPASSWORD='${PGPASSWORD}' psql -h ${CLOUDSQL_PRIVATE_IP} -U postgres -d ${DATABASE_NAME} -c '\dt'"
    
    echo "✅ Orders database verification complete"
}

# Main execution
main() {
    echo "Starting orders database setup..."
    echo "Project: ${PROJECT_ID}"
    echo "Instance: ${CLOUDSQL_INSTANCE} (PRIVATE)"
    echo "Database: ${DATABASE_NAME}"
    echo "Secret: ${SECRET_NAME} (PRIVATE)"
    echo "GSA: ${CLOUDSQL_USER_GSA_NAME} (PRIVATE)"
    echo "Private IP: ${CLOUDSQL_PRIVATE_IP}"
    echo ""
    
    # Create database
    create_database
    
    # Create tables
    create_tables_via_jumpbox
    
    # Setup Workload Identity for checkoutservice
    setup_workload_identity
    
    # Verify setup
    verify_setup
    
    echo ""
    echo "🎉 Orders database setup complete!"
    echo ""
    echo "📝 Next steps:"
    echo "1. Build and deploy updated checkoutservice:"
    echo "   cd src/checkoutservice"
    echo "   docker build -t gcr.io/${PROJECT_ID}/checkoutservice-orders:latest ."
    echo "   docker push gcr.io/${PROJECT_ID}/checkoutservice-orders:latest"
    echo ""
    echo "2. Deploy with: kubectl apply -k kubernetes-manifests/"
    echo ""
    echo "3. Test order placement to verify order history is persisted"
    echo ""
    echo "🔒 Using PRIVATE Cloud SQL instance: ${CLOUDSQL_INSTANCE}"
    echo "🔑 Using private secret: ${SECRET_NAME}"
    echo "👤 Using private GSA: ${CLOUDSQL_USER_GSA_NAME}"
    echo ""
    echo "🎯 Environment variables for checkout service (PRIVATE CONFIG):"
    echo "   - CLOUDSQL_HOST: ${CLOUDSQL_PRIVATE_IP}"
    echo "   - ALLOYDB_DATABASE_NAME: ${DATABASE_NAME}"
    echo "   - ALLOYDB_SECRET_NAME: ${SECRET_NAME}"
    echo ""
    echo "✅ Matches cart and product services configuration!"
}

# Run main function
main "$@" 