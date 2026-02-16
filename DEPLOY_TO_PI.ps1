# Deployment Script for AutoLister to Raspberry Pi
# Run this script from Windows to deploy the application

param(
    [Parameter(Mandatory=$true)]
    [string]$RaspberryPiIP,
    [string]$piUsername = "pi",
    [string]$piPassword = ""
)

# Display banner
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  AutoLister Deployment Script" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Check if required tools are available
Write-Host "Checking for required tools..." -ForegroundColor Yellow
$scpAvailable = Get-Command scp -ErrorAction SilentlyContinue
$sshAvailable = Get-Command ssh -ErrorAction SilentlyContinue

if (-not $scpAvailable) -or (-not $sshAvailable)) {
    Write-Host "ERROR: Neither SCP nor SSH is available." -ForegroundColor Red
    Write-Host "Please install OpenSSH or use PowerShell to connect." -ForegroundColor Red
    Write-Host ""
    Write-Host "You can install OpenSSH from: https://github.com/PowerShell/Win32-OpenSSH/releases/latest" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

# Get Raspberry Pi IP
Write-Host "Enter your Raspberry Pi IP address:" -ForegroundColor Green
$ip = Read-Host

if ([string]::IsNullOrWhiteSpace($ip)) {
    Write-Host "ERROR: IP address cannot be empty." -ForegroundColor Red
    Write-Host ""
    exit 1
}

# Test connection
Write-Host "Testing connection to Raspberry Pi..." -ForegroundColor Yellow
Write-Host ""

# First test SSH connection
$sshResult = ssh -o ConnectTimeout=5 $piUsername@$ip "echo 'Connection successful'" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ SSH connection successful!" -ForegroundColor Green
} else {
    Write-Host "✗ SSH connection failed. Please check:" -ForegroundColor Red
    Write-Host "1. Raspberry Pi is powered on and connected to network" -ForegroundColor Yellow
    Write-Host "2. IP address is correct: $ip" -ForegroundColor Yellow
    Write-Host "3. SSH is enabled on Raspberry Pi (Settings → Interfaces → SSH)"" -ForegroundColor Yellow
    Write-Host "4. No firewall blocking port 22" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "You can also use PowerShell to connect:" -ForegroundColor Cyan
    Write-Host "  ssh $piUsername@$ip" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

# If SSH works, proceed with deployment
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Starting Deployment" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Transfer files to Raspberry Pi
Write-Host "Transferring files to Raspberry Pi..." -ForegroundColor Yellow
Write-Host ""

# Create a temporary zip file
$tempDir = "$env:TEMP\autolister-deploy"
if (-not (Test-Path $tempDir)) {
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
}

# Create zip of application files
$zipFile = "$tempDir\AutoLister.zip"
Write-Host "Creating deployment package..." -ForegroundColor Yellow
Compress-Archive -Path ".\*" -DestinationPath $zipFile -Force -CompressionLevel Optimal

# Get list of files to exclude
$excludeFiles = @(
    "venv",
    "__pycache__",
    "*.pyc",
    ".git",
    ".gitignore",
    ".env.example",
    "data\*.db",
    "data\pdfs\*",
    "data\images\*",
    "logs\*"
)

# Add files to zip
Get-ChildItem -Path ".\*" -Exclude $excludeFiles | ForEach-Object {
    $item = $_
    if ($item.PSIsContainer -eq $false) {
        Compress-Archive -Path $item.FullName -DestinationPath $zipFile -Force
    }
}

Write-Host "✓ Deployment package created: $zipFile" -ForegroundColor Green
Write-Host "Size: $((Get-Item $zipFile).Length / 1MB) MB" -ForegroundColor Green
Write-Host ""

# Transfer zip to Raspberry Pi
Write-Host "Uploading to Raspberry Pi..." -ForegroundColor Yellow

$uploadResult = scp -o ConnectTimeout=60 "$zipFile" "$piUsername@$ip:/home/$piUsername/AutoLister.zip" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Files uploaded successfully!" -ForegroundColor Green
} else {
    Write-Host "✗ File upload failed." -ForegroundColor Red
    Write-Host "Please check the connection and try again." -ForegroundColor Red
    Write-Host ""
    exit 1
}

# Extract and setup on Raspberry Pi
Write-Host ""
Write-Host "Setting up AutoLister on Raspberry Pi..." -ForegroundColor Yellow
Write-Host ""

$commands = @"
# Navigate to AutoLister directory
cd /home/$piUsername/AutoLister

# Extract the deployment package
unzip -o AutoLister.zip

# Create environment file
cp .env.example .env

# Create necessary directories
mkdir -p data/pdfs data/images logs

# Set permissions
chmod +x .env

# Build Docker images
cd docker
docker-compose build

# Start the application
docker-compose up -d

# Check if services are running
sleep 5
docker-compose ps

echo ""
echo "========================================" -ForegroundColor Cyan
echo "  Deployment Complete!" -ForegroundColor Cyan
echo "========================================" -ForegroundColor Cyan
echo ""
echo "AutoLister is now running on your Raspberry Pi!" -ForegroundColor Green
echo ""
echo "Access the dashboard at:" -ForegroundColor Yellow
echo "  http://$ip:8000/dashboard" -ForegroundColor Cyan
echo ""
echo "Next steps:" -ForegroundColor Yellow
echo "1. Edit .env file with your configuration" -ForegroundColor Yellow
echo "2. Restart services if needed: docker-compose restart" -ForegroundColor Yellow
echo "3. View logs: docker-compose logs -f autolister" -ForegroundColor Yellow
echo ""
echo "To stop the application:" -ForegroundColor Yellow
echo "  docker-compose down" -ForegroundColor Yellow
echo ""
"@

# Execute commands on Raspberry Pi
Write-Host "Executing setup commands on Raspberry Pi..." -ForegroundColor Yellow

$sshResult = ssh -o ConnectTimeout=300 $piUsername@$ip $commands 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Setup completed successfully!" -ForegroundColor Green
} else {
    Write-Host "✗ Setup failed. Please check the connection." -ForegroundColor Red
    Write-Host "You can manually SSH into the Raspberry Pi and run:" -ForegroundColor Yellow
    Write-Host "  cd /home/$piUsername/AutoLister && unzip -o AutoLister.zip" -ForegroundColor Cyan
    Write-Host "  cp .env.example .env" -ForegroundColor Cyan
    Write-Host "  cd docker && docker-compose build" -ForegroundColor Cyan
    Write-Host "  docker-compose up -d" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

# Display completion message
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Deployment Script Complete" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
