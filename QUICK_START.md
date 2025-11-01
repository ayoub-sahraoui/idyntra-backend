# 🚀 Quick Start Guide - Production Docker Setup

## Overview
This document provides quick commands for deploying the ID Verification API to production.

---

## Prerequisites Check

```bash
# Check Docker version (need 24.0+)
docker --version

# Check Docker Compose version (need 2.20+)
docker-compose --version

# Check available disk space (need 50GB+)
df -h

# Check available memory (need 8GB+)
free -h
```

---

## Quick Deployment (5 Minutes)

### 1. Clone and Setup

```bash
# Clone repository
git clone https://github.com/yourusername/idyntra-backend.git
cd idyntra-backend/v1

# Create environment file
cp .env.production.example .env.production

# Edit with your values (use nano, vim, or any editor)
nano .env.production
```

### 2. Generate Secrets

```bash
# Generate all required secrets at once
echo "SECRET_KEY=$(openssl rand -base64 64)"
echo "API_KEY_HASH_SALT=$(openssl rand -base64 32)"
echo "POSTGRES_PASSWORD=$(openssl rand -base64 32)"
echo "REDIS_PASSWORD=$(openssl rand -base64 32)"
echo "GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 16)"

# Generate API keys (run multiple times for multiple keys)
python3 -c "import secrets; print('API_KEY=' + secrets.token_urlsafe(32))"
```

### 3. Setup SSL (Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot -y

# Get certificate
sudo certbot certonly --standalone \
  -d yourdomain.com \
  --email admin@yourdomain.com \
  --agree-tos

# Copy certificates
mkdir -p nginx/ssl
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem
sudo chown $USER:$USER nginx/ssl/*.pem
```

### 4. Create Data Directories

```bash
# Create all data directories
mkdir -p data/{postgres,redis,model_cache,logs,prometheus,grafana}
chmod 700 data/postgres data/redis
```

### 5. Deploy

```bash
# Build and start all services
docker-compose -f docker-compose.production.yml up -d

# Wait for services to be healthy (30-60 seconds)
watch docker-compose -f docker-compose.production.yml ps

# Check logs
docker-compose -f docker-compose.production.yml logs -f api
```

### 6. Verify

```bash
# Test health endpoint
curl -k https://localhost/health

# Test API (replace YOUR_API_KEY)
curl -k https://localhost/api/v1/verify \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "id_document=@test_id.jpg" \
  -F "selfie=@test_selfie.jpg"

# Access monitoring
# Grafana: https://localhost:3001 (admin / your_password)
```

---

## Common Commands

### Service Management

```bash
# Start all services
docker-compose -f docker-compose.production.yml up -d

# Stop all services
docker-compose -f docker-compose.production.yml stop

# Restart specific service
docker-compose -f docker-compose.production.yml restart api

# View status
docker-compose -f docker-compose.production.yml ps

# Scale API instances
docker-compose -f docker-compose.production.yml up -d --scale api=3
```

### Logs

```bash
# View all logs
docker-compose -f docker-compose.production.yml logs -f

# View specific service
docker-compose -f docker-compose.production.yml logs -f api
docker-compose -f docker-compose.production.yml logs -f postgres
docker-compose -f docker-compose.production.yml logs -f nginx

# Last 100 lines
docker-compose -f docker-compose.production.yml logs --tail=100 api

# Search logs
docker-compose -f docker-compose.production.yml logs api | grep ERROR
```

### Database

```bash
# Access PostgreSQL
docker exec -it idyntra-postgres psql -U idv_user -d idverification

# Backup database
docker exec idyntra-postgres pg_dump -U idv_user idverification > backup.sql

# Restore database
cat backup.sql | docker exec -i idyntra-postgres psql -U idv_user idverification

# Check database size
docker exec idyntra-postgres psql -U idv_user -d idverification -c "SELECT pg_size_pretty(pg_database_size('idverification'));"
```

### Redis

```bash
# Access Redis CLI (replace PASSWORD)
docker exec -it idyntra-redis redis-cli -a YOUR_REDIS_PASSWORD

# Check Redis info
docker exec -it idyntra-redis redis-cli -a YOUR_REDIS_PASSWORD INFO

# Monitor Redis commands
docker exec -it idyntra-redis redis-cli -a YOUR_REDIS_PASSWORD MONITOR

# Flush all cache (CAREFUL!)
docker exec -it idyntra-redis redis-cli -a YOUR_REDIS_PASSWORD FLUSHALL
```

### Monitoring

```bash
# View resource usage
docker stats

# View network
docker network ls
docker network inspect idyntra-backend

# View volumes
docker volume ls
docker volume inspect idyntra_postgres_data
```

---

## Troubleshooting Quick Fixes

### API Won't Start

```bash
# Check configuration
docker-compose -f docker-compose.production.yml config

# Check logs for errors
docker-compose -f docker-compose.production.yml logs api | grep -i error

# Restart with fresh logs
docker-compose -f docker-compose.production.yml restart api
docker-compose -f docker-compose.production.yml logs -f api
```

### Database Issues

```bash
# Check database is healthy
docker-compose -f docker-compose.production.yml ps postgres

# View database logs
docker-compose -f docker-compose.production.yml logs postgres

# Restart database (CAUTION: may cause downtime)
docker-compose -f docker-compose.production.yml restart postgres
```

### Out of Memory

```bash
# Check memory usage
docker stats --no-stream

# Restart API with more memory (edit docker-compose.production.yml first)
docker-compose -f docker-compose.production.yml up -d --no-deps api

# Clear unused Docker resources
docker system prune -a
```

### SSL Certificate Issues

```bash
# Check certificate expiration
openssl x509 -in nginx/ssl/cert.pem -noout -dates

# Renew certificate
sudo certbot renew

# Restart nginx
docker-compose -f docker-compose.production.yml restart nginx
```

---

## Backup & Restore

### Quick Backup

```bash
# Backup everything
./scripts/backup_full.sh

# Backup just database
./scripts/backup_database.sh
```

### Quick Restore

```bash
# Restore database
./scripts/restore_database.sh /path/to/backup.sql.gz

# Restore data directories
tar -xzf data_backup_20240101.tar.gz
```

---

## Maintenance

### Update Application

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.production.yml build api
docker-compose -f docker-compose.production.yml up -d --no-deps api

# Verify
curl -k https://localhost/health
```

### Update Docker Images

```bash
# Pull latest images
docker-compose -f docker-compose.production.yml pull

# Restart with new images
docker-compose -f docker-compose.production.yml up -d

# Clean old images
docker image prune -a
```

### Clean Up

```bash
# Remove unused containers
docker container prune

# Remove unused images
docker image prune -a

# Remove unused volumes (CAREFUL!)
docker volume prune

# Remove everything unused
docker system prune -a --volumes
```

---

## Security Checklist

- [ ] All passwords changed from defaults
- [ ] SSL certificates installed and valid
- [ ] Firewall configured (ports 80, 443 only)
- [ ] CORS origins whitelisted (no wildcards)
- [ ] API keys generated and secured
- [ ] Database backups scheduled
- [ ] Monitoring and alerts configured
- [ ] Logs being collected
- [ ] SSH key-based authentication
- [ ] Root login disabled

---

## Performance Tuning

### For High Traffic (Adjust in .env.production)

```bash
# API
WORKERS=8

# Database
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=20

# Redis
REDIS_POOL_SIZE=100

# Then restart
docker-compose -f docker-compose.production.yml restart api
```

### For Low Resource Systems

```bash
# API
WORKERS=2

# Reduce memory limits in docker-compose.production.yml
# Then restart
docker-compose -f docker-compose.production.yml up -d
```

---

## URLs & Access

- **API**: https://yourdomain.com/api/v1
- **API Docs**: https://yourdomain.com/docs
- **Health Check**: https://yourdomain.com/health
- **Grafana**: https://yourdomain.com:3001
- **Prometheus**: http://localhost:9091 (internal)

---

## Emergency Procedures

### Complete Restart

```bash
# Stop everything
docker-compose -f docker-compose.production.yml down

# Wait 10 seconds
sleep 10

# Start everything
docker-compose -f docker-compose.production.yml up -d

# Monitor startup
docker-compose -f docker-compose.production.yml logs -f
```

### Emergency Rollback

```bash
# Stop current version
docker-compose -f docker-compose.production.yml down

# Restore previous backup
tar -xzf /opt/backups/full/data_backup_YYYYMMDD.tar.gz

# Start previous version
docker-compose -f docker-compose.production.yml up -d
```

---

## Support

- **Documentation**: See PRODUCTION_DEPLOYMENT.md
- **Detailed Analysis**: See ANALYSIS_AND_IMPROVEMENTS.md
- **Issues**: Open GitHub issue

---

**Last Updated**: 2025-01-01  
**Version**: 2.0.0
