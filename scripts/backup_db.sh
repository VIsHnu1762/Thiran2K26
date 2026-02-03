#!/bin/bash
# =============================================================================
# BillAgent Pro - Database Backup Script
# =============================================================================
# Performs PostgreSQL database backup with compression and rotation.
#
# Usage:
#   ./scripts/backup_db.sh                    # Manual backup
#   ./scripts/backup_db.sh --restore latest   # Restore latest backup
#   ./scripts/backup_db.sh --list             # List available backups
#
# Environment Variables (from .env or environment):
#   POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
#   BACKUP_DIR (default: ./backups)
#   BACKUP_RETENTION_DAYS (default: 7)
# =============================================================================

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Database config (from environment or defaults)
PGHOST="${POSTGRES_HOST:-localhost}"
PGPORT="${POSTGRES_PORT:-5432}"
PGDATABASE="${POSTGRES_DB:-billagent}"
PGUSER="${POSTGRES_USER:-billagent}"
PGPASSWORD="${POSTGRES_PASSWORD:-}"

# Export for pg_dump/pg_restore
export PGHOST PGPORT PGDATABASE PGUSER PGPASSWORD

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Function to perform backup
do_backup() {
    local backup_file="${BACKUP_DIR}/${PGDATABASE}_${TIMESTAMP}.dump"
    local backup_file_gz="${backup_file}.gz"
    
    log_info "Starting backup of database: $PGDATABASE"
    log_info "Backup file: $backup_file_gz"
    
    # Perform backup with custom format (most flexible for restore)
    if pg_dump -Fc -f "$backup_file" "$PGDATABASE"; then
        # Compress the backup
        gzip "$backup_file"
        
        # Get backup size
        local size=$(du -h "$backup_file_gz" | cut -f1)
        
        log_info "Backup completed successfully!"
        log_info "Backup size: $size"
        log_info "File: $backup_file_gz"
        
        # Create latest symlink
        ln -sf "$(basename "$backup_file_gz")" "${BACKUP_DIR}/latest.dump.gz"
        
        # Clean up old backups
        cleanup_old_backups
        
        return 0
    else
        log_error "Backup failed!"
        return 1
    fi
}

# Function to restore backup
do_restore() {
    local backup_name="$1"
    local backup_file
    
    if [[ "$backup_name" == "latest" ]]; then
        backup_file="${BACKUP_DIR}/latest.dump.gz"
        if [[ ! -L "$backup_file" ]]; then
            log_error "No latest backup found!"
            return 1
        fi
        backup_file=$(readlink -f "$backup_file")
    else
        backup_file="${BACKUP_DIR}/${backup_name}"
    fi
    
    if [[ ! -f "$backup_file" ]]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi
    
    log_warn "This will restore database: $PGDATABASE"
    log_warn "From backup: $backup_file"
    read -p "Are you sure you want to continue? (yes/no): " confirm
    
    if [[ "$confirm" != "yes" ]]; then
        log_info "Restore cancelled."
        return 0
    fi
    
    log_info "Starting restore..."
    
    # Decompress if needed
    local restore_file="$backup_file"
    if [[ "$backup_file" == *.gz ]]; then
        restore_file="${backup_file%.gz}"
        gunzip -k "$backup_file"
    fi
    
    # Drop and recreate database
    log_info "Recreating database..."
    dropdb --if-exists "$PGDATABASE" || true
    createdb "$PGDATABASE"
    
    # Restore
    if pg_restore -d "$PGDATABASE" "$restore_file"; then
        log_info "Restore completed successfully!"
        
        # Clean up decompressed file
        if [[ "$backup_file" == *.gz ]]; then
            rm -f "$restore_file"
        fi
        
        return 0
    else
        log_error "Restore failed!"
        return 1
    fi
}

# Function to list backups
list_backups() {
    log_info "Available backups in: $BACKUP_DIR"
    echo ""
    
    if ls -la "$BACKUP_DIR"/*.dump.gz 2>/dev/null; then
        echo ""
        log_info "To restore, run: ./scripts/backup_db.sh --restore <filename>"
    else
        log_warn "No backups found."
    fi
}

# Function to clean up old backups
cleanup_old_backups() {
    log_info "Cleaning up backups older than $RETENTION_DAYS days..."
    
    local count=$(find "$BACKUP_DIR" -name "*.dump.gz" -type f -mtime +$RETENTION_DAYS | wc -l)
    
    if [[ $count -gt 0 ]]; then
        find "$BACKUP_DIR" -name "*.dump.gz" -type f -mtime +$RETENTION_DAYS -delete
        log_info "Removed $count old backup(s)"
    else
        log_info "No old backups to remove"
    fi
}

# Function to show help
show_help() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  (no option)           Perform a database backup"
    echo "  --restore <name>      Restore from backup (use 'latest' for most recent)"
    echo "  --list                List available backups"
    echo "  --cleanup             Remove old backups"
    echo "  --help                Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  POSTGRES_HOST         Database host (default: localhost)"
    echo "  POSTGRES_PORT         Database port (default: 5432)"
    echo "  POSTGRES_DB           Database name (default: billagent)"
    echo "  POSTGRES_USER         Database user (default: billagent)"
    echo "  POSTGRES_PASSWORD     Database password"
    echo "  BACKUP_DIR            Backup directory (default: ./backups)"
    echo "  BACKUP_RETENTION_DAYS Days to keep backups (default: 7)"
}

# Main
case "${1:-}" in
    --restore)
        if [[ -z "${2:-}" ]]; then
            log_error "Please specify backup name or 'latest'"
            exit 1
        fi
        do_restore "$2"
        ;;
    --list)
        list_backups
        ;;
    --cleanup)
        cleanup_old_backups
        ;;
    --help|-h)
        show_help
        ;;
    "")
        do_backup
        ;;
    *)
        log_error "Unknown option: $1"
        show_help
        exit 1
        ;;
esac
