#!/bin/bash
# AutoLister Deployment and Update Script for Raspberry Pi
# This script connects to the Raspberry Pi, pulls latest code, rebuilds Docker, and starts services

# Configuration
PI_USERNAME="lane"
PI_PASSWORD="growtent"
PROJECT_PATH="~/autolister"

# Display banner
echo "========================================="
echo "  AutoLister Update & Deploy Script"
echo "========================================="
echo ""

# Check if SSH is available
if ! command -v ssh &> /dev/null; then
    echo "ERROR: SSH is not available."
    echo "Please install OpenSSH client."
    exit 1
fi

# Check if sshpass is available
if ! command -v sshpass &> /dev/null; then
    echo "WARNING: sshpass is not installed."
    echo "The script will prompt for password, or you can install sshpass:"
    echo "  Ubuntu/Debian: sudo apt install sshpass"
    echo "  macOS: brew install sshpass"
    echo ""
fi

# Get Raspberry Pi IP
if [ -z "$1" ]; then
    read -p "Enter Raspberry Pi IP address: " PI_IP
else
    PI_IP="$1"
fi

if [ -z "$PI_IP" ]; then
    echo "ERROR: IP address cannot be empty."
    exit 1
fi

# Test connection
echo "Testing connection to Raspberry Pi at $PI_IP..."
echo ""

if command -v sshpass &> /dev/null; then
    # Use sshpass for automated authentication
    sshpass -p "$PI_PASSWORD" ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$PI_USERNAME@$PI_IP" "echo 'Connection successful'" > /dev/null 2>&1
else
    # Manual authentication
    ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$PI_USERNAME@$PI_IP" "echo 'Connection successful'" > /dev/null 2>&1
fi

if [ $? -ne 0 ]; then
    echo "✗ SSH connection failed. Please check:"
    echo "  1. Raspberry Pi is powered on and connected to network"
    echo "  2. IP address is correct: $PI_IP"
    echo "  3. SSH is enabled on Raspberry Pi"
    echo "  4. Username '$PI_USERNAME' and password are correct"
    echo ""
    echo "Try connecting manually: ssh $PI_USERNAME@$PI_IP"
    exit 1
fi

echo "✓ Connection successful!"
echo ""

# Build the deployment command
echo "========================================="
echo "  Starting Deployment"
echo "========================================="
echo ""

DEPLOY_COMMAND="cd $PROJECT_PATH && \
echo '--- Step 1: Pulling latest changes from git ---' && \
git pull origin main && \
echo '' && \
echo '--- Step 2: Stopping existing Docker containers ---' && \
cd docker && \
docker-compose down && \
echo '' && \
echo '--- Step 3: Rebuilding Docker images ---' && \
docker-compose build && \
echo '' && \
echo '--- Step 4: Regenerating database ---' && \
docker-compose run --rm web python -c \"from app.database import regenerate_db; regenerate_db()\" && \
echo '' && \
echo '--- Step 5: Starting Docker services ---' && \
docker-compose up -d && \
echo '' && \
echo '--- Step 6: Checking container status ---' && \
docker-compose ps && \
echo '' && \
echo '--- Deployment Complete! ---' && \
echo 'Services should be accessible at:' && \
echo \"  Dashboard: http://$PI_IP:8000\""

# Execute the deployment command
echo "Executing deployment on Raspberry Pi..."
echo ""

if command -v sshpass &> /dev/null; then
    sshpass -p "$PI_PASSWORD" ssh -o StrictHostKeyChecking=no "$PI_USERNAME@$PI_IP" "$DEPLOY_COMMAND"
else
    ssh -o StrictHostKeyChecking=no "$PI_USERNAME@$PI_IP" "$DEPLOY_COMMAND"
fi

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================="
    echo "  Deployment Successful!"
    echo "========================================="
    echo ""
    echo "Your AutoLister application has been updated and restarted."
    echo "Dashboard: http://$PI_IP:8000"
    echo ""
else
    echo ""
    echo "========================================="
    echo "  Deployment Failed!"
    echo "========================================="
    echo ""
    echo "Please check the error messages above and try again."
    echo ""
    exit 1
fi
