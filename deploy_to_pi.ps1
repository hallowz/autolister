# PowerShell script to deploy AutoLister to Raspberry Pi
# Usage: .\deploy_to_pi.ps1

$ErrorActionPreference = "Stop"

# Configuration
$PI_IP = "192.168.5.8"
$PI_USER = "lane"
$PI_PASSWORD = "growtent"
$REPO_NAME = "autolister"
$REPO_URL = "https://github.com/hallowz/$REPO_NAME.git"

Write-Host "AutoLister Deployment Script" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""

# Step 1: Initialize Git Repository
Write-Host "Step 1: Initializing Git repository..." -ForegroundColor Cyan
git init
git add .
git commit -m "Initial commit - AutoLister application"

# Step 2: Create GitHub Repository (you'll need to do this manually)
Write-Host "Step 2: GitHub Repository Setup" -ForegroundColor Cyan
Write-Host "Please create a new repository at: https://github.com/new" -ForegroundColor Yellow
Write-Host "Repository name: $REPO_NAME" -ForegroundColor Yellow
Write-Host "Make it Public or Private as you prefer" -ForegroundColor Yellow
Write-Host ""
$continue = Read-Host "Press Enter after creating the repository"

# Step 3: Add remote and push
Write-Host "Step 3: Pushing to GitHub..." -ForegroundColor Cyan
git remote add origin $REPO_URL
git branch -M main
git push -u origin main

# Step 4: Test SSH Connection
Write-Host "Step 4: Testing SSH connection to Raspberry Pi..." -ForegroundColor Cyan
sshpass -p $PI_PASSWORD ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 $PI_USER@$PI_IP "echo 'Connection successful'"
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ SSH connection successful!" -ForegroundColor Green
} else {
    Write-Host "✗ SSH connection failed. Please check:" -ForegroundColor Red
    Write-Host "  - Raspberry Pi is powered on" -ForegroundColor Red
    Write-Host "  - IP address is correct: $PI_IP" -ForegroundColor Red
    Write-Host "  - SSH is enabled on Raspberry Pi" -ForegroundColor Red
    Write-Host "  - Username and password are correct" -ForegroundColor Red
    exit 1
}

# Step 5: Prepare Raspberry Pi
Write-Host "Step 5: Preparing Raspberry Pi..." -ForegroundColor Cyan
sshpass -p $PI_PASSWORD ssh -o StrictHostKeyChecking=no $PI_USER@$PI_IP "sudo apt-get update && sudo apt-get install -y git docker.io docker-compose"

# Step 6: Clone repository on Raspberry Pi
Write-Host "Step 6: Cloning repository on Raspberry Pi..." -ForegroundColor Cyan
sshpass -p $PI_PASSWORD ssh -o StrictHostKeyChecking=no $PI_USER@$PI_IP "cd ~ && rm -rf $REPO_NAME && git clone $REPO_URL $REPO_NAME"

# Step 7: Create .env file
Write-Host "Step 7: Creating .env file..." -ForegroundColor Cyan
$envContent = @"
APP_NAME=AutoLister
APP_VERSION=1.0.0
DEBUG=false
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8000

# Add your API keys below
# GOOGLE_API_KEY=your_google_api_key_here
# GOOGLE_CX=your_google_custom_search_engine_id_here
# BING_API_KEY=your_bing_api_key_here
# ETSY_API_KEY=your_etsy_api_key_here
# ETSY_API_SECRET=your_etsy_api_secret_here
# ETSY_ACCESS_TOKEN=your_etsy_access_token_here
# ETSY_ACCESS_TOKEN_SECRET=your_etsy_access_token_secret_here
# ETSY_SHOP_ID=your_etsy_shop_id_here
"@

sshpass -p $PI_PASSWORD ssh -o StrictHostKeyChecking=no $PI_USER@$PI_IP "cd ~/$REPO_NAME && echo '$envContent' > .env"

# Step 8: Start Docker containers
Write-Host "Step 8: Starting Docker containers..." -ForegroundColor Cyan
sshpass -p $PI_PASSWORD ssh -o StrictHostKeyChecking=no $PI_USER@$PI_IP "cd ~/$REPO_NAME/docker && docker-compose up -d"

# Step 9: Wait for services to start
Write-Host "Step 9: Waiting for services to start..." -ForegroundColor Cyan
Start-Sleep -Seconds 10

# Step 10: Check status
Write-Host "Step 10: Checking service status..." -ForegroundColor Cyan
sshpass -p $PI_PASSWORD ssh -o StrictHostKeyChecking=no $PI_USER@$PI_IP "cd ~/$REPO_NAME/docker && docker-compose ps"

Write-Host ""
Write-Host "================================" -ForegroundColor Green
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""
Write-Host "Access the dashboard at: http://$PI_IP:8000/dashboard" -ForegroundColor Yellow
Write-Host "To view logs: ssh $PI_USER@$PI_IP 'cd ~/$REPO_NAME/docker && docker-compose logs -f'" -ForegroundColor Yellow
Write-Host "To stop: ssh $PI_USER@$PI_IP 'cd ~/$REPO_NAME/docker && docker-compose down'" -ForegroundColor Yellow
