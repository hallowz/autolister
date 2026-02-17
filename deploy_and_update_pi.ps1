# AutoLister Deployment and Update Script for Raspberry Pi
# This script connects to the Raspberry Pi, pulls latest code, rebuilds Docker, and starts services

param(
    [Parameter(Mandatory=$true)]
    [string]$RaspberryPiIP,
    [string]$piUsername = "lane",
    [string]$projectPath = "~/autolister",
    [switch]$QuickRestart,  # Skip git pull and rebuild, just restart containers
    [switch]$SetupKeys      # Setup SSH keys for passwordless authentication
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

# Setup SSH keys if requested
if ($SetupKeys) {
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host "  Setting up SSH Key Authentication" -ForegroundColor Cyan
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Check if SSH keys already exist
    $sshDir = "$env:USERPROFILE\.ssh"
    $privateKey = "$sshDir\id_ed25519"
    $publicKey = "$sshDir\id_ed25519.pub"
    
    if (-not (Test-Path $privateKey)) {
        Write-Host "No SSH key found. Generating new ED25519 key..." -ForegroundColor Yellow
        New-Item -ItemType Directory -Force -Path $sshDir | Out-Null
        ssh-keygen -t ed25519 -f $privateKey -N "" -q
        Write-Host "SSH key generated successfully" -ForegroundColor Green
    } else {
        Write-Host "SSH key already exists at $privateKey" -ForegroundColor Green
    }
    
    # Read the public key
    $publicKeyContent = Get-Content $publicKey -Raw
    
    # Copy the public key to the Raspberry Pi
    Write-Host "Copying public key to Raspberry Pi..." -ForegroundColor Yellow
    Write-Host "You will be prompted for the password ONE TIME only." -ForegroundColor Cyan
    Write-Host ""
    
    $publicKeyContent | ssh $piUsername@$RaspberryPiIP "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "SSH key setup complete! You should now be able to connect without a password." -ForegroundColor Green
        Write-Host ""
        Write-Host "Test the connection by running: ssh $piUsername@$RaspberryPiIP" -ForegroundColor Cyan
    } else {
        Write-Host "SSH key setup failed. Please check your password and try again." -ForegroundColor Red
        exit 1
    }
    exit 0
}

# Test connection
Write-Host "Testing connection to Raspberry Pi at $RaspberryPiIP..." -ForegroundColor Yellow
$testResult = ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no $piUsername@$RaspberryPiIP "echo 'Connection successful'" 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "SSH connection failed. Please check:" -ForegroundColor Red
    Write-Host "  1. Raspberry Pi is powered on and connected to network" -ForegroundColor Yellow
    Write-Host "  2. IP address is correct: $RaspberryPiIP" -ForegroundColor Yellow
    Write-Host "  3. SSH is enabled on Raspberry Pi" -ForegroundColor Yellow
    Write-Host "  4. Username '$piUsername' is correct" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To set up passwordless SSH authentication, run:" -ForegroundColor Cyan
    Write-Host "  .\deploy_and_update_pi.ps1 -RaspberryPiIP $RaspberryPiIP -SetupKeys" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Or connect manually to test: ssh $piUsername@$RaspberryPiIP" -ForegroundColor Cyan
    exit 1
}
Write-Host "Connection successful!" -ForegroundColor Green
Write-Host ""

# Quick restart mode - just restart containers
if ($QuickRestart) {
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host "  Quick Restart Mode" -ForegroundColor Cyan
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "Restarting Docker containers..." -ForegroundColor Yellow
    ssh $piUsername@$RaspberryPiIP "cd $projectPath/docker && docker-compose restart autolister"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Docker restart failed!" -ForegroundColor Red
        exit 1
    }
    Write-Host "Docker containers restarted" -ForegroundColor Green
    Write-Host ""
    
    Write-Host "Step 2: Checking container status..." -ForegroundColor Yellow
    ssh $piUsername@$RaspberryPiIP "cd $projectPath/docker && docker-compose ps"
    Write-Host ""
    
    Write-Host "=========================================" -ForegroundColor Green
    Write-Host "  Quick Restart Complete!" -ForegroundColor Green
    Write-Host "=========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Your AutoLister application has been restarted." -ForegroundColor Cyan
    Write-Host "Dashboard: http://$RaspberryPiIP:8000" -ForegroundColor Cyan
    Write-Host ""
    exit 0
}

# Full deployment mode - use single SSH connection to avoid multiple password prompts
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Starting Deployment" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Build a single command that runs all deployment steps
$deployCommand = @"
cd $projectPath && echo '--- Step 1: Pulling latest changes from git ---' && git pull origin main && echo '' && echo '--- Step 2: Stopping existing Docker containers ---' && cd docker && docker-compose down && echo '' && echo '--- Step 3: Rebuilding Docker images ---' && docker-compose build && echo '' && echo '--- Step 4: Regenerating database ---' && docker-compose run --rm autolister python -c 'from app.database import regenerate_db; regenerate_db()' && echo '' && echo '--- Step 5: Starting Docker services ---' && docker-compose up -d && echo '' && echo '--- Step 6: Checking container status ---' && docker-compose ps && echo '' && echo '--- Deployment Complete! ---' && echo 'Services should be accessible at:' && echo "  Dashboard: http://$RaspberryPiIP:8000"
"@

# Execute all steps in a single SSH connection
Write-Host "Executing deployment on Raspberry Pi..." -ForegroundColor Yellow
Write-Host "Note: You will be prompted for your password ONE TIME." -ForegroundColor Cyan
Write-Host ""

ssh -o StrictHostKeyChecking=no $piUsername@$RaspberryPiIP $deployCommand

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=========================================" -ForegroundColor Green
    Write-Host "  Deployment Successful!" -ForegroundColor Green
    Write-Host "=========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Your AutoLister application has been updated and restarted." -ForegroundColor Cyan
    Write-Host "Dashboard: http://$RaspberryPiIP:8000" -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "=========================================" -ForegroundColor Red
    Write-Host "  Deployment Failed!" -ForegroundColor Red
    Write-Host "=========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please check the error messages above and try again." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Tip: To avoid password prompts in the future, run:" -ForegroundColor Cyan
    Write-Host "  .\deploy_and_update_pi.ps1 -RaspberryPiIP $RaspberryPiIP -SetupKeys" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}
