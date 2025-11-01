# 🚀 Production Deployment Guide - ID Verification API

## 📋 Table of Contents
1. [Prerequisites](#prerequisites)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Initial Setup](#initial-setup)
4. [Security Hardening](#security-hardening)
5. [Deployment Steps](#deployment-steps)
6. [Monitoring & Observability](#monitoring--observability)
7. [Backup & Disaster Recovery](#backup--disaster-recovery)
8. [Troubleshooting](#troubleshooting)
9. [Maintenance](#maintenance)

---

## 🔧 Prerequisites

### Hardware Requirements
- **Minimum**: 4 CPU cores, 8GB RAM, 50GB SSD
- **Recommended**: 8 CPU cores, 16GB RAM, 100GB SSD
- **Storage**: Additional 500GB for logs, backups, and model cache

### Software Requirements
- Ubuntu 22.04 LTS / Debian 12 or similar Linux distribution
- Docker Engine 24.0+ 
- Docker Compose 2.20+
- SSL/TLS certificates (Let's Encrypt recommended)
- Domain name with DNS configured

### Network Requirements
- Ports 80, 443 open for HTTP/HTTPS
- Firewall configured (UFW or iptables)
- DDoS protection (Cloudflare or similar)

---

## ✅ Pre-Deployment Checklist

### 1. Security Review
- [ ] All default passwords changed
- [ ] API keys generated and secured
- [ ] SSL certificates obtained and tested
- [ ] Firewall rules configured
- [ ] SSH key-based authentication enabled
- [ ] Root login disabled
- [ ] Fail2ban installed and configured
- [ ] Security updates applied

### 2. Configuration Review
- [ ] `.env.production` created from template
- [ ] Database credentials configured
- [ ] Redis password set
- [ ] CORS origins whitelisted (no wildcards!)
- [ ] Rate limits configured appropriately
- [ ] Log levels set correctly
- [ ] Backup destinations configured
- [ ] Monitoring alerts configured

### 3. Infrastructure Review
- [ ] DNS records configured
- [ ] SSL certificates installed
- [ ] Load balancer configured (if applicable)
- [ ] CDN configured (if applicable)
- [ ] Backup storage provisioned
- [ ] Monitoring tools installed

---

## 🛠 Initial Setup

### 1. System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### 2. Firewall Configuration

```bash
# Install UFW
sudo apt install ufw -y

# Configure firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS

# Enable firewall
sudo ufw enable
sudo ufw status
```

### 3. Install Fail2ban

```bash
# Install fail2ban
sudo apt install fail2ban -y

# Create jail configuration
sudo cat > /etc/fail2ban/jail.local <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = 22
logpath = %(sshd_log)s

[nginx-limit-req]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log
EOF

# Restart fail2ban
sudo systemctl restart fail2ban
sudo systemctl enable fail2ban
```

### 4. Clone Repository

```bash
# Create application directory
sudo mkdir -p /opt/idyntra
sudo chown $USER:$USER /opt/idyntra
cd /opt/idyntra

# Clone repository
git clone https://github.com/yourusername/idyntra-backend.git
cd idyntra-backend/v1
```

---

## 🔒 Security Hardening

### 1. Generate Secure Secrets

```bash
# Generate SECRET_KEY
openssl rand -base64 64

# Generate API_KEY_HASH_SALT
openssl rand -base64 32

# Generate Database Password
openssl rand -base64 32

# Generate Redis Password
openssl rand -base64 32

# Generate Grafana Admin Password
openssl rand -base64 16

# Generate API Keys
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Create Production Environment File

```bash
# Copy template
cp .env.production.example .env.production

# Edit with secure values
nano .env.production

# Secure the file
chmod 600 .env.production
```

### 3. SSL Certificate Setup

#### Option A: Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt install certbot -y

# Create certificate directory
mkdir -p nginx/ssl

# Obtain certificate
sudo certbot certonly --standalone \
  -d yourdomain.com \
  -d www.yourdomain.com \
  -d api.yourdomain.com \
  --email admin@yourdomain.com \
  --agree-tos \
  --non-interactive

# Copy certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem
sudo chown $USER:$USER nginx/ssl/*.pem
chmod 600 nginx/ssl/*.pem

# Setup auto-renewal
sudo crontab -e
# Add: 0 0 * * * certbot renew --quiet --deploy-hook "docker-compose -f /opt/idyntra/idyntra-backend/v1/docker-compose.production.yml restart nginx"
```

#### Option B: Self-Signed (Development Only)

```bash
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem \
  -subj "/C=US/ST=State/L=City/O=Org/CN=yourdomain.com"
```

### 4. Create Data Directories

```bash
# Create data directory structure
mkdir -p data/{postgres,redis,model_cache,logs,prometheus,grafana}

# Set permissions
chmod 700 data/postgres
chmod 700 data/redis
chmod 755 data/model_cache
chmod 755 data/logs
chmod 755 data/prometheus
chmod 755 data/grafana
```

---

## 🚀 Deployment Steps

### 1. Build Images

```bash
# Set build variables
export BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
export VCS_REF=$(git rev-parse --short HEAD)
export VERSION=2.0.0

# Build production image
docker build -f Dockerfile.production \
  --build-arg BUILD_DATE=$BUILD_DATE \
  --build-arg VCS_REF=$VCS_REF \
  --build-arg VERSION=$VERSION \
  -t idyntra/id-verification-api:$VERSION \
  -t idyntra/id-verification-api:latest \
  .
```

### 2. Initialize Database

```bash
# Create initialization script
mkdir -p init-scripts

cat > init-scripts/01-init.sql <<'EOF'
-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create verification_logs table
CREATE TABLE IF NOT EXISTS verification_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    verification_id VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL,
    overall_confidence DECIMAL(5,2),
    liveness_score DECIMAL(5,2),
    face_match_confidence DECIMAL(5,2),
    authenticity_score DECIMAL(5,2),
    deepfake_confidence DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    client_ip INET,
    api_key_hash VARCHAR(255),
    metadata JSONB
);

-- Create indexes
CREATE INDEX idx_verification_id ON verification_logs(verification_id);
CREATE INDEX idx_created_at ON verification_logs(created_at);
CREATE INDEX idx_status ON verification_logs(status);
CREATE INDEX idx_api_key_hash ON verification_logs(api_key_hash);

-- Create api_keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    rate_limit_per_minute INTEGER DEFAULT 60,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    metadata JSONB
);

-- Create index
CREATE INDEX idx_key_hash ON api_keys(key_hash);

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO idv_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO idv_user;
EOF
```

### 3. Start Services

```bash
# Load environment variables
source .env.production

# Start all services
docker-compose -f docker-compose.production.yml up -d

# Check status
docker-compose -f docker-compose.production.yml ps

# View logs
docker-compose -f docker-compose.production.yml logs -f api
```

### 4. Verify Deployment

```bash
# Test health endpoint
curl -k https://localhost/health

# Expected response:
# {"status":"healthy","version":"2.0.0","timestamp":"..."}

# Test API with authentication
curl -k https://localhost/api/v1/verify \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "id_document=@test_id.jpg" \
  -F "selfie=@test_selfie.jpg"
```

### 5. Database Migration (if needed)

```bash
# Access database
docker exec -it idyntra-postgres psql -U idv_user -d idverification

# Run migrations
# Your migration commands here
```

---

## 📊 Monitoring & Observability

### 1. Access Monitoring Tools

- **Grafana**: https://yourdomain.com:3001
  - Username: admin
  - Password: (from .env.production)
  
- **Prometheus**: http://localhost:9091 (internal only)

### 2. Setup Grafana Dashboards

```bash
# Create Grafana datasource configuration
mkdir -p monitoring/grafana/datasources

cat > monitoring/grafana/datasources/prometheus.yml <<EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
EOF

# Create dashboard provisioning
mkdir -p monitoring/grafana/dashboards

cat > monitoring/grafana/dashboards/dashboards.yml <<EOF
apiVersion: 1

providers:
  - name: 'Default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
EOF
```

### 3. Configure Alerts

```bash
# Create alert rules (Prometheus)
mkdir -p monitoring/alerts

cat > monitoring/alerts/api_alerts.yml <<EOF
groups:
  - name: api_alerts
    interval: 30s
    rules:
      - alert: APIHighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "API error rate is {{ \$value }} errors per second"

      - alert: APIHighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High API latency detected"
          description: "95th percentile latency is {{ \$value }} seconds"

      - alert: APIDown
        expr: up{job="idverification-api"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "API is down"
          description: "The API has been down for more than 2 minutes"
EOF
```

### 4. Log Management

```bash
# View real-time logs
docker-compose -f docker-compose.production.yml logs -f api

# View specific service logs
docker-compose -f docker-compose.production.yml logs -f postgres
docker-compose -f docker-compose.production.yml logs -f redis
docker-compose -f docker-compose.production.yml logs -f nginx

# Export logs
docker-compose -f docker-compose.production.yml logs --no-color > deployment_logs.txt
```

---

## 💾 Backup & Disaster Recovery

### 1. Database Backup

```bash
# Create backup script
cat > scripts/backup_database.sh <<'EOF'
#!/bin/bash
set -e

BACKUP_DIR="/opt/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="idverification_backup_${DATE}.sql.gz"

mkdir -p $BACKUP_DIR

docker exec idyntra-postgres pg_dump -U idv_user idverification | gzip > "${BACKUP_DIR}/${FILENAME}"

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "Backup completed: ${FILENAME}"
EOF

chmod +x scripts/backup_database.sh

# Schedule daily backups
crontab -e
# Add: 0 2 * * * /opt/idyntra/idyntra-backend/v1/scripts/backup_database.sh
```

### 2. Full System Backup

```bash
# Backup script
cat > scripts/backup_full.sh <<'EOF'
#!/bin/bash
set -e

BACKUP_DIR="/opt/backups/full"
DATE=$(date +%Y%m%d_%H%M%S)
APP_DIR="/opt/idyntra/idyntra-backend/v1"

mkdir -p $BACKUP_DIR

# Stop services
cd $APP_DIR
docker-compose -f docker-compose.production.yml stop

# Backup data directory
tar -czf "${BACKUP_DIR}/data_backup_${DATE}.tar.gz" data/

# Backup configuration
tar -czf "${BACKUP_DIR}/config_backup_${DATE}.tar.gz" .env.production nginx/ monitoring/

# Start services
docker-compose -f docker-compose.production.yml start

echo "Full backup completed"
EOF

chmod +x scripts/backup_full.sh
```

### 3. Restore Procedures

```bash
# Restore database
cat > scripts/restore_database.sh <<'EOF'
#!/bin/bash
set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    exit 1
fi

BACKUP_FILE=$1

gunzip -c $BACKUP_FILE | docker exec -i idyntra-postgres psql -U idv_user idverification

echo "Database restored from ${BACKUP_FILE}"
EOF

chmod +x scripts/restore_database.sh

# Usage:
# ./scripts/restore_database.sh /opt/backups/postgres/idverification_backup_20240101_020000.sql.gz
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. API Not Starting

```bash
# Check logs
docker-compose -f docker-compose.production.yml logs api

# Common causes:
# - Missing environment variables
# - Database connection failed
# - Port already in use

# Fix: Check .env.production and ensure database is healthy
docker-compose -f docker-compose.production.yml ps
```

#### 2. Database Connection Issues

```bash
# Test database connection
docker exec -it idyntra-postgres psql -U idv_user -d idverification

# Check database logs
docker-compose -f docker-compose.production.yml logs postgres

# Reset database (DESTRUCTIVE!)
docker-compose -f docker-compose.production.yml down -v
docker-compose -f docker-compose.production.yml up -d postgres
```

#### 3. High Memory Usage

```bash
# Check resource usage
docker stats

# Adjust resource limits in docker-compose.production.yml
# Restart services
docker-compose -f docker-compose.production.yml restart api
```

#### 4. SSL Certificate Issues

```bash
# Verify certificates
openssl x509 -in nginx/ssl/cert.pem -text -noout

# Test SSL
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com

# Renew Let's Encrypt certificate
sudo certbot renew --force-renewal
```

### Performance Tuning

#### 1. API Performance

```bash
# Increase workers (in .env.production)
WORKERS=8

# Restart API
docker-compose -f docker-compose.production.yml restart api
```

#### 2. Database Performance

```bash
# Access PostgreSQL
docker exec -it idyntra-postgres psql -U idv_user -d idverification

# Analyze queries
EXPLAIN ANALYZE SELECT * FROM verification_logs WHERE status = 'approved';

# Create indexes
CREATE INDEX CONCURRENTLY idx_status_created ON verification_logs(status, created_at DESC);
```

#### 3. Redis Performance

```bash
# Check Redis stats
docker exec -it idyntra-redis redis-cli -a YOUR_REDIS_PASSWORD INFO stats

# Monitor Redis
docker exec -it idyntra-redis redis-cli -a YOUR_REDIS_PASSWORD MONITOR
```

---

## 🔄 Maintenance

### Regular Maintenance Tasks

#### Daily
- [ ] Check service health
- [ ] Monitor error rates
- [ ] Review access logs
- [ ] Verify backups completed

#### Weekly
- [ ] Review resource usage
- [ ] Analyze slow queries
- [ ] Check disk space
- [ ] Review security logs
- [ ] Update dependencies (if needed)

#### Monthly
- [ ] Security audit
- [ ] Performance review
- [ ] Backup restoration test
- [ ] SSL certificate check
- [ ] Log rotation review

### Update Procedure

```bash
# Pull latest changes
cd /opt/idyntra/idyntra-backend/v1
git pull origin main

# Rebuild images
export VERSION=2.1.0
docker build -f Dockerfile.production \
  --build-arg VERSION=$VERSION \
  -t idyntra/id-verification-api:$VERSION \
  .

# Update docker-compose.production.yml with new version
nano docker-compose.production.yml

# Rolling update (minimal downtime)
docker-compose -f docker-compose.production.yml up -d --no-deps --build api

# Verify
curl -k https://localhost/health
```

### Scaling

```bash
# Horizontal scaling (multiple API instances)
docker-compose -f docker-compose.production.yml up -d --scale api=3

# Update Nginx upstream in nginx/nginx.production.conf
# Add:
#   server api2:8000 max_fails=3 fail_timeout=30s;
#   server api3:8000 max_fails=3 fail_timeout=30s;
```

---

## 📞 Support & Resources

- **Documentation**: https://docs.idyntra.com
- **Support Email**: support@idyntra.com
- **Issue Tracker**: https://github.com/yourusername/idyntra-backend/issues
- **Status Page**: https://status.idyntra.com

---

## ✅ Post-Deployment Checklist

- [ ] All services running and healthy
- [ ] SSL certificates valid and working
- [ ] API endpoints accessible
- [ ] Authentication working correctly
- [ ] Rate limiting functioning
- [ ] Database connections stable
- [ ] Redis cache working
- [ ] Monitoring dashboards accessible
- [ ] Logs being collected
- [ ] Backups scheduled and tested
- [ ] Alerts configured
- [ ] Documentation updated
- [ ] Team notified

---

**Last Updated**: 2024-01-01  
**Version**: 2.0.0  
**Maintained by**: Idyntra DevOps Team
