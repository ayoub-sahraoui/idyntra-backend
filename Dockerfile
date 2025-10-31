# ============================================================================
# Stage 1: Base image with system dependencies (CACHED)
# ============================================================================
FROM python:3.10-slim-bookworm as base

# Install dependencies in the base stage
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libopenblas-dev \
    cmake \
    build-essential \
    curl \
    tesseract-ocr \
    tesseract-ocr-eng \
    libmagic1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && mkdir -p /app/logs /app/temp \
    && chmod 770 /app/logs /app/temp

# Download both MRZ and English trained data
RUN mkdir -p /usr/share/tesseract-ocr/4/tessdata && \
    curl -L -o /usr/share/tesseract-ocr/4/tessdata/mrz.traineddata \
    https://github.com/alex-raw/tesseract_mrz/raw/master/mrz.traineddata && \
    curl -L -o /usr/share/tesseract-ocr/4/tessdata/eng.traineddata \
    https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata && \
    chmod 644 /usr/share/tesseract-ocr/4/tessdata/*.traineddata && \
    ls -lh /usr/share/tesseract-ocr/4/tessdata/ && \
    echo "✓ Tesseract trained data installed"

# Set TESSDATA_PREFIX environment variable globally
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/4/tessdata

# ============================================================================
# Stage 2: Python dependencies (HEAVILY CACHED)
# ============================================================================
FROM base as dependencies

WORKDIR /app

# Copy ONLY requirements first for better caching
COPY requirements.txt .

# Install Python packages with pip cache
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============================================================================
# Stage 3: Model downloader (CACHED SEPARATELY)
# ============================================================================
FROM dependencies as models

# Pre-download HuggingFace models to cache them
RUN python -c "from transformers import AutoImageProcessor, AutoModelForImageClassification; \
    print('Downloading deepfake detection model...'); \
    processor = AutoImageProcessor.from_pretrained('dima806/deepfake_vs_real_image_detection'); \
    model = AutoModelForImageClassification.from_pretrained('dima806/deepfake_vs_real_image_detection'); \
    print('Models cached successfully!')"

# Download dlib face recognition models
RUN python -c "import face_recognition; \
    import cv2; \
    print('Face recognition models loaded')"

# ============================================================================
# Stage 4: Final application image
# ============================================================================
FROM base as final

WORKDIR /app

# Copy Python packages from dependencies stage
COPY --from=dependencies /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Copy cached models from models stage
COPY --from=models /root/.cache /root/.cache

# Copy application code (this changes frequently, so it's last)
COPY app/ ./app/
COPY requirements.txt ./

# Verify traineddata files and setup readmrz
RUN ls -lh /usr/share/tesseract-ocr/4/tessdata/ && \
    mkdir -p /usr/local/lib/python3.10/site-packages/readmrz/language/ && \
    cp /usr/share/tesseract-ocr/4/tessdata/eng.traineddata /usr/local/lib/python3.10/site-packages/readmrz/language/ && \
    ls -lh /usr/local/lib/python3.10/site-packages/readmrz/language/ && \
    echo "✓ Tesseract data verified in final stage"

# Install cron
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user and set permissions
RUN useradd -m -u 1000 -s /bin/bash apiuser && \
    chown -R apiuser:apiuser /app /root/.cache && \
    chmod -R 755 /root/.cache && \
    # Add .local/bin to PATH for pip-installed binaries
    echo 'export PATH="/home/apiuser/.local/bin:$PATH"' >> /home/apiuser/.bashrc

# Switch to non-root user
USER apiuser
ENV PATH="/home/apiuser/.local/bin:$PATH"

# Expose port
EXPOSE 8000

# Security scanning during build (with vulnerability report)
RUN pip install --no-cache-dir pip-audit && \
    # Run security audit and save report, but don't fail the build
    (pip-audit --format json > /app/security_audit.json || true) && \
    # Generate a human-readable report
    (pip-audit || true) && \
    pip uninstall -y pip-audit && \
    # Clean up pip cache
    rm -rf /root/.cache/pip/*

# Health checks
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Additional service checks
RUN echo '#!/bin/sh\n\
check_services() {\n\
  # Check API health\n\
  curl -sf http://localhost:8000/health > /dev/null || return 1\n\
  # Check log file permissions\n\
  test -w /app/logs/idv_api.log || return 1\n\
  # Check temp directory permissions\n\
  test -w /app/temp || return 1\n\
  # Check model cache access\n\
  test -r /root/.cache || return 1\n\
  return 0\n\
}\n\
check_services' > /app/healthcheck.sh && \
    chmod +x /app/healthcheck.sh

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    CPU_ONLY=1 \
    LOG_FILE=/app/logs/idv_api.log \
    LOG_LEVEL=INFO \
    TESSDATA_PREFIX=/usr/share/tesseract-ocr/4/tessdata \
    # Security settings
    PYTHONHASHSEED=random \
    # Disable Python bytecode cache
    PYTHONDONTWRITEBYTECODE=1 \
    # Set umask for created files
    UMASK=0027 \
    # Set secure temp directory
    TMPDIR=/app/temp

# Set secure workdir permissions and setup log management
COPY --chown=apiuser:apiuser <<-"EOF" /app/cleanup_logs.sh
#!/bin/sh
find /app/logs -type f -name "*.log" -size +100M -exec rm -f {} \;
# Ensure log file exists with correct permissions
touch /app/logs/idv_api.log
chmod 640 /app/logs/idv_api.log
EOF

RUN chmod 750 /app && \
    chmod +x /app/cleanup_logs.sh && \
    # Create log file with correct permissions
    touch /app/logs/idv_api.log && \
    chown apiuser:apiuser /app/logs/idv_api.log && \
    chmod 640 /app/logs/idv_api.log

# Run application with security options
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--log-level", "info", \
     "--limit-concurrency", "1000", \
     "--limit-max-requests", "10000", \
     "--timeout-keep-alive", "5", \
     "--server-header", "false"]