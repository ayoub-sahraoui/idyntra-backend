#!/bin/bash
# ============================================================================
# Database Backup Script for ID Verification API
# ============================================================================

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/opt/backups/postgres}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-idyntra-postgres}"
POSTGRES_USER="${POSTGRES_USER:-idv_user}"
POSTGRES_DB="${POSTGRES_DB:-idverification}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

# Timestamp
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="idverification_backup_${DATE}.sql.gz"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Database Backup Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo "Timestamp: $(date)"
echo "Database: $POSTGRES_DB"
echo "Backup location: $BACKUP_DIR"
echo ""

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Check if PostgreSQL container is running
if ! docker ps | grep -q "$POSTGRES_CONTAINER"; then
    echo -e "${RED}Error: PostgreSQL container '$POSTGRES_CONTAINER' is not running${NC}"
    exit 1
fi

# Perform backup
echo -e "${YELLOW}Starting backup...${NC}"

if docker exec "$POSTGRES_CONTAINER" pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "${BACKUP_DIR}/${FILENAME}"; then
    echo -e "${GREEN}✓ Backup completed successfully${NC}"
    echo "Backup file: ${FILENAME}"
    
    # Get file size
    SIZE=$(du -h "${BACKUP_DIR}/${FILENAME}" | cut -f1)
    echo "Backup size: $SIZE"
else
    echo -e "${RED}✗ Backup failed${NC}"
    exit 1
fi

# Clean up old backups
echo ""
echo -e "${YELLOW}Cleaning up old backups (older than $RETENTION_DAYS days)...${NC}"

DELETED=$(find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)

if [ "$DELETED" -gt 0 ]; then
    echo -e "${GREEN}✓ Deleted $DELETED old backup(s)${NC}"
else
    echo "No old backups to delete"
fi

# List current backups
echo ""
echo "Current backups:"
ls -lh "$BACKUP_DIR" | tail -n +2

# Calculate total backup size
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
echo ""
echo "Total backup size: $TOTAL_SIZE"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Backup completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"

exit 0
