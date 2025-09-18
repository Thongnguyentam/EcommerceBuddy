#!/bin/bash

# Setup Reviews Database for Review Service
# This script creates the reviews database and tables in the existing PRIVATE Cloud SQL instance

set -euo pipefail

# Configuration - Match the PRIVATE Cloud SQL setup (same as other services)
PROJECT_ID="gke-hack-471804"
CLOUDSQL_INSTANCE="onlineboutique-instance-private"  # Private instance
REGION="us-central1"
CLOUDSQL_PRIVATE_IP="10.103.0.3"  # Private IP (same as other services)
DATABASE_NAME="reviews"
SECRET_NAME="cloudsql-secret-private"  
CLOUDSQL_USER_GSA_NAME="cloudsql-user-sa-private"  
PGPASSWORD="Admin123"  

echo "🗃️ Setting up Reviews Database for Review Service..."
echo "=================================================="
echo "🔒 Using PRIVATE Cloud SQL (same as other services)"
echo "📍 Private IP: ${CLOUDSQL_PRIVATE_IP}"

# Function to create database
create_database() {
    echo "📦 Creating reviews database..."
    
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
    
    # Create the product_reviews table
    echo "Creating product_reviews table..."
    gcloud compute ssh alloydb-jumpbox --zone=us-central1-a \
        --command="PGPASSWORD='${PGPASSWORD}' psql -h ${CLOUDSQL_PRIVATE_IP} -U postgres -d ${DATABASE_NAME} -c 'CREATE TABLE IF NOT EXISTS product_reviews (id SERIAL PRIMARY KEY, product_id VARCHAR(255) NOT NULL, user_id VARCHAR(255) NOT NULL, rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5), review_text TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);'"
    
    echo "Creating indexes for performance..."
    gcloud compute ssh alloydb-jumpbox --zone=us-central1-a \
        --command="PGPASSWORD='${PGPASSWORD}' psql -h ${CLOUDSQL_PRIVATE_IP} -U postgres -d ${DATABASE_NAME} -c 'CREATE INDEX IF NOT EXISTS idx_product_reviews_product_id ON product_reviews(product_id); CREATE INDEX IF NOT EXISTS idx_product_reviews_user_id ON product_reviews(user_id); CREATE INDEX IF NOT EXISTS idx_product_reviews_rating ON product_reviews(rating); CREATE INDEX IF NOT EXISTS idx_product_reviews_created_at ON product_reviews(created_at);'"
    
    echo "✅ Reviews tables created successfully"
}

# Function to verify setup
verify_setup() {
    echo "🔍 Verifying reviews database setup..."
    
    # Check if tables exist using jumpbox VM
    echo "Checking tables in reviews database:"
    gcloud compute ssh alloydb-jumpbox --zone=us-central1-a \
        --command="PGPASSWORD='${PGPASSWORD}' psql -h ${CLOUDSQL_PRIVATE_IP} -U postgres -d ${DATABASE_NAME} -c '\dt'"
    
    echo "✅ Reviews database verification complete"
}

# Main execution
main() {
    echo "Starting reviews database setup..."
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
    
    # Verify setup
    verify_setup
    
    echo ""
    echo "🎉 Reviews database setup complete!"
    echo ""
    echo "📝 Next steps:"
    echo "1. The reviewservice should now be able to connect to the reviews database"
    echo "2. Test the review service to verify it can create and retrieve reviews"
    echo ""
    echo "🔒 Using PRIVATE Cloud SQL instance: ${CLOUDSQL_INSTANCE}"
    echo "🔑 Using private secret: ${SECRET_NAME}"
    echo "�� Using private GSA: ${CLOUDSQL_USER_GSA_NAME}"
    echo ""
    echo "✅ Matches other services configuration!"
}

# Run main function
main "$@"
