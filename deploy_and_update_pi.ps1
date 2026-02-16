# AutoLister Deployment and Update Script for Raspberry Pi
# This script connects to the Raspberry Pi, pulls latest code, rebuilds Docker, and starts services

param(
    [Parameter(Mandatory=$true)]
    [string]$RaspberryPiIP,
    [string]$piUsername = "lane",
    [string]$piPassword = "growtent",
    [string]$projectPath = "~/autolister"
)

# Display banner
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  AutoLister Update & Deploy Script" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Validate IP address
if ([string]::IsNullOrWhiteSpace($RaspberryPiIP)) {
    Write-Host "ERROR: IP address cannot be empty." -ForegroundColor Red
    exit 1
}

# Check if SSH is available
Write-Host "Checking for SSH..." -ForegroundColor Yellow
$sshAvailable = Get-Command ssh -ErrorAction SilentlyContinue

if (-not $sshAvailable) {
    Write-Host "ERROR: SSH is not available." -ForegroundColor Red
    Write-Host "Please install OpenSSH from: https://github.com/PowerShell/Win32-OpenSSH/releases/latest" -ForegroundColor Cyan
    exit 1
}
Write-Host "SSH found" -ForegroundColor Green
Write-Host ""

# Test connection
Write-Host "Testing connection to Raspberry Pi at $RaspberryPiIP..." -ForegroundColor Yellow
$testResult = ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no $piUsername@$RaspberryPiIP "echo 'Connection successful'" 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "SSH connection failed. Please check:" -ForegroundColor Red
    Write-Host "  1. Raspberry Pi is powered on and connected to network" -ForegroundColor Yellow
    Write-Host "  2. IP address is correct: $RaspberryPiIP" -ForegroundColor Yellow
    Write-Host "  3. SSH is enabled on Raspberry Pi" -ForegroundColor Yellow
    Write-Host "  4. Username '$piUsername' and password are correct" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Try connecting manually: ssh $piUsername@$RaspberryPiIP" -ForegroundColor Cyan
    exit 1
}
Write-Host "Connection successful!" -ForegroundColor Green
Write-Host ""

# Build the deployment command
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Starting Deployment" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Execute deployment steps one by one
Write-Host "Step 1: Pulling latest changes from git..." -ForegroundColor Yellow
ssh $piUsername@$RaspberryPiIP "cd $projectPath && git pull origin main"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Git pull failed!" -ForegroundColor Red
    exit 1
}
Write-Host "Git pull complete" -ForegroundColor Green
Write-Host ""

Write-Host "Step 2: Stopping existing Docker containers..." -ForegroundColor Yellow
ssh $piUsername@$RaspberryPiIP "cd $projectPath/docker && docker-compose down"
Write-Host "Containers stopped" -ForegroundColor Green
Write-Host ""

Write-Host "Step 3: Rebuilding Docker images..." -ForegroundColor Yellow
ssh $piUsername@$RaspberryPiIP "cd $projectPath/docker && docker-compose build --no-cache"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "Docker images rebuilt" -ForegroundColor Green
Write-Host ""

Write-Host "Step 4: Starting Docker services..." -ForegroundColor Yellow
ssh $piUsername@$RaspberryPiIP "cd $projectPath/docker && docker-compose up -d"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker start failed!" -ForegroundColor Red
    exit 1
}
Write-Host "Docker services started" -ForegroundColor Green
Write-Host ""

Write-Host "Step 5: Checking container status..." -ForegroundColor Yellow
ssh $piUsername@$RaspberryPiIP "cd $projectPath/docker && docker-compose ps"
Write-Host ""

Write-Host "=========================================" -ForegroundColor Green
Write-Host "  Deployment Successful!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Your AutoLister application has been updated and restarted." -ForegroundColor Cyan
Write-Host "Dashboard: http://$RaspberryPiIP:8000" -ForegroundColor Cyan
Write-Host ""
