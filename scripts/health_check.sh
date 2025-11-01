#!/bin/bash
# ============================================================================
# Health Check Script for ID Verification API
# ============================================================================

set -e

# Configuration
API_URL="${API_URL:-https://localhost}"
API_KEY="${API_KEY:-}"
TIMEOUT="${TIMEOUT:-10}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}System Health Check${NC}"
echo -e "${GREEN}========================================${NC}"
echo "Timestamp: $(date)"
echo ""

# Function to check service
check_service() {
    local name=$1
    local container=$2
    
    echo -n "Checking $name... "
    
    if docker ps | grep -q "$container"; then
        echo -e "${GREEN}✓ Running${NC}"
        return 0
    else
        echo -e "${RED}✗ Not running${NC}"
        return 1
    fi
}

# Function to check health endpoint
check_health_endpoint() {
    local url=$1
    
    echo -n "Checking API health endpoint... "
    
    if curl -sf -k --max-time "$TIMEOUT" "$url/health" > /dev/null; then
        echo -e "${GREEN}✓ Healthy${NC}"
        return 0
    else
        echo -e "${RED}✗ Unhealthy${NC}"
        return 1
    fi
}

# Function to check database
check_database() {
    echo -n "Checking database connection... "
    
    if docker exec idyntra-postgres pg_isready -U idv_user -d idverification > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Connected${NC}"
        return 0
    else
        echo -e "${RED}✗ Not connected${NC}"
        return 1
    fi
}

# Function to check Redis
check_redis() {
    echo -n "Checking Redis connection... "
    
    if docker exec idyntra-redis redis-cli -a "$REDIS_PASSWORD" ping 2>/dev/null | grep -q "PONG"; then
        echo -e "${GREEN}✓ Connected${NC}"
        return 0
    else
        echo -e "${RED}✗ Not connected${NC}"
        return 1
    fi
}

# Function to check disk space
check_disk_space() {
    echo -n "Checking disk space... "
    
    USAGE=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
    
    if [ "$USAGE" -lt 80 ]; then
        echo -e "${GREEN}✓ OK (${USAGE}% used)${NC}"
        return 0
    elif [ "$USAGE" -lt 90 ]; then
        echo -e "${YELLOW}⚠ Warning (${USAGE}% used)${NC}"
        return 1
    else
        echo -e "${RED}✗ Critical (${USAGE}% used)${NC}"
        return 1
    fi
}

# Function to check memory
check_memory() {
    echo -n "Checking memory usage... "
    
    USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100}')
    
    if [ "$USAGE" -lt 80 ]; then
        echo -e "${GREEN}✓ OK (${USAGE}% used)${NC}"
        return 0
    elif [ "$USAGE" -lt 90 ]; then
        echo -e "${YELLOW}⚠ Warning (${USAGE}% used)${NC}"
        return 1
    else
        echo -e "${RED}✗ Critical (${USAGE}% used)${NC}"
        return 1
    fi
}

# Run checks
FAILED=0

echo "Service Status:"
check_service "API" "idyntra-api" || ((FAILED++))
check_service "PostgreSQL" "idyntra-postgres" || ((FAILED++))
check_service "Redis" "idyntra-redis" || ((FAILED++))
check_service "Nginx" "idyntra-nginx" || ((FAILED++))
check_service "Prometheus" "idyntra-prometheus" || ((FAILED++))
check_service "Grafana" "idyntra-grafana" || ((FAILED++))

echo ""
echo "Health Checks:"
check_health_endpoint "$API_URL" || ((FAILED++))
check_database || ((FAILED++))

echo ""
echo "System Resources:"
check_disk_space || ((FAILED++))
check_memory || ((FAILED++))

echo ""
echo -e "${GREEN}========================================${NC}"

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ $FAILED check(s) failed${NC}"
    exit 1
fi
