#!/bin/bash
# ============================================================================
# Production Docker Build Script with Enhanced Error Handling
# ============================================================================

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="${IMAGE_NAME:-idyntra/id-verification-api}"
VERSION="${VERSION:-2.0.0}"
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
log_info "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed or not in PATH"
    exit 1
fi

if ! docker info &> /dev/null; then
    log_error "Docker daemon is not running"
    exit 1
fi

log_success "Prerequisites check passed"

# Check network connectivity (optional but helpful)
log_info "Checking network connectivity..."
if ping -c 1 huggingface.co &> /dev/null 2>&1 || ping -c 1 8.8.8.8 &> /dev/null 2>&1; then
    log_success "Network connectivity OK"
else
    log_warning "Network connectivity issues detected - model downloads may fail"
    log_warning "Models will be downloaded at runtime if build-time download fails"
fi

# Build arguments
BUILD_ARGS=(
    --build-arg BUILD_DATE="${BUILD_DATE}"
    --build-arg VCS_REF="${VCS_REF}"
    --build-arg VERSION="${VERSION}"
)

# Add network configuration if needed
if [ -n "${HTTP_PROXY}" ]; then
    BUILD_ARGS+=(--build-arg http_proxy="${HTTP_PROXY}")
    log_info "Using HTTP proxy: ${HTTP_PROXY}"
fi

if [ -n "${HTTPS_PROXY}" ]; then
    BUILD_ARGS+=(--build-arg https_proxy="${HTTPS_PROXY}")
    log_info "Using HTTPS proxy: ${HTTPS_PROXY}"
fi

# Enable BuildKit for better performance
export DOCKER_BUILDKIT=1

log_info "Building Docker image: ${IMAGE_NAME}:${VERSION}"
log_info "Build date: ${BUILD_DATE}"
log_info "VCS ref: ${VCS_REF}"

# Build the image
if docker build \
    -f Dockerfile.production \
    -t "${IMAGE_NAME}:${VERSION}" \
    -t "${IMAGE_NAME}:latest" \
    "${BUILD_ARGS[@]}" \
    --progress=plain \
    . ; then
    
    log_success "Docker image built successfully!"
    log_info "Image tags:"
    echo "  - ${IMAGE_NAME}:${VERSION}"
    echo "  - ${IMAGE_NAME}:latest"
    
    # Show image size
    IMAGE_SIZE=$(docker images "${IMAGE_NAME}:${VERSION}" --format "{{.Size}}")
    log_info "Image size: ${IMAGE_SIZE}"
    
    # Optional: Run tests
    if [ "${RUN_TESTS}" = "true" ]; then
        log_info "Running container health check..."
        CONTAINER_ID=$(docker run -d -p 8000:8000 "${IMAGE_NAME}:${VERSION}")
        
        sleep 10
        
        if docker exec "${CONTAINER_ID}" /app/healthcheck.sh; then
            log_success "Health check passed!"
        else
            log_warning "Health check failed - container may need more time to start"
        fi
        
        docker stop "${CONTAINER_ID}" > /dev/null
        docker rm "${CONTAINER_ID}" > /dev/null
    fi
    
else
    log_error "Docker build failed!"
    log_info "Troubleshooting tips:"
    echo "  1. Check your internet connection"
    echo "  2. Ensure you have enough disk space"
    echo "  3. Try cleaning Docker build cache: docker builder prune"
    echo "  4. Check if HuggingFace is accessible: curl -I https://huggingface.co"
    echo "  5. Models will download at runtime if build fails"
    exit 1
fi

log_success "Build completed successfully! 🚀"
