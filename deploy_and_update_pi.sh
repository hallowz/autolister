#!/bin/bash
# AutoLister Deployment and Update Script for Raspberry Pi
# This script connects to the Raspberry Pi, pulls latest code, rebuilds Docker, and starts services

# Configuration
PI_USERNAME="lane"
PROJECT_PATH="~/autolister"
QUICK_RESTART=false
SETUP_KEYS=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            QUICK_RESTART=true
            shift
            ;;
        --setup-keys)
            SETUP_KEYS=true
            shift
            ;;
        *)
            PI_IP="$1"
            shift
            ;;
    esac
done

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

# Setup SSH keys if requested
if [ "$SETUP_KEYS" = true ]; then
    echo "========================================="
    echo "  Setting up SSH Key Authentication"
    echo "========================================="
    echo ""
    
    # Check if SSH keys already exist
    SSH_DIR="$HOME/.ssh"
    PRIVATE_KEY="$SSH_DIR/id_ed25519"
    PUBLIC_KEY="$SSH_DIR/id_ed25519.pub"
    
    if [ ! -f "$PRIVATE_KEY" ]; then
        echo "No SSH key found. Generating new ED25519 key..."
        mkdir -p "$SSH_DIR"
        chmod 700 "$SSH_DIR"
        ssh-keygen -t ed25519 -f "$PRIVATE_KEY" -N "" -q
        echo "✓ SSH key generated successfully"
    else
        echo "✓ SSH key already exists at $PRIVATE_KEY"
    fi
    
    # Copy the public key to the Raspberry Pi
    echo "Copying public key to Raspberry Pi..."
    echo "You will be prompted for the password ONE TIME only."
    echo ""
    
    ssh-copy-id -i "$PUBLIC_KEY" "$PI_USERNAME@$PI_IP"
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✓ SSH key setup complete! You should now be able to connect without a password."
        echo ""
        echo "Test the connection by running: ssh $PI_USERNAME@$PI_IP"
    else
        echo "✗ SSH key setup failed. Please check your password and try again."
        exit 1
    fi
    exit 0
fi

# Get Raspberry Pi IP
if [ -z "$PI_IP" ]; then
    read -p "Enter Raspberry Pi IP address: " PI_IP
fi

if [ -z "$PI_IP" ]; then
    echo "ERROR: IP address cannot be empty."
    exit 1
fi

# Test connection
echo "Testing connection to Raspberry Pi at $PI_IP..."
echo ""

ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$PI_USERNAME@$PI_IP" "echo 'Connection successful'" > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "✗ SSH connection failed. Please check:"
    echo "  1. Raspberry Pi is powered on and connected to network"
    echo "  2. IP address is correct: $PI_IP"
    echo "  3. SSH is enabled on Raspberry Pi"
    echo "  4. Username '$PI_USERNAME' is correct"
    echo ""
    echo "To set up passwordless SSH authentication, run:"
    echo "  ./deploy_and_update_pi.sh $PI_IP --setup-keys"
    echo ""
    echo "Or connect manually to test: ssh $PI_USERNAME@$PI_IP"
    exit 1
fi

echo "✓ Connection successful!"
echo ""

# Quick restart mode - just restart containers
if [ "$QUICK_RESTART" = true ]; then
    echo "========================================="
    echo "  Quick Restart Mode"
    echo "========================================="
    echo ""
    
    echo "Restarting Docker containers..."
    ssh "$PI_USERNAME@$PI_IP" "cd $PROJECT_PATH/docker && docker-compose restart autolister"
    
    if [ $? -ne 0 ]; then
        echo "✗ Docker restart failed!"
        exit 1
    fi
    
    echo "✓ Docker containers restarted"
    echo ""
    
    echo "Checking container status..."
    ssh "$PI_USERNAME@$PI_IP" "cd $PROJECT_PATH/docker && docker-compose ps"
    echo ""
    
    echo "========================================="
    echo "  Quick Restart Complete!"
    echo "========================================="
    echo ""
    echo "Your AutoLister application has been restarted."
    echo "Dashboard: http://$PI_IP:8000"
    echo ""
    exit 0
fi

# Full deployment mode
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
docker-compose run --rm autolister python -c \"from app.database import regenerate_db; regenerate_db()\" && \
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

ssh -o StrictHostKeyChecking=no "$PI_USERNAME@$PI_IP" "$DEPLOY_COMMAND"

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
