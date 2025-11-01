#!/bin/bash
# ============================================================================
# Database Restore Script for ID Verification API
# ============================================================================

set -e

# Configuration
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-idyntra-postgres}"
POSTGRES_USER="${POSTGRES_USER:-idv_user}"
POSTGRES_DB="${POSTGRES_DB:-idverification}"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if backup file is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: No backup file specified${NC}"
    echo "Usage: $0 <backup_file.sql.gz>"
    exit 1
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}Error: Backup file '$BACKUP_FILE' not found${NC}"
    exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Database Restore Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo "Timestamp: $(date)"
echo "Database: $POSTGRES_DB"
echo "Backup file: $BACKUP_FILE"
echo ""

# Check if PostgreSQL container is running
if ! docker ps | grep -q "$POSTGRES_CONTAINER"; then
    echo -e "${RED}Error: PostgreSQL container '$POSTGRES_CONTAINER' is not running${NC}"
    exit 1
fi

# Warning
echo -e "${YELLOW}WARNING: This will overwrite the current database!${NC}"
echo -e "${YELLOW}Press Ctrl+C to cancel, or wait 10 seconds to continue...${NC}"
sleep 10

# Perform restore
echo ""
echo -e "${YELLOW}Starting restore...${NC}"

if gunzip -c "$BACKUP_FILE" | docker exec -i "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" "$POSTGRES_DB" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Restore completed successfully${NC}"
else
    echo -e "${RED}✗ Restore failed${NC}"
    exit 1
fi

# Verify restore
echo ""
echo "Verifying restore..."
TABLE_COUNT=$(docker exec "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")

echo "Tables found: $TABLE_COUNT"

if [ "$TABLE_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Database verification passed${NC}"
else
    echo -e "${RED}✗ Database verification failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Restore completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"

exit 0
