#!/bin/bash

# ============================================================================
# Coolify/Traefik Diagnostic Script
# ============================================================================
# Run this on your Coolify server to diagnose connection issues
# Usage: bash diagnose.sh
# ============================================================================

set -e

echo ""
echo "========================================================================"
echo "🔍 Coolify/Traefik API Diagnostic Tool"
echo "========================================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Find API container
echo "1️⃣  Finding API container..."
API_CONTAINER=$(docker ps | grep -E 'api|idyntra|verification' | grep -v postgres | grep -v redis | awk '{print $1}' | head -n 1)

if [ -z "$API_CONTAINER" ]; then
    echo -e "${RED}❌ API container not found!${NC}"
    echo "Available containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    exit 1
fi

API_NAME=$(docker ps | grep $API_CONTAINER | awk '{print $NF}')
echo -e "${GREEN}✓ Found API container: $API_NAME ($API_CONTAINER)${NC}"
echo ""

# Check container status
echo "2️⃣  Checking container status..."
CONTAINER_STATUS=$(docker inspect $API_CONTAINER | jq -r '.[0].State.Status')
CONTAINER_HEALTH=$(docker inspect $API_CONTAINER | jq -r '.[0].State.Health.Status // "no healthcheck"')

echo "   Status: $CONTAINER_STATUS"
echo "   Health: $CONTAINER_HEALTH"

if [ "$CONTAINER_STATUS" != "running" ]; then
    echo -e "${RED}❌ Container is not running!${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Container is running${NC}"
echo ""

# Check networks
echo "3️⃣  Checking networks..."
NETWORKS=$(docker inspect $API_CONTAINER | jq -r '.[0].NetworkSettings.Networks | keys[]')
echo "   Connected to networks:"
for net in $NETWORKS; do
    echo "   - $net"
done

if echo "$NETWORKS" | grep -q "default"; then
    echo -e "${GREEN}✓ Connected to default network (Traefik can reach)${NC}"
else
    echo -e "${RED}❌ NOT connected to default network (Traefik cannot reach)${NC}"
    echo "   Fix: Add 'default' to networks in docker-compose.yml"
fi
echo ""

# Check Traefik labels
echo "4️⃣  Checking Traefik labels..."
TRAEFIK_ENABLED=$(docker inspect $API_CONTAINER | jq -r '.[0].Config.Labels["traefik.enable"] // "not set"')
TRAEFIK_RULE=$(docker inspect $API_CONTAINER | jq -r '.[0].Config.Labels["traefik.http.routers.api-idyntra.rule"] // "not set"')
TRAEFIK_PORT=$(docker inspect $API_CONTAINER | jq -r '.[0].Config.Labels["traefik.http.services.api-idyntra.loadbalancer.server.port"] // "not set"')
HEALTH_PATH=$(docker inspect $API_CONTAINER | jq -r '.[0].Config.Labels["traefik.http.services.api-idyntra.loadbalancer.healthcheck.path"] // "not set"')

echo "   traefik.enable: $TRAEFIK_ENABLED"
echo "   Router rule: $TRAEFIK_RULE"
echo "   Port: $TRAEFIK_PORT"
echo "   Health check path: $HEALTH_PATH"

if [ "$TRAEFIK_ENABLED" != "true" ]; then
    echo -e "${RED}❌ Traefik is not enabled!${NC}"
else
    echo -e "${GREEN}✓ Traefik is enabled${NC}"
fi
echo ""

# Test internal health endpoint
echo "5️⃣  Testing health endpoint (internal)..."
echo "   Testing: http://localhost:8000/health"

HEALTH_RESPONSE=$(docker exec $API_CONTAINER curl -s -w "\n%{http_code}" http://localhost:8000/health 2>&1 || echo "ERROR")

if echo "$HEALTH_RESPONSE" | grep -q "200"; then
    echo -e "${GREEN}✓ Health endpoint responding (200 OK)${NC}"
    echo "   Response:"
    echo "$HEALTH_RESPONSE" | head -n -1 | jq '.' 2>/dev/null || echo "$HEALTH_RESPONSE" | head -n -1
else
    echo -e "${RED}❌ Health endpoint not responding properly${NC}"
    echo "   Response: $HEALTH_RESPONSE"
    
    # Try alternate paths
    echo ""
    echo "   Trying alternate paths..."
    
    echo "   - Testing: http://localhost:8000/api/v1/health"
    ALT_RESPONSE=$(docker exec $API_CONTAINER curl -s -w "\n%{http_code}" http://localhost:8000/api/v1/health 2>&1 || echo "ERROR")
    if echo "$ALT_RESPONSE" | grep -q "200"; then
        echo -e "${YELLOW}   ⚠️  Health endpoint is at /api/v1/health (not /health)${NC}"
        echo "   Fix: Update Traefik label to use /api/v1/health"
    fi
    
    echo "   - Testing: http://localhost:8000/"
    ROOT_RESPONSE=$(docker exec $API_CONTAINER curl -s -w "\n%{http_code}" http://localhost:8000/ 2>&1 || echo "ERROR")
    if echo "$ROOT_RESPONSE" | grep -q "200"; then
        echo -e "${GREEN}   ✓ Root endpoint responding${NC}"
    fi
fi
echo ""

# Check if app is listening
echo "6️⃣  Checking if application is listening on port 8000..."
LISTENING=$(docker exec $API_CONTAINER netstat -tlnp 2>/dev/null | grep :8000 || echo "not listening")

if echo "$LISTENING" | grep -q "LISTEN"; then
    echo -e "${GREEN}✓ Application is listening on port 8000${NC}"
    echo "   $LISTENING"
else
    echo -e "${RED}❌ Application is NOT listening on port 8000${NC}"
    echo "   Check application logs"
fi
echo ""

# Check recent logs
echo "7️⃣  Recent application logs (last 20 lines)..."
echo "   ---------------------------------------------------------------"
docker logs $API_CONTAINER --tail 20
echo "   ---------------------------------------------------------------"
echo ""

# Find Traefik container
echo "8️⃣  Checking Traefik..."
TRAEFIK_CONTAINER=$(docker ps | grep traefik | awk '{print $1}' | head -n 1)

if [ -z "$TRAEFIK_CONTAINER" ]; then
    echo -e "${YELLOW}⚠️  Traefik container not found on this host${NC}"
    echo "   (This is normal if Traefik runs on a different container/host)"
else
    echo -e "${GREEN}✓ Found Traefik container: $TRAEFIK_CONTAINER${NC}"
    
    # Check Traefik logs for our service
    echo "   Checking Traefik logs for api-idyntra..."
    TRAEFIK_LOGS=$(docker logs $TRAEFIK_CONTAINER --tail 50 2>&1 | grep -i "idyntra" || echo "No logs found")
    
    if [ "$TRAEFIK_LOGS" != "No logs found" ]; then
        echo "   Recent Traefik logs:"
        echo "$TRAEFIK_LOGS" | tail -10
    else
        echo "   No recent logs mentioning 'idyntra'"
    fi
fi
echo ""

# Summary
echo "========================================================================"
echo "📊 Summary"
echo "========================================================================"
echo ""

ISSUES=0

if [ "$CONTAINER_STATUS" != "running" ]; then
    echo -e "${RED}❌ Container not running${NC}"
    ((ISSUES++))
fi

if ! echo "$NETWORKS" | grep -q "default"; then
    echo -e "${RED}❌ Not connected to default network${NC}"
    ((ISSUES++))
fi

if [ "$TRAEFIK_ENABLED" != "true" ]; then
    echo -e "${RED}❌ Traefik not enabled${NC}"
    ((ISSUES++))
fi

if ! echo "$HEALTH_RESPONSE" | grep -q "200"; then
    echo -e "${RED}❌ Health endpoint not responding${NC}"
    ((ISSUES++))
fi

if ! echo "$LISTENING" | grep -q "LISTEN"; then
    echo -e "${RED}❌ Application not listening on port 8000${NC}"
    ((ISSUES++))
fi

if [ $ISSUES -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo ""
    echo "If you're still seeing 503 errors:"
    echo "1. Wait 30-60 seconds for ML models to fully load"
    echo "2. Check Traefik dashboard for service status"
    echo "3. Try accessing: https://api.idyntra.space/health"
    echo "4. Check Coolify proxy logs"
else
    echo -e "${RED}Found $ISSUES issue(s)${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Fix the issues listed above"
    echo "2. Redeploy: docker-compose down && docker-compose up -d"
    echo "3. Run this script again"
fi

echo ""
echo "========================================================================"
echo ""
