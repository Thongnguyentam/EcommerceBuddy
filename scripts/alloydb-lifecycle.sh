#!/bin/bash

# AlloyDB Development Lifecycle Script
# Delete AlloyDB when not working, recreate when needed

set -e

PROJECT_ID="gke-hack-471804"
REGION="us-central1"
CLUSTER_NAME="onlineboutique-cluster"
PRIMARY_INSTANCE_NAME="onlineboutique-instance"
VPC_NETWORK="projects/${PROJECT_ID}/global/networks/default"

ACTION=${1:-help}

backup_data() {
    echo "💾 Backing up database data..."
    
    # Create backup directory with timestamp
    BACKUP_DIR="alloydb-backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Get current primary IP
    PRIMARY_IP=$(gcloud alloydb instances describe ${PRIMARY_INSTANCE_NAME} \
        --cluster=${CLUSTER_NAME} \
        --region=${REGION} \
        --format="value(ipAddress)" 2>/dev/null || echo "")
    
    if [[ -n "$PRIMARY_IP" ]]; then
        echo "   Exporting products database..."
        gcloud compute ssh alloydb-jumpbox --zone=us-central1-a --command="
            PGPASSWORD='Admin123' pg_dump -h ${PRIMARY_IP} -U postgres -d products > products_backup.sql &&
            PGPASSWORD='Admin123' pg_dump -h ${PRIMARY_IP} -U postgres -d carts > carts_backup.sql
        " || echo "   ⚠️  Backup failed - instance may not be running"
        
        # Copy backups locally
        gcloud compute scp alloydb-jumpbox:~/products_backup.sql "${BACKUP_DIR}/" --zone=us-central1-a
        gcloud compute scp alloydb-jumpbox:~/carts_backup.sql "${BACKUP_DIR}/" --zone=us-central1-a
        
        echo "   ✅ Backups saved to: ${BACKUP_DIR}/"
    else
        echo "   ⚠️  No running instance found to backup"
    fi
}

restore_data() {
    local backup_dir=$1
    if [[ -z "$backup_dir" ]]; then
        echo "❌ Please specify backup directory"
        echo "Usage: $0 restore <backup-directory>"
        exit 1
    fi
    
    if [[ ! -d "$backup_dir" ]]; then
        echo "❌ Backup directory not found: $backup_dir"
        exit 1
    fi
    
    echo "🔄 Restoring data from: $backup_dir"
    
    # Get current primary IP
    PRIMARY_IP=$(gcloud alloydb instances describe ${PRIMARY_INSTANCE_NAME} \
        --cluster=${CLUSTER_NAME} \
        --region=${REGION} \
        --format="value(ipAddress)")
    
    # Copy backups to jumpbox
    gcloud compute scp "${backup_dir}/products_backup.sql" alloydb-jumpbox:~/ --zone=us-central1-a
    gcloud compute scp "${backup_dir}/carts_backup.sql" alloydb-jumpbox:~/ --zone=us-central1-a
    
    # Restore databases
    echo "   Restoring products database..."
    gcloud compute ssh alloydb-jumpbox --zone=us-central1-a --command="
        PGPASSWORD='Admin123' createdb -h ${PRIMARY_IP} -U postgres products 2>/dev/null || true &&
        PGPASSWORD='Admin123' psql -h ${PRIMARY_IP} -U postgres -d products -f products_backup.sql
    "
    
    echo "   Restoring carts database..."
    gcloud compute ssh alloydb-jumpbox --zone=us-central1-a --command="
        PGPASSWORD='Admin123' createdb -h ${PRIMARY_IP} -U postgres carts 2>/dev/null || true &&
        PGPASSWORD='Admin123' psql -h ${PRIMARY_IP} -U postgres -d carts -f carts_backup.sql
    "
    
    echo "   ✅ Data restored successfully"
}

delete_cluster() {
    echo "🗑️  Deleting AlloyDB cluster..."
    echo "⚠️  This will delete ALL data! Make sure you've backed up first."
    echo ""
    
    read -p "🔄 Continue with deletion? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Deletion cancelled"
        exit 1
    fi
    
    # Delete instances first
    echo "   Deleting instance: ${PRIMARY_INSTANCE_NAME}"
    gcloud alloydb instances delete ${PRIMARY_INSTANCE_NAME} \
        --cluster=${CLUSTER_NAME} \
        --region=${REGION} \
        --quiet 2>/dev/null || echo "   Instance already deleted"
    
    # Wait a bit
    sleep 10
    
    # Delete cluster
    echo "   Deleting cluster: ${CLUSTER_NAME}"
    gcloud alloydb clusters delete ${CLUSTER_NAME} \
        --region=${REGION} \
        --quiet 2>/dev/null || echo "   Cluster already deleted"
    
    echo "   ✅ AlloyDB cluster deleted"
    echo "   💰 Billing stopped!"
}

create_cluster() {
    echo "🚀 Creating AlloyDB cluster..."
    
    # Create cluster
    echo "   Creating cluster: ${CLUSTER_NAME}"
    gcloud alloydb clusters create ${CLUSTER_NAME} \
        --region=${REGION} \
        --network=${VPC_NETWORK} \
        --quiet
    
    # Create minimal primary instance (2 vCPUs)
    echo "   Creating primary instance: ${PRIMARY_INSTANCE_NAME}"
    gcloud alloydb instances create ${PRIMARY_INSTANCE_NAME} \
        --cluster=${CLUSTER_NAME} \
        --region=${REGION} \
        --cpu-count=2 \
        --instance-type=PRIMARY \
        --quiet
    
    # Wait for ready
    echo "   Waiting for instance to be ready..."
    while true; do
        STATUS=$(gcloud alloydb instances describe ${PRIMARY_INSTANCE_NAME} \
            --cluster=${CLUSTER_NAME} \
            --region=${REGION} \
            --format="value(state)" 2>/dev/null || echo "CREATING")
        
        if [[ "$STATUS" == "READY" ]]; then
            echo "   ✅ Instance is ready!"
            break
        else
            echo "   Status: $STATUS - waiting..."
            sleep 30
        fi
    done
    
    # Get new IP
    NEW_PRIMARY_IP=$(gcloud alloydb instances describe ${PRIMARY_INSTANCE_NAME} \
        --cluster=${CLUSTER_NAME} \
        --region=${REGION} \
        --format="value(ipAddress)")
    
    echo "   ✅ AlloyDB cluster created"
    echo "   📍 Primary IP: ${NEW_PRIMARY_IP}"
    echo ""
    echo "🔧 Update Kustomize configuration:"
    echo "   sed -i 's/10\.79\.0\.[0-9]*/${NEW_PRIMARY_IP}/g' kustomize/components/alloydb/kustomization.yaml"
}

show_help() {
    echo "AlloyDB Development Lifecycle Manager"
    echo "===================================="
    echo ""
    echo "💰 Save money by deleting AlloyDB when not working!"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  backup              - Backup current data to local files"
    echo "  delete              - Delete AlloyDB cluster (saves ~\$500/month)"
    echo "  create              - Create new minimal AlloyDB cluster"
    echo "  restore <dir>       - Restore data from backup directory"
    echo "  full-stop           - Backup data + delete cluster"
    echo "  full-start [dir]    - Create cluster + restore data"
    echo ""
    echo "Examples:"
    echo "  # End of work day:"
    echo "  $0 full-stop"
    echo ""
    echo "  # Start of work day:"
    echo "  $0 full-start alloydb-backup-20250913-090000"
    echo ""
    echo "  # Manual backup:"
    echo "  $0 backup"
}

case $ACTION in
    "backup")
        backup_data
        ;;
    "delete")
        delete_cluster
        ;;
    "create")
        create_cluster
        ;;
    "restore")
        restore_data $2
        ;;
    "full-stop")
        backup_data
        delete_cluster
        echo ""
        echo "🏁 Work session ended!"
        echo "💰 AlloyDB billing stopped"
        echo "📁 Data backed up safely"
        ;;
    "full-start")
        create_cluster
        if [[ -n "$2" ]]; then
            restore_data $2
        else
            echo ""
            echo "⚠️  No backup directory specified"
            echo "💡 To restore data: $0 restore <backup-directory>"
        fi
        echo ""
        echo "🎯 Work session started!"
        echo "🔄 Don't forget to update Kustomize and redeploy"
        ;;
    *)
        show_help
        ;;
esac 