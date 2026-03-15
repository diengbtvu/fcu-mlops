# Hydrogen Production Rate Prediction - Docker Deployment Script
# PowerShell Script for Windows

param(
    [switch]$Build,
    [switch]$Fresh,
    [switch]$Stop,
    [switch]$Logs,
    [switch]$Restart
)

$ErrorActionPreference = "Stop"

function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

Write-ColorOutput Green "========================================="
Write-ColorOutput Green "Hydrogen Production Rate Prediction - Docker Deploy"
Write-ColorOutput Green "========================================="
Write-Host ""

# Check if Docker is running
try {
    docker ps | Out-Null
} catch {
    Write-ColorOutput Red "Error: Docker is not running. Please start Docker Desktop."
    exit 1
}

# Stop containers
if ($Stop) {
    Write-ColorOutput Yellow "Stopping all containers..."
    docker-compose down
    Write-ColorOutput Green "Containers stopped successfully!"
    exit 0
}

# View logs
if ($Logs) {
    Write-ColorOutput Yellow "Showing logs (Ctrl+C to exit)..."
    docker-compose logs -f
    exit 0
}

# Restart containers
if ($Restart) {
    Write-ColorOutput Yellow "Restarting containers..."
    docker-compose restart
    Write-ColorOutput Green "Containers restarted successfully!"
    exit 0
}

# Create .env.docker from example if not exists
if (-not (Test-Path ".env.docker")) {
    Write-ColorOutput Yellow "Creating .env.docker from .env.docker.example..."
    if (Test-Path ".env.docker.example") {
        Copy-Item ".env.docker.example" ".env.docker"
        Write-ColorOutput Green ".env.docker created successfully!"
    } else {
        Write-ColorOutput Red "Error: .env.docker.example not found!"
        exit 1
    }
}

# Copy environment file to WebApp if not exists
if (-not (Test-Path "WebApp\.env")) {
    Write-ColorOutput Yellow "Copying .env.docker to WebApp\.env..."
    Copy-Item ".env.docker" "WebApp\.env"
}

# Build containers
if ($Build -or $Fresh) {
    Write-ColorOutput Yellow "Building Docker images..."
    docker-compose build --no-cache
}

# Fresh start - remove volumes
if ($Fresh) {
    Write-ColorOutput Yellow "Removing old volumes and containers..."
    docker-compose down -v
}

# Start containers
Write-ColorOutput Yellow "Starting Docker containers..."
docker-compose up -d

# Wait for MySQL to be ready
Write-ColorOutput Yellow "Waiting for MySQL to be ready..."
$maxRetries = 30
$retries = 0
while ($retries -lt $maxRetries) {
    $result = docker-compose exec -T mysql mysqladmin ping -h localhost -u root -pMySecureRootPass2025! 2>&1
    if ($result -match "mysqld is alive") {
        break
    }
    $retries++
    Write-Host "." -NoNewline
    Start-Sleep -Seconds 2
}
Write-Host ""

if ($retries -eq $maxRetries) {
    Write-ColorOutput Red "MySQL failed to start in time!"
    exit 1
}

Write-ColorOutput Green "MySQL is ready!"

# Run migrations and seeders
if ($Fresh) {
    Write-ColorOutput Yellow "Running database migrations..."
    docker-compose exec laravel-webapp php artisan migrate:fresh --force
    
    Write-ColorOutput Yellow "Seeding database..."
    docker-compose exec laravel-webapp php artisan db:seed --force
    
    Write-ColorOutput Yellow "Creating storage link..."
    docker-compose exec laravel-webapp php artisan storage:link
    
    Write-ColorOutput Yellow "Clearing caches..."
    docker-compose exec laravel-webapp php artisan config:clear
    docker-compose exec laravel-webapp php artisan cache:clear
    docker-compose exec laravel-webapp php artisan view:clear
} else {
    Write-ColorOutput Yellow "Running database migrations..."
    docker-compose exec laravel-webapp php artisan migrate --force
}

Write-Host ""
Write-ColorOutput Green "========================================="
Write-ColorOutput Green "Deployment Complete!"
Write-ColorOutput Green "========================================="
Write-Host ""
Write-ColorOutput Cyan "Access the application at: http://localhost:52025"
Write-Host ""
Write-ColorOutput Yellow "Default admin credentials:"
Write-Host "  Email: admin@example.com"
Write-Host "  Password: password"
Write-Host ""
Write-ColorOutput Yellow "Useful commands:"
Write-Host "  View logs:         .\deploy.ps1 -Logs"
Write-Host "  Stop containers:   .\deploy.ps1 -Stop"
Write-Host "  Restart:           .\deploy.ps1 -Restart"
Write-Host "  Fresh install:     .\deploy.ps1 -Fresh"
Write-Host "  Rebuild images:    .\deploy.ps1 -Build"
Write-Host ""
