# ============================================================================
# Production Docker Build Script with Enhanced Error Handling (PowerShell)
# ============================================================================

param(
    [string]$ImageName = "idyntra/id-verification-api",
    [string]$Version = "2.0.0",
    [switch]$RunTests
)

$ErrorActionPreference = "Stop"

# Configuration
$BUILD_DATE = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$VCS_REF = try { (git rev-parse --short HEAD) } catch { "unknown" }

# Color functions
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Check prerequisites
Write-Info "Checking prerequisites..."

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is not installed or not in PATH"
    exit 1
}

try {
    docker info | Out-Null
} catch {
    Write-Error "Docker daemon is not running"
    exit 1
}

Write-Success "Prerequisites check passed"

# Check network connectivity
Write-Info "Checking network connectivity..."
try {
    $null = Test-NetConnection -ComputerName huggingface.co -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
    Write-Success "Network connectivity OK"
} catch {
    Write-Warning "Network connectivity issues detected - model downloads may fail"
    Write-Warning "Models will be downloaded at runtime if build-time download fails"
}

# Build arguments
$buildArgs = @(
    "--build-arg", "BUILD_DATE=$BUILD_DATE",
    "--build-arg", "VCS_REF=$VCS_REF",
    "--build-arg", "VERSION=$Version"
)

# Add proxy settings if configured
if ($env:HTTP_PROXY) {
    $buildArgs += "--build-arg", "http_proxy=$($env:HTTP_PROXY)"
    Write-Info "Using HTTP proxy: $($env:HTTP_PROXY)"
}

if ($env:HTTPS_PROXY) {
    $buildArgs += "--build-arg", "https_proxy=$($env:HTTPS_PROXY)"
    Write-Info "Using HTTPS proxy: $($env:HTTPS_PROXY)"
}

# Enable BuildKit
$env:DOCKER_BUILDKIT = "1"

Write-Info "Building Docker image: ${ImageName}:${Version}"
Write-Info "Build date: $BUILD_DATE"
Write-Info "VCS ref: $VCS_REF"

# Build the image
try {
    $buildCommand = @(
        "build",
        "-f", "Dockerfile.production",
        "-t", "${ImageName}:${Version}",
        "-t", "${ImageName}:latest"
    ) + $buildArgs + @(
        "--progress=plain",
        "."
    )
    
    & docker $buildCommand
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker image built successfully!"
        Write-Info "Image tags:"
        Write-Host "  - ${ImageName}:${Version}" -ForegroundColor Cyan
        Write-Host "  - ${ImageName}:latest" -ForegroundColor Cyan
        
        # Show image size
        $imageInfo = docker images "${ImageName}:${Version}" --format "{{.Size}}"
        Write-Info "Image size: $imageInfo"
        
        # Optional: Run tests
        if ($RunTests) {
            Write-Info "Running container health check..."
            $containerId = docker run -d -p 8000:8000 "${ImageName}:${Version}"
            
            Start-Sleep -Seconds 10
            
            try {
                docker exec $containerId /app/healthcheck.sh
                if ($LASTEXITCODE -eq 0) {
                    Write-Success "Health check passed!"
                } else {
                    Write-Warning "Health check failed - container may need more time to start"
                }
            } finally {
                docker stop $containerId | Out-Null
                docker rm $containerId | Out-Null
            }
        }
        
        Write-Success "Build completed successfully! 🚀"
    } else {
        throw "Docker build failed with exit code $LASTEXITCODE"
    }
    
} catch {
    Write-Error "Docker build failed!"
    Write-Info "Troubleshooting tips:"
    Write-Host "  1. Check your internet connection" -ForegroundColor Yellow
    Write-Host "  2. Ensure you have enough disk space" -ForegroundColor Yellow
    Write-Host "  3. Try cleaning Docker build cache: docker builder prune" -ForegroundColor Yellow
    Write-Host "  4. Check if HuggingFace is accessible: Test-NetConnection huggingface.co -Port 443" -ForegroundColor Yellow
    Write-Host "  5. Models will download at runtime if build fails" -ForegroundColor Yellow
    exit 1
}
