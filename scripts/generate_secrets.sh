#!/bin/bash
# ============================================================================
# Generate Secrets Script for ID Verification API
# ============================================================================

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Secret Generation Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "This script generates secure random secrets for your production environment."
echo ""

# Generate secrets
echo -e "${BLUE}# ============================================${NC}"
echo -e "${BLUE}# Generated Secrets - $(date)${NC}"
echo -e "${BLUE}# ============================================${NC}"
echo ""

echo -e "${YELLOW}# Application Secrets${NC}"
echo "SECRET_KEY=$(openssl rand -base64 64)"
echo "API_KEY_HASH_SALT=$(openssl rand -base64 32)"
echo ""

echo -e "${YELLOW}# Database${NC}"
echo "POSTGRES_PASSWORD=$(openssl rand -base64 32)"
echo ""

echo -e "${YELLOW}# Redis${NC}"
echo "REDIS_PASSWORD=$(openssl rand -base64 32)"
echo ""

echo -e "${YELLOW}# Grafana${NC}"
echo "GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 16)"
echo ""

echo -e "${YELLOW}# API Keys (generate one per client)${NC}"
for i in {1..3}; do
    echo "API_KEY_${i}=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")"
done

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Copy these values to your .env.production file${NC}"
echo -e "${YELLOW}⚠️  NEVER commit these secrets to version control!${NC}"
echo -e "${GREEN}========================================${NC}"
