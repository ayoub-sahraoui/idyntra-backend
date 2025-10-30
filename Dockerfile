# ============================================================================
# Stage 1: Base image with system dependencies (CACHED)
# ============================================================================
FROM python:3.10-slim-bookworm as base

# Install curl in the base stage
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
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

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

# Create necessary directories
RUN mkdir -p /app/logs /app/temp && \
    chmod 755 /app/logs /app/temp

# Verify traineddata files exist in final stage and copy eng.traineddata to readmrz
RUN ls -lh /usr/share/tesseract-ocr/4/tessdata/ && \
    mkdir -p /usr/local/lib/python3.10/site-packages/readmrz/language/ && \
    cp /usr/share/tesseract-ocr/4/tessdata/eng.traineddata /usr/local/lib/python3.10/site-packages/readmrz/language/ && \
    ls -lh /usr/local/lib/python3.10/site-packages/readmrz/language/ && \
    echo "✓ Tesseract data verified in final stage"

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash apiuser && \
    chown -R apiuser:apiuser /app

# Switch to non-root user
USER apiuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV CPU_ONLY=1
# Use the same variable name the app expects (LOG_FILE)
ENV LOG_FILE=/app/logs/idv_api.log
ENV LOG_LEVEL=INFO
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/4/tessdata

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info"]