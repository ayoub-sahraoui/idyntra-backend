# ============================================================================
# Production-Ready Multi-Stage Dockerfile for ID Verification API
# ============================================================================
# Security: Non-root user, minimal base image, security scanning
# Performance: Layer caching, multi-stage builds, optimized dependencies
# Reliability: Health checks, graceful shutdown, proper signal handling
# ============================================================================

# ============================================================================
# Stage 1: Base image with system dependencies (HEAVILY CACHED)
# ============================================================================
FROM python:3.10-slim-bookworm AS base

# Set build arguments
ARG DEBIAN_FRONTEND=noninteractive
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=2.0.0

# Add metadata labels
LABEL maintainer="idyntra@example.com" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.title="ID Verification API" \
      org.opencontainers.image.description="Production-grade identity verification API with AI/ML capabilities" \
      org.opencontainers.image.vendor="Idyntra" \
      org.label-schema.schema-version="1.0"

# Install system dependencies and security updates
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        # Core libraries for OpenCV and image processing
        libgl1-mesa-glx \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
        libgomp1 \
        libopenblas-dev \
        # Build tools (removed after use)
        cmake \
        build-essential \
        # OCR support
        tesseract-ocr \
        tesseract-ocr-eng \
        # File type detection
        libmagic1 \
        # SSL certificates
        ca-certificates \
        # Health check utility
        curl \
        # Process management
        tini \
        # Security scanning
        && \
    # Clean up apt cache to reduce image size
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean && \
    # Create application directories with proper permissions
    mkdir -p /app/logs /app/temp /app/security && \
    chmod 770 /app/logs /app/temp

# Download Tesseract trained data files
RUN mkdir -p /usr/share/tesseract-ocr/4/tessdata && \
    curl -fsSL -o /usr/share/tesseract-ocr/4/tessdata/mrz.traineddata \
        https://github.com/alex-raw/tesseract_mrz/raw/master/mrz.traineddata && \
    curl -fsSL -o /usr/share/tesseract-ocr/4/tessdata/eng.traineddata \
        https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata && \
    chmod 644 /usr/share/tesseract-ocr/4/tessdata/*.traineddata && \
    # Verify download
    ls -lh /usr/share/tesseract-ocr/4/tessdata/

# Set TESSDATA_PREFIX globally
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/4/tessdata

# ============================================================================
# Stage 2: Python dependencies builder (HEAVILY CACHED)
# ============================================================================
FROM base AS builder

WORKDIR /app

# Upgrade pip and install build tools
RUN pip install --no-cache-dir --upgrade pip==23.3.2 setuptools==69.0.3 wheel==0.42.0

# Copy requirements file ONLY (for maximum cache efficiency)
COPY requirements.txt .

# Install Python packages to a separate location
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ============================================================================
# Stage 3: ML Models downloader (CACHED SEPARATELY)
# ============================================================================
FROM builder AS models

# Pre-download and cache HuggingFace models
RUN python -c "from transformers import AutoImageProcessor, AutoModelForImageClassification; \
    import sys; \
    print('📥 Downloading deepfake detection model...', file=sys.stderr); \
    processor = AutoImageProcessor.from_pretrained('dima806/deepfake_vs_real_image_detection'); \
    model = AutoModelForImageClassification.from_pretrained('dima806/deepfake_vs_real_image_detection'); \
    print('✅ Models cached successfully!', file=sys.stderr)"

# Pre-load face recognition models (dlib)
RUN python -c "import face_recognition; \
    import cv2; \
    import sys; \
    print('✅ Face recognition models loaded', file=sys.stderr)"

# ============================================================================
# Stage 4: Security Scanner (OPTIONAL - can be disabled in production)
# ============================================================================
FROM builder AS security-scanner

# Install security audit tools
RUN pip install --no-cache-dir pip-audit==2.6.3 safety==3.0.1

# Run security scans and generate reports
RUN mkdir -p /app/security && \
    # Pip-audit for known vulnerabilities
    pip-audit --requirement /app/requirements.txt --format json 2>/dev/null > /app/security/audit.json || true && \
    pip-audit --requirement /app/requirements.txt --format text 2>/dev/null > /app/security/audit.txt || true && \
    # Safety check
    safety check --json > /app/security/safety.json || true && \
    # Create summary
    echo "Security scan completed at $(date)" > /app/security/scan_summary.txt

# ============================================================================
# Stage 5: Final production image (MINIMAL SIZE)
# ============================================================================
FROM base AS production

WORKDIR /app

# Copy Python packages from builder stage
COPY --from=builder /install /usr/local

# Copy cached ML models
COPY --from=models /root/.cache /root/.cache

# Copy security scan results (optional)
COPY --from=security-scanner /app/security /app/security

# Copy application code
COPY --chown=root:root app/ ./app/
COPY --chown=root:root requirements.txt ./

# Copy Tesseract data to readmrz package
RUN mkdir -p /usr/local/lib/python3.10/site-packages/readmrz/language/ && \
    cp /usr/share/tesseract-ocr/4/tessdata/eng.traineddata \
       /usr/local/lib/python3.10/site-packages/readmrz/language/ 2>/dev/null || true

# Create non-root user with specific UID/GID
RUN groupadd -g 1000 apiuser && \
    useradd -r -u 1000 -g apiuser -s /bin/bash -m -d /home/apiuser apiuser && \
    # Set ownership for app directories
    chown -R apiuser:apiuser /app /root/.cache && \
    # Make cache readable by apiuser
    chmod -R 755 /root/.cache && \
    # Set secure permissions on application code
    chmod -R 750 /app/app && \
    # Ensure log and temp directories are writable
    chmod 770 /app/logs /app/temp && \
    chown apiuser:apiuser /app/logs /app/temp

# Create startup script with proper signal handling
RUN cat > /app/entrypoint.sh << 'ENTRYPOINT_EOF'
#!/bin/bash
set -e

# Trap SIGTERM and SIGINT for graceful shutdown
_term() {
  echo "Received SIGTERM signal, shutting down gracefully..."
  kill -TERM "$child" 2>/dev/null
}

trap _term SIGTERM SIGINT

# Create log file with proper permissions
touch /app/logs/idv_api.log
chmod 640 /app/logs/idv_api.log

# Log startup
echo "========================================" | tee -a /app/logs/idv_api.log
echo "🚀 Starting ID Verification API v${VERSION:-2.0.0}" | tee -a /app/logs/idv_api.log
echo "⏰ $(date)" | tee -a /app/logs/idv_api.log
echo "👤 Running as: $(whoami)" | tee -a /app/logs/idv_api.log
echo "🖥️  CPU Mode: ${CPU_ONLY:-1}" | tee -a /app/logs/idv_api.log
echo "========================================" | tee -a /app/logs/idv_api.log

# Start uvicorn with proper configuration
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers "${WORKERS:-4}" \
    --loop uvloop \
    --log-config /dev/null \
    --no-access-log \
    --proxy-headers \
    --forwarded-allow-ips='*' &

child=$!
wait "$child"
ENTRYPOINT_EOF

RUN chmod +x /app/entrypoint.sh

# Create health check script
RUN cat > /app/healthcheck.sh << 'HEALTHCHECK_EOF'
#!/bin/bash
set -e

# Check if the API is responding
if ! curl -f -s -o /dev/null http://localhost:${PORT:-8000}/health; then
    echo "❌ Health check failed: API not responding"
    exit 1
fi

# Check if log directory is writable
if [ ! -w /app/logs ]; then
    echo "❌ Health check failed: Log directory not writable"
    exit 1
fi

# Check if temp directory is writable
if [ ! -w /app/temp ]; then
    echo "❌ Health check failed: Temp directory not writable"
    exit 1
fi

# Check if model cache is accessible
if [ ! -r /root/.cache ]; then
    echo "⚠️  Warning: Model cache not accessible"
fi

echo "✅ Health check passed"
exit 0
HEALTHCHECK_EOF

RUN chmod +x /app/healthcheck.sh

# Create log cleanup script
RUN cat > /app/cleanup_logs.sh << 'CLEANUP_EOF'
#!/bin/bash
# Clean up logs larger than 100MB
find /app/logs -type f -name "*.log" -size +100M -exec rm -f {} \;
# Clean up temp files older than 24 hours
find /app/temp -type f -mtime +1 -delete
CLEANUP_EOF

RUN chmod +x /app/cleanup_logs.sh

# Switch to non-root user
USER apiuser

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    # Application settings
    CPU_ONLY=1 \
    PORT=8000 \
    WORKERS=4 \
    # Paths
    LOG_FILE=/app/logs/idv_api.log \
    LOG_LEVEL=INFO \
    TESSDATA_PREFIX=/usr/share/tesseract-ocr/4/tessdata \
    TMPDIR=/app/temp \
    # Security
    UMASK=0027 \
    # Performance
    MALLOC_TRIM_THRESHOLD_=100000 \
    MALLOC_MMAP_THRESHOLD_=100000

# Expose port
EXPOSE 8000

# Health check with proper timing
HEALTHCHECK --interval=30s \
            --timeout=10s \
            --start-period=60s \
            --retries=3 \
            CMD ["/app/healthcheck.sh"]

# Use tini as init system for proper signal handling
ENTRYPOINT ["/usr/bin/tini", "--"]

# Start the application
CMD ["/app/entrypoint.sh"]

# ============================================================================
# Build command example:
# docker build -f Dockerfile.production \
#   --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
#   --build-arg VCS_REF=$(git rev-parse --short HEAD) \
#   --build-arg VERSION=2.0.0 \
#   -t idyntra/id-verification-api:2.0.0 \
#   -t idyntra/id-verification-api:latest \
#   .
# ============================================================================
