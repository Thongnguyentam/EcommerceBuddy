#!/bin/bash

# AlloyDB Jumpbox VM Management Script
# This script helps manage a jumpbox VM for accessing AlloyDB from within the VPC

set -e

# Configuration
PROJECT_ID="gke-hack-471804"
ZONE="us-central1-a"
VM_NAME="alloydb-jumpbox"
SERVICE_ACCOUNT="alloydb-user-sa@${PROJECT_ID}.iam.gserviceaccount.com"
ALLOYDB_IP="10.79.0.2"
ALLOYDB_PASSWORD="Admin123"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Function to create jumpbox VM
create_jumpbox() {
    print_status "Creating jumpbox VM: ${VM_NAME}"
    
    gcloud compute instances create ${VM_NAME} \
        --zone=${ZONE} \
        --machine-type=e2-micro \
        --subnet=default \
        --service-account=${SERVICE_ACCOUNT} \
        --scopes=https://www.googleapis.com/auth/cloud-platform \
        --image=projects/debian-cloud/global/images/debian-12-bookworm-v20240312 \
        --boot-disk-size=10GB \
        --project=${PROJECT_ID} \
        --metadata=startup-script='#!/bin/bash
        apt update -y
        apt install -y postgresql-client wget curl
        echo "Jumpbox VM ready for AlloyDB access"'
    
    print_status "Waiting for VM to be ready..."
    sleep 30
    
    print_status "Installing PostgreSQL client on jumpbox..."
    gcloud compute ssh ${VM_NAME} \
        --zone=${ZONE} \
        --project=${PROJECT_ID} \
        --command="sudo apt update && sudo apt install -y postgresql-client wget" \
        --quiet
    
    print_status "Jumpbox VM created successfully!"
    print_status "VM Name: ${VM_NAME}"
    print_status "Zone: ${ZONE}"
    print_status "Service Account: ${SERVICE_ACCOUNT}"
}

# Function to delete jumpbox VM
delete_jumpbox() {
    print_status "Deleting jumpbox VM: ${VM_NAME}"
    
    gcloud compute instances delete ${VM_NAME} \
        --zone=${ZONE} \
        --project=${PROJECT_ID} \
        --quiet
    
    print_status "Jumpbox VM deleted successfully!"
}

# Function to check if VM exists
vm_exists() {
    gcloud compute instances describe ${VM_NAME} \
        --zone=${ZONE} \
        --project=${PROJECT_ID} \
        --quiet > /dev/null 2>&1
}

# Function to test direct AlloyDB connection
test_direct_connection() {
    print_status "Testing direct connection to AlloyDB..."
    
    gcloud compute ssh ${VM_NAME} \
        --zone=${ZONE} \
        --project=${PROJECT_ID} \
        --command="PGPASSWORD='${ALLOYDB_PASSWORD}' psql -h ${ALLOYDB_IP} -U postgres -d postgres -c 'SELECT version();'" \
        --quiet
}

# Function to query available databases
query_databases() {
    print_status "Querying available databases..."
    
    gcloud compute ssh ${VM_NAME} \
        --zone=${ZONE} \
        --project=${PROJECT_ID} \
        --command="PGPASSWORD='${ALLOYDB_PASSWORD}' psql -h ${ALLOYDB_IP} -U postgres -c '\l'" \
        --quiet
}

# Function to query tables in products database
query_products_tables() {
    print_status "Querying tables in 'products' database..."
    
    gcloud compute ssh ${VM_NAME} \
        --zone=${ZONE} \
        --project=${PROJECT_ID} \
        --command="PGPASSWORD='${ALLOYDB_PASSWORD}' psql -h ${ALLOYDB_IP} -U postgres -d products -c '\dt'" \
        --quiet
}

# Function to query tables in carts database
query_carts_tables() {
    print_status "Querying tables in 'carts' database..."
    
    gcloud compute ssh ${VM_NAME} \
        --zone=${ZONE} \
        --project=${PROJECT_ID} \
        --command="PGPASSWORD='${ALLOYDB_PASSWORD}' psql -h ${ALLOYDB_IP} -U postgres -d carts -c '\dt'" \
        --quiet
}

# Function to query products data
query_products_data() {
    print_status "Querying data from products table..."
    
    gcloud compute ssh ${VM_NAME} \
        --zone=${ZONE} \
        --project=${PROJECT_ID} \
        --command="PGPASSWORD='${ALLOYDB_PASSWORD}' psql -h ${ALLOYDB_IP} -U postgres -d products -c 'SELECT * FROM products LIMIT 10;'" \
        --quiet
}

# Function to query cart items data
query_cart_data() {
    print_status "Querying data from cart_items table..."
    
    gcloud compute ssh ${VM_NAME} \
        --zone=${ZONE} \
        --project=${PROJECT_ID} \
        --command="PGPASSWORD='${ALLOYDB_PASSWORD}' psql -h ${ALLOYDB_IP} -U postgres -d carts -c 'SELECT * FROM cart_items LIMIT 10;'" \
        --quiet
}

# Function to install and test AlloyDB Auth Proxy
test_auth_proxy() {
    print_status "Testing AlloyDB Auth Proxy on jumpbox VM..."
    
    # Install AlloyDB Auth Proxy
    gcloud compute ssh ${VM_NAME} \
        --zone=${ZONE} \
        --project=${PROJECT_ID} \
        --command="wget https://storage.googleapis.com/alloydb-auth-proxy/v1.13.6/alloydb-auth-proxy.linux.amd64 -O alloydb-auth-proxy && chmod +x alloydb-auth-proxy" \
        --quiet
    
    # Test Auth Proxy connection
    print_status "Testing connection through AlloyDB Auth Proxy..."
    gcloud compute ssh ${VM_NAME} \
        --zone=${ZONE} \
        --project=${PROJECT_ID} \
        --command="timeout 20s ./alloydb-auth-proxy projects/${PROJECT_ID}/locations/us-central1/clusters/onlineboutique-cluster/instances/onlineboutique-instance --port=15432 & sleep 5 && PGPASSWORD='${ALLOYDB_PASSWORD}' psql -h 127.0.0.1 -p 15432 -U postgres -d products -c '\dt' && pkill alloydb-auth-proxy" \
        --quiet
}

# Function to start interactive psql session
interactive_psql() {
    local database=${1:-postgres}
    print_status "Starting interactive psql session for database: ${database}"
    print_warning "Type 'exit' or '\\q' to quit the psql session"
    
    gcloud compute ssh ${VM_NAME} \
        --zone=${ZONE} \
        --project=${PROJECT_ID} \
        --command="PGPASSWORD='${ALLOYDB_PASSWORD}' psql -h ${ALLOYDB_IP} -U postgres -d ${database}"
}

# Function to show VM status
show_status() {
    if vm_exists; then
        print_status "Jumpbox VM Status:"
        gcloud compute instances describe ${VM_NAME} \
            --zone=${ZONE} \
            --project=${PROJECT_ID} \
            --format="table(name,status,machineType.basename(),scheduling.preemptible)" \
            --quiet
    else
        print_warning "Jumpbox VM does not exist"
    fi
}

# Function to show help
show_help() {
    echo "AlloyDB Jumpbox VM Management Script"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  create              Create the jumpbox VM"
    echo "  delete              Delete the jumpbox VM"
    echo "  status              Show VM status"
    echo "  test-direct         Test direct AlloyDB connection"
    echo "  test-proxy          Test AlloyDB Auth Proxy connection"
    echo "  query-dbs           List all databases"
    echo "  query-products      Show tables in products database"
    echo "  query-carts         Show tables in carts database"
    echo "  query-products-data Show data from products table"
    echo "  query-carts-data    Show data from cart_items table"
    echo "  psql [database]     Start interactive psql (default: postgres)"
    echo "  help                Show this help message"
    echo ""
    echo "Configuration:"
    echo "  Project ID: ${PROJECT_ID}"
    echo "  Zone: ${ZONE}"
    echo "  VM Name: ${VM_NAME}"
    echo "  AlloyDB IP: ${ALLOYDB_IP}"
    echo ""
    echo "Examples:"
    echo "  $0 create                    # Create jumpbox VM"
    echo "  $0 query-products           # Query products tables"
    echo "  $0 psql products            # Interactive psql to products database"
    echo "  $0 delete                   # Delete jumpbox VM"
}

# Main script logic
case "$1" in
    "create")
        if vm_exists; then
            print_warning "Jumpbox VM already exists!"
            show_status
        else
            create_jumpbox
        fi
        ;;
    "delete")
        if vm_exists; then
            delete_jumpbox
        else
            print_warning "Jumpbox VM does not exist!"
        fi
        ;;
    "status")
        show_status
        ;;
    "test-direct")
        if vm_exists; then
            test_direct_connection
        else
            print_error "Jumpbox VM does not exist! Run '$0 create' first."
            exit 1
        fi
        ;;
    "test-proxy")
        if vm_exists; then
            test_auth_proxy
        else
            print_error "Jumpbox VM does not exist! Run '$0 create' first."
            exit 1
        fi
        ;;
    "query-dbs")
        if vm_exists; then
            query_databases
        else
            print_error "Jumpbox VM does not exist! Run '$0 create' first."
            exit 1
        fi
        ;;
    "query-products")
        if vm_exists; then
            query_products_tables
        else
            print_error "Jumpbox VM does not exist! Run '$0 create' first."
            exit 1
        fi
        ;;
    "query-carts")
        if vm_exists; then
            query_carts_tables
        else
            print_error "Jumpbox VM does not exist! Run '$0 create' first."
            exit 1
        fi
        ;;
    "query-products-data")
        if vm_exists; then
            query_products_data
        else
            print_error "Jumpbox VM does not exist! Run '$0 create' first."
            exit 1
        fi
        ;;
    "query-carts-data")
        if vm_exists; then
            query_cart_data
        else
            print_error "Jumpbox VM does not exist! Run '$0 create' first."
            exit 1
        fi
        ;;
    "psql")
        if vm_exists; then
            interactive_psql "$2"
        else
            print_error "Jumpbox VM does not exist! Run '$0 create' first."
            exit 1
        fi
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
