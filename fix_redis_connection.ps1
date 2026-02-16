# Quick fix script to update docker-compose.yml on Raspberry Pi
# This script uploads the fixed docker-compose.yml and restarts the containers

# Configuration
$PI_IP = "192.168.5.8"
$PI_USER = "pi"
$PI_DIR = "~/autolister"
$LOCAL_DIR = "e:/Programs/repos/hallowz/AutoLister"

Write-Host "====================================" -ForegroundColor Cyan
Write-Host "AutoLister Redis Connection Fix" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Test SSH connection
Write-Host "Testing SSH connection to $PI_USER@$PI_IP..." -ForegroundColor Yellow
$testResult = ssh -o ConnectTimeout=5 "$PI_USER@$PI_IP" "echo 'Connection successful'"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Cannot connect to Raspberry Pi via SSH" -ForegroundColor Red
    Write-Host "Please ensure:"
    Write-Host "  1. Raspberry Pi is powered on"
    Write-Host "  2. Connected to the same network"
    Write-Host "  3. SSH is enabled on the Pi"
    Write-Host "  4. Correct IP address: $PI_IP"
    exit 1
}
Write-Host "SSH connection successful!" -ForegroundColor Green
Write-Host ""

# Upload the fixed docker-compose.yml
Write-Host "Uploading fixed docker-compose.yml..." -ForegroundColor Yellow
scp docker/docker-compose.yml "$PI_USER@$PI_IP`:$PI_DIR/docker/docker-compose.yml"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to upload docker-compose.yml" -ForegroundColor Red
    exit 1
}
Write-Host "Upload successful!" -ForegroundColor Green
Write-Host ""

# Restart the containers
Write-Host "Restarting Docker containers..." -ForegroundColor Yellow
ssh "$PI_USER@$PI_IP" "cd $PI_DIR && docker-compose down && docker-compose up -d"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to restart containers" -ForegroundColor Red
    exit 1
}
Write-Host "Containers restarted successfully!" -ForegroundColor Green
Write-Host ""

# Wait for containers to start
Write-Host "Waiting for containers to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Check container status
Write-Host "Checking container status..." -ForegroundColor Yellow
ssh "$PI_USER@$PI_IP" "docker ps --filter 'name=autolister' --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
Write-Host ""

# Check Celery logs
Write-Host "Checking Celery logs..." -ForegroundColor Yellow
ssh "$PI_USER@$PI_IP" "docker logs autolister-celery --tail 20"
Write-Host ""

Write-Host "====================================" -ForegroundColor Cyan
Write-Host "Fix completed!" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Access the dashboard at: http://$PI_IP:8000/dashboard" -ForegroundColor Green
Write-Host ""
Write-Host "If you still see Redis connection errors, run:" -ForegroundColor Yellow
Write-Host "  ssh $PI_USER@$PI_IP 'cd $PI_DIR && docker-compose logs autolister-celery'" -ForegroundColor Yellow
Write-Host ""
